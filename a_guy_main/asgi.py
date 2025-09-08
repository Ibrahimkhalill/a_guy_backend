import chatbot.routing  # ✅ Now it's safe to import after `django.setup()`
import os
import django  # ✅ Import Django first
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

# ✅ Ensure Django settings are loaded before anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'a_guy_main.settings')
django.setup()  # ✅ Required to load Django apps properly


application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # ✅ Standard HTTP requests
    # ✅ WebSocket routes (No authentication required)
    "websocket": URLRouter(chatbot.routing.websocket_urlpatterns),
})
