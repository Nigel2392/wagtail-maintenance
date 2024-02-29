from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from wagtail import hooks

from . import modes
from .settings import IS_ASGI


entering_maintenance_hook = "maintenance.entering_maintenance"
exiting_maintenance_hook = "maintenance.exiting_maintenance"

if IS_ASGI:
    @hooks.register(exiting_maintenance_hook)
    def exiting_maintenance(*args, **kwargs):
        MaintenancePingConsumer.notify_of_maintenance()

    @hooks.register(entering_maintenance_hook)
    def entering_maintenance(*args, **kwargs):
        MaintenancePingConsumer.notify_of_maintenance()

class MaintenancePingConsumer(AsyncJsonWebsocketConsumer):

    # channel layer group name
    group_name = "maintenance"
    channel_layer_alias = "maintenance"

    @classmethod
    def notify_of_maintenance(cls):
        """
        Notify all connected clients of maintenance mode
        """

        if IS_ASGI:
            channel_layer       = get_channel_layer("maintenance")
            maintenance_mode    = bool(modes.is_in_maintenance())        
            # Send message to group
            async_to_sync(channel_layer.group_send)(
                cls.group_name,
                {
                    "type": "maintenance.message",
                    "maintenance_mode": maintenance_mode,
                },
            )

    @classmethod
    async def anotify_of_maintenance(cls):
        """
        Notify all connected clients of maintenance mode
        """

        channel_layer       = get_channel_layer("maintenance")
        maintenance_mode    = modes.is_in_maintenance()        

        # Send message to group
        await channel_layer.group_send(
            cls.group_name,
            {
                "type": "maintenance.message",
                "maintenance_mode": bool(maintenance_mode),
            },
        )

    async def connect(self):
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept connection
        await self.accept()

        status = modes.is_in_maintenance()

        send_dict = {
            "maintenance_mode": bool(status),
            "modes": modes.get_maintenance_dict(),
        }

        # user = self.scope["user"]
        # if user and user.is_authenticated and user.has_perm("maintenance.see_info"):
        #key_data = modes.get_maintenance_key_data(cached=status.cached)
        #send_dict["key_data"] = key_data

        await self.send_json(content=send_dict)

    async def maintenance_message(self, event):
        """
            Notify client of maintenance mode
        """
        maintenance_mode = event["maintenance_mode"]
        d = modes.get_maintenance_dict()

        send_dict = {
            "maintenance_mode": maintenance_mode,
            "modes": d,
        }

        await self.send_json(content=send_dict)

    async def receive_json(self, content, **kwargs):
        """
            Receive JSON message from client
        """

        d = modes.get_maintenance_dict()

        if "key" in content:
            key = content["key"]
            if key in d:
                status = d[key]
                return await self.send_json(content={
                    "current_mode": key,
                    "maintenance_mode": bool(status),
                    "modes": d,
                })

        return self.send_json(content={
            "maintenance_mode": bool(modes.is_in_maintenance()),
            "modes": d,
        })

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            return await super().receive(text_data, bytes_data, **kwargs)
        except Exception as e:
            return await self.send_json(content={
                "error": "An error occurred while processing your request.",
                "maintenance_mode": bool(modes.is_in_maintenance()),
            })

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
