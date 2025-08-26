from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import ChatRoom, Message, UploadedFile, MessageURL
from .serializers import ChatRoomSerializer, MessageSerializer, UploadedFileSerializer, MessageURLSerializer

from django.utils import timezone


# Import your FSM chatbot
from pathlib import Path
import json
from .chatbot import DialogueFSM  # <- put FSM code in fsm_chatbot.py
APP_DIR = Path(__file__).resolve().parent
PARSED_INPUT_FILE = APP_DIR / "parsed_outputs" / "all_parsed.json"

# ✅ Keep a single FSM per user (in memory or DB)
_user_fsms = {}

def get_user_fsm(user_id):
    """Get or create FSM for a specific user."""
    if not PARSED_INPUT_FILE.exists():
        return None
    if user_id not in _user_fsms:
        exercises = load_json(PARSED_INPUT_FILE)
        _user_fsms[user_id] = DialogueFSM(exercises)
    return _user_fsms[user_id]

def load_json(p):
    if not p.exists():
        return []  # empty exercises
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

# ------------------ ChatRoom Views ------------------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def chatroom_list_create(request):
    if request.method == "GET":
        rooms = ChatRoom.objects.all().order_by("-created_at")
        serializer = ChatRoomSerializer(rooms, many=True, context={"request": request})
        return Response(serializer.data)
    elif request.method == "POST":
        serializer = ChatRoomSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def chatroom_detail(request, uuid):
    """
    GET    -> Retrieve chatroom details
    PATCH  -> Update chatroom (e.g., rename)
    DELETE -> Delete chatroom
    """
    room = get_object_or_404(ChatRoom, uuid=uuid)

    # GET
    if request.method == "GET":
        serializer = ChatRoomSerializer(room, context={"request": request})
        return Response(serializer.data)

    # PATCH / UPDATE
    elif request.method == "PATCH":
        serializer = ChatRoomSerializer(room, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    elif request.method == "DELETE":
        room.delete()
        return Response({"detail": "ChatRoom deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chatroom_detail_uuid(request, uuid):
    """
    GET    -> Retrieve chatroom details
    PATCH  -> Update chatroom (e.g., rename)
    DELETE -> Delete chatroom
    """
    room = get_object_or_404(ChatRoom, uuid=uuid)

    # GET
    if request.method == "GET":
        serializer = ChatRoomSerializer(room, context={"request": request})
        return Response(serializer.data)


# ------------------ Message Views ------------------

# @api_view(["GET", "POST"])
# @permission_classes([IsAuthenticated])
# def message_list_create(request):
#     if request.method == "GET":
#         messages = Message.objects.all().order_by("timestamp")
#         serializer = MessageSerializer(messages, many=True, context={"request": request})
#         return Response(serializer.data)

#     elif request.method == "POST":
#         urls_data = request.data.pop("urls", [])
#         serializer = MessageSerializer(data=request.data, context={"request": request})
        
#         if serializer.is_valid():
#             # Save user message
#             user_message = serializer.save(user=request.user)

#             # Save attached URLs
#             for u in urls_data:
#                 MessageURL.objects.create(
#                     message=user_message,
#                     file_url=u.get("file_url"),
#                     type=u.get("type", "file")
#                 )

#             # Create bot reply
#             bot_message = Message.objects.create(
#                 room=user_message.room,
#                 sender="AI Bot",
#                 text=f"I am your assistant",
#                 user=None
#             )

#             # If you want to include URLs for bot message, you can do it here too
#             # MessageURL.objects.create(message=bot_message, file_url="...", type="...")

#             # Return **both messages** in response
#             data = MessageSerializer([user_message, bot_message], many=True, context={"request": request}).data
#             return Response(data, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def message_list_create(request):
    if request.method == "GET":
        messages = Message.objects.all().order_by("timestamp")
        serializer = MessageSerializer(messages, many=True, context={"request": request})
        return Response(serializer.data)

    elif request.method == "POST":
        urls_data = request.data.pop("urls", [])
        lang = request.data.get("lang", "en")  # frontend language
        print("Language from frontend:", lang)

        serializer = MessageSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            # Save user message
            user_message = serializer.save(user=request.user)

            # Save attached URLs
            for u in urls_data:
                MessageURL.objects.create(
                    message=user_message,
                    file_url=u.get("file_url"),
                    type=u.get("type", "file")
                )

            # -------- Get last 5 messages (excluding current) --------
            previous_messages = Message.objects.filter(
                room=user_message.room
            ).exclude(id=user_message.id).order_by("-timestamp")[:5]
            previous_messages = reversed(previous_messages)  # oldest first

            chat_history_text = ""
            for msg in previous_messages:
                if msg.user:  
                    sender = "User"
                else:
                    sender = msg.sender or "AI Bot"
                chat_history_text += f"{sender}: {msg.text}\n"

            # -------- Load FSM state --------
            room = user_message.room
            fsm_state = room.fsm_state_json or {
                "state": "START",
                "grade": None,
                "topic": None,
                "current_exercise": None,
                "hint_index": 0,
                "question_index": 0,
            }

            fsm = DialogueFSM(
                exercises_data=load_json(PARSED_INPUT_FILE),
                state=fsm_state.get("state"),
                grade=fsm_state.get("grade"),
                topic=fsm_state.get("topic"),
                current_exercise=fsm_state.get("current_exercise"),
                hint_index=fsm_state.get("hint_index", 0),
                question_index=fsm_state.get("question_index", 0),
                language=lang  # pass language here
            )

            # -------- Combine prompt with language info --------
            combined_input = f"[Language: {lang}]\n{chat_history_text}User: {user_message.text}"
            reply = fsm.transition(combined_input)

            # Save bot reply
            bot_message = Message.objects.create(
                room=room,
                sender="AI Bot",
                text=reply,
                user=None
            )

            # Persist updated FSM state
            room.fsm_state_json = fsm.serialize()
            room.save()

            return Response({
                "messages": MessageSerializer([bot_message], many=True, context={"request": request}).data,
                "fsm": fsm.serialize()
            }, status=201)

        return Response(serializer.errors, status=400)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def message_detail(request, pk):
    message = get_object_or_404(Message, pk=pk)
    serializer = MessageSerializer(message, context={"request": request})
    return Response(serializer.data)


# ------------------ UploadedFile Views ------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_files(request):
    """
    Upload files independently, return URLs for later use in MessageURL
    """
    files = request.FILES.getlist("files")
    if not files:
        return Response({"error": "files are required"}, status=400)

    uploaded_files = []
    for f in files:
        uf = UploadedFile.objects.create(
            file=f,
            type="image" if f.content_type.startswith("image") else "file"
        )
        uploaded_files.append(uf)

    serializer = UploadedFileSerializer(uploaded_files, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)
