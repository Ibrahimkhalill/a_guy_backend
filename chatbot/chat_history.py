import os
import json
import random
from pathlib import Path
from enum import Enum, auto
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from google import genai
from .chatbot import DialogueFSM 

# ----------------------------
# CONFIG
# -----------------------------
PARSED_INPUT_FILE = Path("parsed_outputs/all_parsed.json")

# -----------------------------
# GenAI Chat Client
# -----------------------------
client = genai.Client()
chat = client.chats.create(model="gemini-2.5-flash")


# -----------------------------
# Helpers
# -----------------------------
def load_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def genai_chat_answer(message: str) -> str:
    try:
        response = chat.send_message(message)
        return response.text
    except Exception as e:
        return f"❌ GenAI Error: {str(e)}"




# -----------------------------
# Django View (API)
# -----------------------------
@csrf_exempt
def dialogue_api(request):
    """
    POST /dialogue_api/
    Body: {"message": "user text", "fsm": {...}}
    Returns: {"reply": "...", "fsm": {...}}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        message = data.get("message", "")
        fsm_state = data.get("fsm", {})

        # Load exercises
        if not PARSED_INPUT_FILE.exists():
            return JsonResponse({"error": "Missing JSON file."}, status=500)
        exercises = load_json(PARSED_INPUT_FILE)

        # Rebuild FSM
        fsm = DialogueFSM(
            exercises,
            state=fsm_state.get("state", "START"),
            grade=fsm_state.get("grade"),
            topic=fsm_state.get("topic"),
            current_exercise=fsm_state.get("current_exercise"),
            hint_index=fsm_state.get("hint_index", 0),
            question_index=fsm_state.get("question_index", 0),
        )

        # Run FSM transition
        reply = fsm.transition(message)

        return JsonResponse({
            "reply": reply,
            "fsm": fsm.serialize()
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
