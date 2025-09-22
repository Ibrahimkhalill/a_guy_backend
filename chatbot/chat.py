# <- put FSM code in fsm_chatbot.py
from .chatbot import DialogueFSM, State, get_pinecone_index
import json
from pathlib import Path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import ChatRoom, UploadedFile
from django.core.files import File
import os
import uuid
import re 
INDEX_NAME = "mathtutor-e5-large"
# Import your FSM chatbot
APP_DIR = Path(__file__).resolve().parent
PARSED_INPUT_FILE = APP_DIR / "parsed_outputs" / "merged_output.json"
SVG_OUTPUT_DIR = APP_DIR / "svg_outputs"
SVG_OUTPUT_DIR.mkdir(exist_ok=True)

# ✅ Keep a single FSM per user (in memory or DB)
_user_room_fsms = {}  # cache per-user FSMs


def load_json(p):
    if not p.exists():
        return []  # empty exercises
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def get_user_room_fsm(room_uuid):
    """Get or create FSM for a specific user and chat room, loading state from DB."""
    if not PARSED_INPUT_FILE.exists():
        print(f"Parsed input file not found: {PARSED_INPUT_FILE}")
        return None

    key = (room_uuid)
    # Check cache first
    if key in _user_room_fsms:
        return _user_room_fsms[key]

    # Load exercises and Pinecone index
    exercises = load_json(PARSED_INPUT_FILE)
    pinecone_index = get_pinecone_index()

    # Create new FSM
    fsm = DialogueFSM(
        exercises_data=exercises,
        pinecone_index=pinecone_index,
        room_uuid=room_uuid
    )

    # Load state from room's fsm_state_json if available
    try:
        room = ChatRoom.objects.get(uuid=room_uuid)
        if room.fsm_state_json:
            fsm_state = room.fsm_state_json
            fsm.state = State[fsm_state.get("state", "START")]
            fsm.grade = fsm_state.get("grade")
            fsm.hebrew_grade = fsm_state.get("hebrew_grade")
            fsm.topic = fsm_state.get("topic")
            fsm.current_exercise = fsm_state.get("current_exercise")
            fsm.current_hint_index = fsm_state.get("hint_index", 0)
            fsm.current_question_index = fsm_state.get("question_index", 0)
            fsm.attempt_tracker.guidance_level = fsm_state.get("guidance_level")
            fsm.diagnostic_question_index = fsm_state.get("diagnostic_question_index")
            fsm.diagnostic_responses = fsm_state.get("diagnostic_responses")
            fsm.topic_exercises_count = fsm_state.get("topic_exercises_count")
            fsm.user_language = fsm_state.get("user_language")
            fsm.recently_asked_exercise_ids = fsm_state.get(
                "recently_asked_exercise_ids", [])
            # Recompute hebrew_grade if missing
            if fsm.grade and not fsm.hebrew_grade:
                fsm.hebrew_grade = fsm._translate_grade_to_hebrew(fsm.grade)
    except ChatRoom.DoesNotExist:
        print(
            f"ChatRoom with uuid {room_uuid} not found")
        return None

    # Cache the FSM (optional, for performance during a session)
    _user_room_fsms[key] = fsm
    return fsm

# ------------------ ChatRoom Views ------------------


def save_svg_to_file(svg_filepath):
    """Save SVG file to media storage and create an UploadedFile record."""
    try:
        svg_filename = os.path.basename(svg_filepath)
        with open(svg_filepath, "rb") as f:
            uploaded_file = UploadedFile.objects.create(
                file=File(f, name=svg_filename),
                type="image"
            )
        file_url = f"{settings.MEDIA_URL}chat/uploads/{svg_filename}"
        return uploaded_file, file_url
    except Exception as e:
        print(f"Error saving SVG file: {str(e)}")
        return None, None




@api_view(["POST"])
def message_create(request):
    user_text = request.data.get("text")   # user message text
    room_id = request.data.get("chat_id")  # optional room id

    # ✅ Check user_text provided
    if not user_text:
        return Response(
            {"messages": "Text field is a required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ✅ Validate chat_id if provided
    if room_id:
        try:
            room_uuid = uuid.UUID(str(room_id).strip())  # ensure valid UUID
            room = ChatRoom.objects.get(uuid=room_uuid)
        except ValueError:
            return Response(
                {"messages": "The provided chat ID format is not valid."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ChatRoom.DoesNotExist:
            return Response(
                {"messages": "We could not find a chat with this ID."},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        room = ChatRoom.objects.create()

    
    # Initialize FSM
    fsm = get_user_room_fsm(room.uuid)
    if fsm is None:
        return Response(
            {"messages": "Sorry, exercises are not available right now."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Process user input
    response = fsm.transition(user_text)

    response_text = re.sub(r"[$]", "", response['text'])  # remove $ signs

    # Save SVG if available
    file_url = None
    if response["svg_file_path"]:
        uploaded_file, relative_url = save_svg_to_file(response["svg_file_path"])
        if relative_url:
            file_url = request.build_absolute_uri(relative_url)
        else:
            print(f"Failed to save SVG for message in room {room.uuid}")

    return Response({
        "chat_id": room.uuid,
        "bot_response": response_text,
        "svg_url": file_url
    }, status=status.HTTP_200_OK)

  
