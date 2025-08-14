"""
ASGI config for elearning project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django

# Configure settings early
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning.settings')

# Initialize Django so apps/models can be imported safely
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Build the HTTP app first (this also ensures Django is fully ready)
django_asgi_app = get_asgi_application()

# Import routing AFTER Django is set up to avoid AppRegistryNotReady
import chat.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
            )
        )
    ),
})
