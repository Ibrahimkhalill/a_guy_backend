import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatRoom(models.Model):
    """
    Represents a chat room where multiple messages can belong.
    """
    user = models.ForeignKey(
        User, related_name="chatrooms", on_delete=models.CASCADE, blank=True, null=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    fsm_state_json = models.JSONField(
        default=dict, blank=True, null=True)  # <-- add this field

    def __str__(self):
        return self.name or f"Room {self.uuid}"


class Message(models.Model):
    """
    Represents a message sent by a user or bot.
    Supports text + optional URLs (stored in MessageURL model)
    """
    SENDER_CHOICES = [
        ("user", "User"),
        ("bot", "Bot"),
    ]

    room = models.ForeignKey(
        ChatRoom, related_name="messages", on_delete=models.CASCADE)
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    user = models.ForeignKey(User, related_name="messages",
                             on_delete=models.SET_NULL, blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sender_name = self.user.username if self.user else self.sender
        return f"{sender_name}: {self.text[:30] if self.text else 'Attachment(s)'}"


class UploadedFile(models.Model):
    """
    Stores uploaded files independently, without linking to message.
    """
    ATTACHMENT_TYPES = [
        ("image", "Image"),
        ("file", "File"),
    ]

    file = models.FileField(upload_to="chat/uploads/")
    type = models.CharField(max_length=10, choices=ATTACHMENT_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.file.name}"


class MessageURL(models.Model):
    """
    Links a Message to one or multiple uploaded file URLs.
    """
    message = models.ForeignKey(
        Message, related_name="urls", on_delete=models.CASCADE)
    file_url = models.URLField()  # store the URL of uploaded file
    type = models.CharField(
        max_length=10, choices=UploadedFile.ATTACHMENT_TYPES)

    def __str__(self):
        return f"{self.type} - {self.file_url}"
