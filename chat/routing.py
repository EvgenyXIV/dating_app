"""
Формирование пути URLconf для WebSocket-соединений для сообщений
ws/chat/                            — фиксированная часть пути для всех соединений WebSocket (ws)
(?P<room_id>\w+)                    — получение room_id
/$                                  — завершающий слэш и символ конца строки адреса
consumers.ChatConsumer.as_asgi()    - указание на получателя сообщений
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_id>\w+)/$", consumers.ChatConsumer.as_asgi()),
]
