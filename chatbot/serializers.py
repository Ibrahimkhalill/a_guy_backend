from rest_framework import serializers
from .models import ChatRoom, Message, UploadedFile, MessageURL


from authentications.serializers import CustomUserSerializer


class UploadedFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = ["id", "type", "file_url", "uploaded_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None


class MessageURLSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageURL
        fields = ["id", "file_url", "type"]


class MessageSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    urls = MessageURLSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ["id", "room", "sender", "user", "text", "timestamp", "urls"]


class ChatRoomSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatRoom
        fields = ["id", "uuid", "name", "created_at", "messages"]



