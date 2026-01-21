from django.apps import AppConfig
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from PIL import (
    Image as PILImage,
)  # Импортируем класс Image из библиотеки PIL для обработки изображений


class UserManager(BaseUserManager):
    """Кастомный менеджер для модели User без поля username"""

    def create_user(
        self, email, password=None, **extra_fields
    ):  # Переопределяем метод create_user
        """Создание и сохранение пользователя с email и паролем"""
        if not email:
            raise ValueError("Email обязателен для заполнения")

        email = self.normalize_email(email)  # Переводим email в нижний регистр
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Хэширование пароля
        user.save(using=self._db)  # Сохранение пользователя в текущецй базе данных
        return user

    def create_superuser(
        self, email, password=None, **extra_fields
    ):  # Переопределяем метод create_superuser
        """Создание суперпользователя"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Кастомная модель пользователя для платформы знакомств"""

    GENDER_CHOICES = [
        ("M", "Мужской"),
        ("F", "Женский"),
    ]

    STATUS_CHOICES = [
        ("single", "В поиске"),
        ("relationship", "В отношениях"),
        ("married", "Женат/Замужем"),
    ]

    # Основные поля
    email = models.EmailField("email адрес", unique=True)
    first_name = models.CharField("имя", max_length=100)
    last_name = models.CharField("фамилия", max_length=100)
    gender = models.CharField("пол", max_length=15, choices=GENDER_CHOICES)
    age = models.PositiveIntegerField("возраст", default=30)
    city = models.CharField("город", max_length=100)
    hobbies = models.TextField("увлечения", blank=True)
    status = models.CharField(
        "статус отношений", max_length=50, choices=STATUS_CHOICES, default="single"
    )

    # Системные поля
    likes_count = models.PositiveIntegerField("количество лайков", default=0)
    is_private = models.BooleanField("приватный профиль", default=False)
    phone = models.CharField("телефон", max_length=50, blank=True)

    # Служебные поля
    is_verified = models.BooleanField("верифицирован", default=False)
    last_active = models.DateTimeField("последняя активность", auto_now=True)

    # Убираем username (чтобы использовать email в качестве логина)
    username = None
    # Kастомный менеджер с переопределёнными методами create_user и create_superuser
    objects = UserManager()

    USERNAME_FIELD = "email"  # В поле для входа назначаем использовать email
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "gender",
        "age",
        "city",
    ]  # Обязательные поля при создании пользователя в админке

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name


