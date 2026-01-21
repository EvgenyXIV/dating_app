from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.db import models
from .models import User, UserPhoto, UserAction, Match, Invitation, ContactExchange
from chat.models import ChatRoom

# Для кастомизации сериалайзера TokenObtainSerializer при работе с токеном
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.serializers import (
    TokenObtainSerializer,
    TokenObtainPairSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from sys import stdout


class EmailTokenObtainPairSerializer(TokenObtainSerializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    username_field = "email"  # Поле для аутентификации по email указываем явно

    def validate(self, attrs):
        # Аутентифицируем по email
        self.user = authenticate(email=attrs["email"], password=attrs["password"])

        if not self.user:
            raise serializers.ValidationError("Неверный email или пароль")

        if not self.user.is_active:
            raise serializers.ValidationError("Аккаунт неактивен")

        # Генерация токена
        refresh = self.get_token(self.user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        return data

    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)


class UserPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPhoto
        fields = ["id", "image", "is_main", "created_at"]


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)  # Подтверждение пароля

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "password2",
            "first_name",
            "last_name",
            "gender",
            "age",
            "city",
            "hobbies",
            "status",
            "phone",
        ]

    # Проверяем валидность по входным данным attrs при регистрации пользователя
    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs

    # Создаем пользователя в БД при регистрации
    def create(self, validated_data):
        validated_data.pop(
            "password2"
        )  # Удаляем пароль2 из данных для создания пользователя
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    photos = UserPhotoSerializer(
        many=True, read_only=True
    )  # Сериализуем фотографии пользователя
    main_photo = (
        serializers.SerializerMethodField()
    )  # Создаём вычисляемое поле для главной фотографии

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "gender",
            "age",
            "city",
            "hobbies",
            "status",
            "likes_count",
            "is_private",
            "phone",
            "photos",
            "main_photo",
        ]
        read_only_fields = ["id", "email", "likes_count"]

    # Получаем главную фотографию пользователя (первую попавшуюся)
    def get_main_photo(self, obj):
        main_photo = obj.photos.filter(is_main=True).first()
        return UserPhotoSerializer(main_photo).data if main_photo else None


class UserActionToSerializer(serializers.ModelSerializer):
    """С помощью вложенного сериализатора создаём поле с данными пользователя, который отправил действие"""

    user_to_profile = UserProfileSerializer(source="user_to", read_only=True)

    class Meta:
        model = UserAction
        fields = ["id", "user_to_profile", "action_type", "created_at"]


class UserActionFromSerializer(serializers.ModelSerializer):
    """С помощью вложенного сериализатора создаём поле с данными пользователя, которому отправили действие"""

    user_from_profile = UserProfileSerializer(source="user_from", read_only=True)

    class Meta:
        model = UserAction
        fields = ["id", "user_from_profile", "action_type", "created_at"]


class MatchSerializer(serializers.ModelSerializer):
    other_user = (
        serializers.SerializerMethodField()
    )  # Создаём вычисляемое поле для другого пользователя
    chat_room_id = (
        serializers.SerializerMethodField()
    )  # Создаём вычисляемое поле для id чата

    class Meta:
        model = Match
        fields = ["id", "other_user", "chat_room_id", "created_at", "is_active"]

    def get_other_user(self, obj):
        request = self.context.get("request")
        other_user = obj.user2 if obj.user1 == request.user else obj.user1
        return UserProfileSerializer(other_user).data

    def get_chat_room_id(self, obj):
        try:
            chat_room = ChatRoom.objects.get(user1=obj.user1, user2=obj.user2)
            return chat_room.id
        except ChatRoom.DoesNotExist:
            return None


class ContactExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactExchange
        fields = [
            "id",
            "user1_contact_shared",
            "user2_contact_shared",
            "user1_phone",
            "user2_phone",
            "exchanged_at",
            "is_completed",
        ]


class InvitationSerializer(serializers.ModelSerializer):
    """Создаём поля с помощью вложенных сериалайзеров"""

    from_user_profile = UserProfileSerializer(source="from_user", read_only=True)
    to_user_profile = UserProfileSerializer(source="to_user", read_only=True)
    contact_exchange = ContactExchangeSerializer(read_only=True)

    class Meta:
        model = Invitation
        fields = [
            "id",
            "from_user_profile",
            "to_user_profile",
            "invitation_type",
            "message",
            "proposed_date",
            "proposed_location",
            "status",
            "created_at",
            "updated_at",
            "contact_exchange",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CreateInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = [
            "to_user",
            "invitation_type",
            "message",
            "proposed_date",
            "proposed_location",
        ]

    # Проверяем валидность по входным данным attrs при отправке приглашения от пользователя
    def validate(self, attrs):
        request = self.context.get(
            "request"
        )  # сохраняем контекст запроса в объекте request
        to_user = attrs.get(
            "to_user"
        )  # Из входных данных получаем пользователя, которому отправляется приглашение

        # Проверяем, что пользователь существует и это не сам пользователь
        if to_user == request.user:
            raise serializers.ValidationError(
                "Нельзя отправить приглашение самому себе"
            )

        # Проверяем, что есть актуальный мэтч между пользователями (объединяем условия мэтч в один запрос)
        if not Match.objects.filter(
            (models.Q(user1=request.user) & models.Q(user2=to_user))
            | (models.Q(user1=to_user) & models.Q(user2=request.user)),
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                "Можно отправлять приглашения только взаимным лайкам"
            )

        return attrs
