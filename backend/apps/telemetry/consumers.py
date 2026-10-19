import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_key):
    try:
        access = AccessToken(token_key)
        user_id = access.get("user_id")
        return User.objects.select_related("organization").get(id=user_id)
    except Exception as e:
        logger.debug("WebSocket JWT auth failed: %s", e)
        return AnonymousUser()


class FleetTelemetryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_list = params.get("token", [])
        
        user = None
        if token_list:
            user = await get_user_from_token(token_list[0])
        else:
            user = self.scope.get("user")

        if not user or not user.is_authenticated or not getattr(user, "organization", None):
            logger.warning("Rejecting unauthenticated/tenant-less WebSocket connection")
            await self.close(code=4401)
            return

        self.user = user
        self.org_group_name = f"fleet_telemetry_{str(user.organization.id)}"

        await self.channel_layer.group_add(self.org_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "org_group_name"):
            await self.channel_layer.group_discard(self.org_group_name, self.channel_name)

    async def telemetry_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))
