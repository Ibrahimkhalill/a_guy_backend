from django.urls import path
from . import views

urlpatterns = [
    # ChatRooms
    path("rooms/", views.chatroom_list_create, name="chatroom_list_create"),
    path("rooms/<str:uuid>/", views.chatroom_detail, name="chatroom_detail"),
    path("rooms/<str:uuid>/messages/",
         views.chatroom_detail_uuid, name="chatroom_detail_uuid"),
    # Messages
    path("messages/", views.message_list_create, name="message_list_create"),
    path("messages/<int:pk>/", views.message_detail, name="message_detail"),

    # Attachments
    path("attachments/upload/", views.upload_files, name="upload_attachments"),
]