class UserPhoto(models.Model):
    """Фотографии пользователя"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="пользователь",
    )
    image = models.ImageField(
        "фотография", upload_to="user_photos/", blank=True, null=True
    )
    is_main = models.BooleanField("главная фотография", default=False)
    created_at = models.DateTimeField("дата загрузки", auto_now_add=True)

    class Meta:
        verbose_name = "фотография пользователя"
        verbose_name_plural = "фотографии пользователей"
        ordering = ["-is_main", "created_at"]   # Сначала гл.фото остальные по дате создания

    """При сохранении нового фото проверяем флаг is_main и устанвливаем единый размер фото по высоте с сохранением пропороций"""

    def save(self, *args, **kwargs):  # переопределяем метод save
        """При сохранении главного фото снимаем флаг is_main у других фото пользователя"""
        if self.is_main:
            UserPhoto.objects.filter(user=self.user, is_main=True).update(is_main=False)
        super().save(
            *args, **kwargs
        )  # вызываем родительский метод save для сохранения  фото
        
        """Устанавливаем единую высоту для всех фотографий, не меняя пропорции"""
        if self.image:
            img = PILImage.open(self.image.path)
            try:
                new_height = 300
                new_width = int(new_height * (img.width / img.height))
                img = img.resize([new_width, new_height])
                img.save(self.image.path)
                return self.image
            except Exception as e:
                raise ValidationError(f"Ошибка при изменении размера фото: {e}")

    def __str__(self):
        if self.is_main:
            return f"главное фото пользователя {self.user.get_full_name}"
        else:
            return f"Дополнительное фото пользователя {self.user.get_full_name}"


class UserAction(models.Model):
    """Действия пользователей (просмотры, лайки, дизлайки)"""

    ACTION_CHOICES = [
        ("view", "Просмотр"),
        ("like", "Лайк"),
        ("dislike", "Дизлайк"),
    ]

    user_from = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="actions_sent",
        verbose_name="от пользователя",
    )
    user_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="actions_received",
        verbose_name="пользователю",
    )
    action_type = models.CharField(
        "тип действия", max_length=20, choices=ACTION_CHOICES
    )
    created_at = models.DateTimeField("дата действия", auto_now_add=True)

    class Meta:
        verbose_name = "действие пользователя"
        verbose_name_plural = "действия пользователей"
        unique_together = ["user_from", "user_to"]      # При смене действия существующая запись обновится, а не добавится новая
        ordering = ["-created_at"]

    def __str__(self):
        action_icons = {"view": "👀", "like": "❤️", "dislike": "👎"}
        return (
            f"{self.user_from} {action_icons.get(self.action_type, '')} {self.user_to}"
        )


class Match(models.Model):
    """Взаимные лайки (совпадения) между пользователями"""

    user1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="matches_as_user1",
        verbose_name="пользователь 1",
    )
    user2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="matches_as_user2",
        verbose_name="пользователь 2",
    )
    created_at = models.DateTimeField("дата совпадения", auto_now_add=True)
    is_active = models.BooleanField("активно", default=True)

    class Meta:
        verbose_name = "совпадение"
        verbose_name_plural = "совпадения"
        unique_together = ["user1", "user2"]
        ordering = ["-created_at"]
    """
    Чтобы не дублировать мэтчи при взаимных лайках пары пользователей в разное время,
    сохраняем одну запись. Для этого переопределим save() и сохраним только один мэтч 
    с пользователями в порядке возрастания id
    """
    def save(self, *args, **kwargs):
        if self.user1.id > self.user2.id:
            self.user1, self.user2 = self.user2, self.user1
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Совпадение: {self.user1} & {self.user2}"


class Invitation(models.Model):
    """Приглашения на свидания или обмен контактами"""

    STATUS_CHOICES = [
        ("pending", "Ожидание"),
        ("accepted", "Принято"),
        ("rejected", "Отклонено"),
        ("cancelled", "Отменено"),
    ]

    TYPE_CHOICES = [
        ("randezvous", "Свидание"),
        ("contact", "Обмен контактами"),
    ]

    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
        verbose_name="от пользователя",
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_invitations",
        verbose_name="пользователю",
    )
    invitation_type = models.CharField(
        "тип приглашения", max_length=30, choices=TYPE_CHOICES
    )
    message = models.TextField("сообщение", blank=True)
    proposed_date = models.DateTimeField("предлагаемая дата", null=True, blank=True)
    proposed_location = models.CharField(
        "предлагаемое место", max_length=200, blank=True
    )
    status = models.CharField(
        "статус", max_length=30, choices=STATUS_CHOICES, default="pending"
    )
    created_at = models.DateTimeField("дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("дата обновления", auto_now=True)

    class Meta:
        verbose_name = "приглашение"
        verbose_name_plural = "приглашения"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.from_user} → {self.to_user} ({self.get_invitation_type_display()})"
        )


class ContactExchange(models.Model):
    """Безопасный обмен контактами между пользователями"""

    invitation = models.OneToOneField(
        Invitation, on_delete=models.CASCADE, verbose_name="приглашение"
    )
    user1_contact_shared = models.BooleanField(
        "пользователь 1 поделился", default=False
    )
    user2_contact_shared = models.BooleanField(
        "пользователь 2 поделился", default=False
    )
    user1_phone = models.CharField("телефон пользователя 1", max_length=50, blank=True)
    user2_phone = models.CharField("телефон пользователя 2", max_length=50, blank=True)
    exchanged_at = models.DateTimeField("дата обмена", null=True, blank=True)

    class Meta:
        verbose_name = "обмен контактами"
        verbose_name_plural = "обмены контактами"

    def __str__(self):
        return f"Обмен контактами: {self.invitation}"

    def is_completed(self):
        """Проверка, завершен ли обмен контактами"""
        return self.user1_contact_shared and self.user2_contact_shared
