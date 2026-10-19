from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"^ws/telemetry/$", consumers.FleetTelemetryConsumer.as_asgi()),
]
