from django.contrib import admin

# Register your models here.
from .models import ChatRoom, Message, UploadedFile, MessageURL
admin.site.register(ChatRoom)
admin.site.register(Message)
admin.site.register(UploadedFile)
admin.site.register(MessageURL)
