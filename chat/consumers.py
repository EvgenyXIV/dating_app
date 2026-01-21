"""
Доставка сообщений в реальном времени
в асинхронном режиме передачи данных от сервера к клиентам через WebSocket-соединение.
Здесь идёт беседа tet-a-tet.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatMessage

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    # Получаем ID комнаты из вложенного словаря url_route и создаём название группы
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"

        # Проверяем доступ пользователя к группе и присоединяемся к этой группе
        if await self.is_user_in_room():
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    # Отсоединяемся (удаляем канал) от группы при разрыве соединения (например, при закрытии вкладки)
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        # Получаем текст сообщения от пользователя
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Сохраняем сообщение в БД
        chat_message = await self.save_message(message)

        # Отправляем сообщение в группу
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "user_id": self.scope["user"].id,
                "username": self.scope["user"].get_full_name(),
                "message_id": chat_message.id,
                "created_at": chat_message.created_at.isoformat(),  # ISO 8601 формат YYYY-MM-DD HH:MM:SS.mmmmmmm
            },
        )

    async def chat_message(self, event):
        # Отправляем пользователю ответное сообщение WebSocket от другого пользователя,
        # event - словарь с данными сообщения
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "message_id": event["message_id"],
                    "created_at": event["created_at"],
                    "type": "chat_message",
                }
            )
        )

    @database_sync_to_async  # Декоратор для асинхронного вызова функции из модели
    def is_user_in_room(self):
        """Проверяем, принадлежность пользователя user, создавшего канал, к комнате и активность самой команты"""
        try:
            room = ChatRoom.objects.get(id=self.room_id, is_active=True)
            return self.scope["user"] in [
                room.user1,
                room.user2,
            ]  # scope - словарь со всей информацией о текущем соединении WebSocket
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async  # Декоратор для асинхронного вызова синхронной опреации с БД из модели
    def save_message(self, message):
        """Сохраняем сообщение в БД"""
        room = ChatRoom.objects.get(id=self.room_id)  # Получаем комнату по ID
        chat_message = ChatMessage.objects.create(
            room=room, user=self.scope["user"], message=message
        )  # scope - словарь со всей информацией о текущем соединении WebSocket
        return chat_message
