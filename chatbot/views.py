from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import ChatRoom, Message, UploadedFile, MessageURL
from .serializers import ChatRoomSerializer, MessageSerializer, UploadedFileSerializer, MessageURLSerializer


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

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def message_list_create(request):
    if request.method == "GET":
        messages = Message.objects.all().order_by("timestamp")
        serializer = MessageSerializer(messages, many=True, context={"request": request})
        return Response(serializer.data)

    elif request.method == "POST":
        urls_data = request.data.pop("urls", [])
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

            # Create bot reply
            bot_message = Message.objects.create(
                room=user_message.room,
                sender="AI Bot",
                text=f"I am your assistant",
                user=None
            )

            # If you want to include URLs for bot message, you can do it here too
            # MessageURL.objects.create(message=bot_message, file_url="...", type="...")

            # Return **both messages** in response
            data = MessageSerializer([user_message, bot_message], many=True, context={"request": request}).data
            return Response(data, status=status.HTTP_201_CREATED)

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

    serializer = UploadedFileSerializer(uploaded_files, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)
