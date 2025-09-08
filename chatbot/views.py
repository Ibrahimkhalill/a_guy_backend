# <- put FSM code in fsm_chatbot.py
from .chatbot import DialogueFSM, State, get_pinecone_index, generate_chat_title
import json
from pathlib import Path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import ChatRoom, Message, UploadedFile, MessageURL
from .serializers import ChatRoomSerializer, MessageSerializer, UploadedFileSerializer, MessageURLSerializer
from django.core.files import File
from django.utils import timezone
import uuid
import os


INDEX_NAME = "mathtutor-e5-large"
# Import your FSM chatbot
APP_DIR = Path(__file__).resolve().parent
PARSED_INPUT_FILE = APP_DIR / "parsed_outputs" / "all_parsed.json"
SVG_OUTPUT_DIR = APP_DIR / "svg_outputs"
SVG_OUTPUT_DIR.mkdir(exist_ok=True)

# ✅ Keep a single FSM per user (in memory or DB)
_user_room_fsms = {}  # cache per-user FSMs


def load_json(p):
    if not p.exists():
        return []  # empty exercises
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def get_user_room_fsm(user, room_uuid):
    """Get or create FSM for a specific user and chat room, loading state from DB."""
    if not PARSED_INPUT_FILE.exists():
        print(f"Parsed input file not found: {PARSED_INPUT_FILE}")
        return None

    key = (user, room_uuid)
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
        room = ChatRoom.objects.get(uuid=room_uuid, user=user)
        if room.fsm_state_json:
            fsm_state = room.fsm_state_json
            fsm.state = State[fsm_state.get("state", "START")]
            fsm.grade = fsm_state.get("grade")
            fsm.hebrew_grade = fsm_state.get("hebrew_grade")
            fsm.topic = fsm_state.get("topic")
            fsm.current_exercise = fsm_state.get("current_exercise")
            fsm.current_hint_index = fsm_state.get("hint_index", 0)
            fsm.current_question_index = fsm_state.get("question_index", 0)
            fsm.recently_asked_exercise_ids = fsm_state.get(
                "recently_asked_exercise_ids", [])
            # Recompute hebrew_grade if missing
            if fsm.grade and not fsm.hebrew_grade:
                fsm.hebrew_grade = fsm._translate_grade_to_hebrew(fsm.grade)
    except ChatRoom.DoesNotExist:
        print(
            f"ChatRoom with uuid {room_uuid} and user_id {user} not found")
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


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def chatroom_list_create(request):
    if request.method == "GET":
        rooms = ChatRoom.objects.filter(
            user=request.user).order_by("-created_at")
        serializer = ChatRoomSerializer(
            rooms, many=True, context={"request": request})
        return Response(serializer.data)
    elif request.method == "POST":
        serializer = ChatRoomSerializer(
            data=request.data, context={"request": request})
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
        serializer = ChatRoomSerializer(
            room, data=request.data, partial=True, context={"request": request})
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
        serializer = MessageSerializer(
            messages, many=True, context={"request": request})
        return Response(serializer.data)

    elif request.method == "POST":
        urls_data = request.data.pop("urls", [])
        lang = request.data.get("lang", "en")

        serializer = MessageSerializer(
            data=request.data, context={"request": request})
        if serializer.is_valid():
            user_message = serializer.save(user=request.user)

            for u in urls_data:
                MessageURL.objects.create(
                    message=user_message,
                    file_url=u.get("file_url"),
                    type=u.get("type", "file")
                )

            room = user_message.room

            try:
                # Use room-specific FSM
                fsm = get_user_room_fsm(request.user.id, str(room.uuid))
                if fsm is None:
                    print(
                        f"Failed to initialize FSM for user {request.user.id} and room {room.uuid}")
                    return Response(
                        {"detail": "Exercises data not available. Check if parsed JSON file exists."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Process user input
                response_text, svg_filepath = fsm.transition(
                    user_message.text)

                # Create bot message
                bot_message = Message.objects.create(
                    room=room,
                    sender="bot",
                    text=response_text,
                    user=None
                )

                # If first bot message, generate and set chat title
                if room.messages.count() > 10 and room.messages.count() < 14:  # user + bot
                    message_history = list(room.messages.order_by(
                        "timestamp").values_list("text", flat=True))[-5:]
                    title = generate_chat_title(message_history, language=lang)

                    room.name = title

                # Save SVG file and link to bot message
                if svg_filepath:
                    uploaded_file, file_url = save_svg_to_file(
                        svg_filepath)
                    if uploaded_file and file_url:
                        MessageURL.objects.create(
                            message=bot_message,
                            file_url=file_url,
                            type="image"
                        )
                    else:
                        print(
                            f"Failed to save SVG for message in room {room.uuid}")

                # Save FSM state back to room
                room.fsm_state_json = fsm.serialize()
                room.save()

                return Response({
                    "messages": MessageSerializer([bot_message], many=True, context={"request": request}).data,
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                print(
                    f"FSM Error for user {request.user.id} and room {room.uuid}: {str(e)}")
                return Response(
                    {"detail": f"Error processing chatbot response: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

    serializer = UploadedFileSerializer(
        uploaded_files, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)
