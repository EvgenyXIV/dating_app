"""
Вьюсеты для чата
"""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from .models import ChatRoom, ChatMessage
from .serializers import (
    ChatRoomSerializer,
    ChatMessageSerializer,
    SendMessageSerializer,
)


class ChatRoomViewSet(viewsets.ReadOnlyModelViewSet):
    """Список чатов текущего пользователя"""

    serializer_class = ChatRoomSerializer

    def get_serializer_class(self):  # Переопределяем метод для выбора сериализатора
        if (
            self.action == "send_message"
        ):  # Выбираем сериализатор при отправке сообщения
            return SendMessageSerializer
        return super().get_serializer_class()

    def get_queryset(self):  # Переопределяем метод для фильтрации комнат
        if getattr(
            self, "swagger_fake_view", False
        ):  # Если фейковый запрос (не авториз.user) — возвращаем пустой QS
            return ChatRoom.objects.none()

        return ChatRoom.objects.filter(
            Q(user1=self.request.user)
            | Q(user2=self.request.user),  # Фильтрация по текущему пользователю
            is_active=True,  # Фильтрация по активным комнатам
        ).annotate(
            unread_count=Count(
                "messages",
                filter=Q(messages__is_read=False)
                & ~Q(messages__user=self.request.user),
            )
        )  # Добавляем атрибут unread_count для каждой комнаты - число непрочитанных сообщенй (исключаем сообщения пользователя)

    def get_serializer_context(self):  # Добавляем контекст для сериализатора
        context = super().get_serializer_context()  # Получаем контекст базовым методом
        context["request"] = (
            self.request
        )  # Добавляем текущий запрос в контекст вручную для надёжности
        return context

    @action(
        detail=True, methods=["get"]
    )  # Декоратор используется для создания дополнительных действий (options)
    def messages(
        self, request, pk=None
    ):  # Действие messages для получения сообщений комнаты
        """Получение сообщений комнаты"""
        room = self.get_object()
        messages = room.messages.all()

        # Помечаем сообщения как прочитанные
        room.messages.filter(is_read=False).exclude(user=request.user).update(
            is_read=True
        )

        # Проверяем, нужно ли выполнить пагинацию, и выполняем её, если нужно
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = ChatMessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        """Отправка сообщения в чат"""
        room = self.get_object()  # Получаем все данные о комнате и пользователе

        serializer = self.get_serializer(
            data=request.data
        )  # Создание и валидация сериализатора для отправки сообщения
        serializer.is_valid(raise_exception=True)

        message = ChatMessage.objects.create(  # Создаем сообщение
            room=room,  # Сохраняем комнату и пользователя
            user=request.user,
            message=serializer.validated_data["message"],  # Сохраняем текст сообщения
        )

        response_serializer = ChatMessageSerializer(  # Возвращаем ответ с контекстом
            message, context=self.get_serializer_context()
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
