"""
Сериализаторы для моделей ChatRoom и ChatMessage
"""

from rest_framework import serializers
from .models import ChatRoom, ChatMessage
from users.serializers import UserProfileSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(
        source="user", read_only=True
    )  # поле для отображения профиля пользователя

    class Meta:
        model = ChatMessage
        fields = ["id", "user", "user_profile", "message", "created_at", "is_read"]
        read_only_fields = ["id", "user", "created_at", "is_read"]


class ChatRoomSerializer(serializers.ModelSerializer):
    other_user = (
        serializers.SerializerMethodField()
    )  # поле для отображения данных о собеседнике, полученных в методе
    last_message = (
        serializers.SerializerMethodField()
    )  # поле для отображения последнего сообщения, полученного в методе
    unread_count = (
        serializers.SerializerMethodField()
    )  # поле для отображения количества непрочитанных сообщений, полученного в методе

    class Meta:
        model = ChatRoom
        fields = ["id", "other_user", "last_message", "unread_count", "created_at"]

    def get_other_user(
        self, obj
    ):  # функция для получения данных о пользователе, с которым идет переписка
        request = self.context.get(
            "request"
        )  # получаем объект запроса из контекста сериализатора
        other_user = (
            obj.user2 if request.user == obj.user1 else obj.user1
        )  # определяем, кто является собеседником
        return UserProfileSerializer(
            other_user
        ).data  # возвращаем сериализованные данные о пользователе

    def get_last_message(
        self, obj
    ):  # функция для получения последнего сообщения в переписке
        last_message = (
            obj.messages.last()
        )  # получаем последнее сообщение из модели ChatMessage
        return (
            ChatMessageSerializer(last_message).data if last_message else None
        )  # если сообщение есть, сериализуем его

    def get_unread_count(
        self, obj
    ):  # функция для получения количества непрочитанных сообщений
        return getattr(obj, "unread_count", 0)  # по атрибуту unread_count в комнате


class SendMessageSerializer(serializers.Serializer):
    """
    Сериализатор для отправки сообщения. Используется в ChatRoomViewSet.send_message
    """

    message = serializers.CharField(
        max_length=1000,
        min_length=1,
        trim_whitespace=True,
        help_text="Текст сообщения (обязательно)",
    )

    def __init__(
        self, *args, **kwargs
    ):  # переопределяем конструктор для добавления подсказки help_text
        super().__init__(*args, **kwargs)  # вызываем конструктор родительского класса
        context = kwargs.get("context", {})  # получаем контекст сериализатора
        view = context.get("view")  # получаем вьюсет, связанный с сериализатором
        request = context.get("request")  # получаем запрос, связанный с сериализатором

        if view and request:
            try:
                room = view.get_object()  # Получаем комнату из вьюсета
                other_user = (
                    room.user2 if request.user == room.user1 else room.user1
                )  # Определяем собеседника
                full_name = (
                    other_user.get_full_name() or other_user.email
                )  # Получаем полное имя или email собеседника
                self.fields["message"].help_text = (
                    f"Сообщение для: {full_name}"  # Добавляем подсказку help_text в поле
                )
            except:
                self.fields["message"].help_text = (
                    "Введите сообщение (получатель неизвестен)"
                )

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Сообщение не может быть пустым или состоять только из пробелов."
            )
        return value
