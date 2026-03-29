import json
from channels.generic.websocket import AsyncWebsocketConsumer

class LiveUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.article_id = self.scope['url_route']['kwargs']['article_id']
        self.group_name = f'live_article_{self.article_id}'

        # User ko article ke specific live room (group) mein add karein
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Room se bahar nikalein
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Jab naya update aayega toh ye function call hoga
    async def send_new_update(self, event):
        update_data = event['update_data']
        
        # Frontend ko JSON data bhej dein
        await self.send(text_data=json.dumps({
            'update_data': update_data
        }))