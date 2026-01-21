from django.apps import AppConfig
from django.db import models
from django.contrib.auth import get_user_model  # Возвращает модель пользователя

User = get_user_model()  # Сохраняем модель пользователя в переменную User


# Модель для чата tet-a-tet
class ChatRoom(models.Model):
    """Комната чата между двумя пользователями"""

    user1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_rooms_user1"
    )
    user2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_rooms_user2"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["user1", "user2"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Чат: {self.user1} & {self.user2}"


class ChatMessage(models.Model):
    """Сообщение в чате"""

    AppConfig.default = (
        False  # Для отключения автоматической регистрации модели в админке
    )
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user}: {self.message[:20]}..."
