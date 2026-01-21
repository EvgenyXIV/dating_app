from rest_framework import viewsets, permissions
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.reverse import reverse as drf_reverse  # для получения URL-адресов эндпойнтов
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import (LoginRequiredMixin,)    # защита доступа к страницам
from django.views.generic.detail import DetailView              # для веб-интерфейса модели User (детали user)
from rest_framework_simplejwt.tokens import RefreshToken

from chat.models import ChatRoom
from .models import User, UserPhoto, UserAction, Match, Invitation, ContactExchange
from .serializers import (
    UserRegisterSerializer,
    UserProfileSerializer,
    UserPhotoSerializer,
    UserActionToSerializer,
    UserActionFromSerializer,
    MatchSerializer,
    InvitationSerializer,
    CreateInvitationSerializer,
    ContactExchangeSerializer,
)

# Для социальной авторизации
from allauth.account.utils import (
    setup_user_email,
)  # Для привязки email из соц.сети к пользователю (использует CustomSignupView)
from django.conf import (
    settings,
)  # для импорта настроек из settings.py (SECRET_KEY и др. для SimpleJWT)
from django.urls import (
    reverse,
)  # Для динамической генерации URL-адресов на основе именованных URL-шаблонов
from django.views.generic import (
    FormView,
)  # Класс представления для автоматизации пользовательского ввода
from .forms import SocialSignupForm  # Форма из dating_app\users\forms.py
from allauth.socialaccount.adapter import get_adapter  # Для работы с адаптером соц.сети
from allauth.socialaccount.models import SocialAccount
from allauth.account.utils import (
    user_email,
)  # Для получения email пользователя из соц.сети
from allauth.socialaccount.helpers import (
    complete_social_login,
)  # Для завершения соцавторизации

# Для проверки прав доступа при выводе доступных эндпойнтов на главной странице, использует api_root(request)
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from sys import stdout


FRONTEND_URL = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

# ВЬЮСЕТЫ

class UserViewSet(viewsets.ModelViewSet):
    """ViewSet для управления пользователями"""

    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    template_name = "rest_framework/api.html"  # Подключаем встроенный шаблон для html

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegisterSerializer
        return UserProfileSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]  # все могут сделать попытку авторизации
        elif self.action == "list":
            return [IsAdminUser()]  # только админы увидят список пользователей
        return [IsAuthenticated()]

    # Функция для получения объекта пользователя
    def get_object(self):
        if self.action in [
            "profile",
            "update",
            "partial_update",
        ]:  # Проверка действия в запросе
            return (
                self.request.user
            )  # Возвращается запрос текущего пользователя, независимо от id в запросе
        return (
            super().get_object()
        )  # Для остальных действий стандартное поведение функции

    # Действия 'get', 'put', 'patch' на выбор при запросе профиля пользователя
    @action(detail=False, methods=["get", "put", "patch"])
    def profile(self, request):
        """Профиль всегда текущего пользователя"""
        if request.method == "GET":
            serializer = self.get_serializer(request.user)
            return Response(
                serializer.data
            )  # Возвращаем для просмотра все данные пользователя
        elif request.method in [
            "PUT",
            "PATCH",
        ]:  # Сериализуем данные для запроса PUT (указываем все) или PATCH (можно часть)
            serializer = self.get_serializer(
                request.user,
                data=request.data,  # Получаем данные из запроса
                partial=request.method
                == "PATCH",  # Флаг для частичного обновления (True для PATCH)
            )
            serializer.is_valid(
                raise_exception=True
            )  # Валидация сериализованных данных, создаем исключение при ошибке
            serializer.save()  # Сохраняем данные в запросе
            return Response(
                serializer.data
            )  # Возвращаем обновленные данные пользователя

    @action(detail=False, methods=["get", "post"])
    def unregister(self, request):
        """Удаление аккаунта пользователя - работает с HTML шаблоном"""
        if request.method == "GET":
            # Показываем страницу удаления пользователя
            return render(request, "profile_unregister.html")

        elif request.method == "POST":
            user = request.user
            # Проверяем есть ли пароль у пользователя. Если нет, выходим из системы и удаляем user
            if not user.has_usable_password():
                logout(request)
                user.delete()
                messages.success(request, "Ваш аккаунт был успешно удален")
                return redirect("/login/")
            # Получаем пароль из HTML формы и при ошибке обновляем страницу удаления пользователя
            password = request.POST.get("password")
            if not request.user.check_password(password):
                messages.error(request, "Неверный пароль")
                return render(request, "profile_unregister.html")

            # Удаляем пользователя
            logout(request)  # Выходим из системы
            user.delete()  # Удаляем пользователя

            messages.success(request, "Ваш аккаунт был успешно удален")
            return redirect("/login/")


class UserPhotoViewSet(viewsets.ModelViewSet):
    """ViewSet для управления фотографиями пользователя"""

    serializer_class = UserPhotoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Возникает ошибка, т.к. Swagger пытается генерировать схему до аутентификации запроса,
        создаёт фейк-объект вьюсета с параметром swagger_fake_view=True и пытается отправить
        мок-запрос для получения полей ответа. Решение: метод getattr получает атрибуты запроса Swagger
        и, если запрос моковый, то подставляет ответ с пустыми полями.
        """
        if getattr(
            self, "swagger_fake_view", False
        ):  # Предотвращение запроса во время генерации Swagger
            return (
                UserPhoto.objects.none()
            )  # Возвращаем пустой набор данных для Swagger
        return UserPhoto.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InteractionViewSet(viewsets.ViewSet):
    """ViewSet для взаимодействий между пользователями"""

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get", "post"])
    def random_profile(self, request):
        """
        Получение случайного профиля с фильтрами
        B Browsable API: отображает профиль и формы для like/dislike    
        """
        excluded_actions = UserAction.objects.filter(
            user_from=request.user
        ).values_list("user_to_id", flat=True)

        queryset = User.objects.exclude(
            Q(id=request.user.id) | Q(id__in=excluded_actions) | Q(is_private=True)
        )

        # Фильтры
        gender = request.query_params.get("gender")
        min_age = request.query_params.get("min_age")
        max_age = request.query_params.get("max_age")
        city = request.query_params.get("city")
        status = request.query_params.get("status")

        if gender:
            queryset = queryset.filter(gender=gender)
        if min_age:
            queryset = queryset.filter(age__gte=int(min_age))
        if max_age:
            queryset = queryset.filter(age__lte=int(max_age))
        if city:
            queryset = queryset.filter(city__icontains=city)
        if status:
            queryset = queryset.filter(status=status)

        user = queryset.order_by("?").first()

        if not user:
            return Response(
                {"error": "Нет подходящих профилей для просмотра"}, status=404
            )

        # Логирование просмотренных профилей
        UserAction.objects.get_or_create(
            user_from=request.user, user_to=user, action_type="view"
        )

        serializer = UserProfileSerializer(user)

        # Формируем URL для like/dislike
        like_url = drf_reverse('interaction-like', kwargs={'pk': user.pk}, request=request)
        dislike_url = drf_reverse('interaction-dislike', kwargs={'pk': user.pk}, request=request)
        user_details_url = f"http://127.0.0.1:8000/user/{user.pk}/"

        # Формируем ответ (для JSON и Browsable API)
        data = {
            "user": serializer.data,
            "actions": {
                "like": {
                    "method": "POST",
                    "url": like_url,
                    "description": "Поставить лайк",
                    "help": "Перейдите на этот URL и нажмите кнопку POST, чтобы лайкнуть пользователя"
                },
                "dislike": {
                    "method": "POST",
                    "url": dislike_url,
                    "description": "Поставить дизлайк",
                    "help": "Перейдите на этот URL и нажмите кнопку POST, чтобы дизлайкнуть пользователя"
                },
                "user_details": {
                    "method": "GET",
                    "url": user_details_url,
                    "description": "Посмотреть html-профиль пользователя",
                    "help": "Перейдите на этот URL, чтобы посмотреть пользователя"
                }
            }
        }

        return Response(data)

    @action(detail=True, methods=["post"], url_path="like", url_name="like")
    def like(self, request, pk=None):
        try:
            target_user = User.objects.get(id=pk)
            user_ = target_user.get_full_name
        except User.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)

        if target_user == request.user:
            return Response({"error": "Нельзя лайкнуть себя"}, status=400)

         # Обновляем или создаём действие
        action, created = UserAction.objects.update_or_create(
            user_from=request.user, 
            user_to=target_user, 
            defaults={"action_type": "like"}
        )

        # Увеличиваем счётчик лайков только если действие изменилось на 'like' или создано
        if created or action.action_type != 'like':
            # Увеличиваем счётчик
            target_user.likes_count += 1
            target_user.save()

        mutual_like = UserAction.objects.filter(
            user_from=target_user, user_to=request.user, action_type="like"
        ).first()
        # Проверяем взаимный лайк
        if mutual_like:
            # Нормализуем порядок для поиска мэтча: user1.id всегда < user2.id (по модели Match.save())
            if request.user.id < target_user.id: 
                u1, u2 = (request.user, target_user) 
            else: 
                u1, u2 = (target_user, request.user)
            
            match, match_created = Match.objects.update_or_create(
                user1=u1, user2=u2
            )

            if match_created:
                ChatRoom.objects.get_or_create(
                    user1=request.user, user2=target_user
                )
                message = f"Лайк пользователю {user_} отправлен. Мэтч! Взаимный лайк"
                details = "Создан чат"
                is_match = match.is_active
                match_id = match.id
            else:
                message = f"Лайк пользователю {user_} отправлен. Мэтч подтверждён"
                details = "Вы ранее уже были в мэтче"
                is_match = match.is_active
                match_id = match.id
        else:
            message = f"Лайк пользователю {user_} отправлен или подтверждён"
            details = "Ожидайте взаимного лайка"
            is_match = False
            match_id = None
        return Response(
            {
                "message": message,
                "details": details,
                "is_match": is_match,
                "match_id": match_id,
            }
        )

    @action(detail=True, methods=["post"], url_path="dislike", url_name="dislike")
    def dislike(self, request, pk=None):
        try:
            target_user = User.objects.get(id=pk)
            user_ = target_user.first_name + " " + target_user.last_name
        except User.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=404)
        
        if target_user == request.user:
            return Response({"error": "Нельзя дизлайкнуть себя"}, status=400)

        # Получаем и запоминаем предыдущее действие
        previous_action = UserAction.objects.filter(
            user_from=request.user, user_to=target_user
        ).first()
        was_like = previous_action and previous_action.action_type == "like"
        was_dislike = previous_action and previous_action.action_type == "dislike"
        was_view = previous_action and previous_action.action_type == "view"

        # Нормализуем порядок для поиска мэтча: user1.id всегда < user2.id (по модели Match.save())
        if request.user.id < target_user.id: 
            u1, u2 = (request.user, target_user) 
        else: 
            u1, u2 = (target_user, request.user)
        match, match_created = Match.objects.get_or_create(
            user1=u1, user2=u2
        )

        
        # Обновляем или создаём действие
        action, created = UserAction.objects.update_or_create(
            user_from=request.user, 
            user_to=target_user, 
            defaults={"action_type": "dislike"}
        )
        # Если ранее был мэтч — проверяем и отменяем
        match = Match.objects.filter(user1=u1, user2=u2, is_active=True).first()
        if match:
            match.is_active = False
            match.save()
            message = f"Дизлайк пользователю {user_} отправлен"
            details = "Мэтч был и расторгнут"
        else:
            message = f"Дизлайк пользователю {user_} отправлен"
            details = "Мэтча не было. Действие обновлено или установлено: дизлайк"

        return Response(
            {
            "message": message,
            "details": details
            }
        )


class HistoryViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def received_likes(self, request):
        """История лайков профиля пользователя (кто лайкнул меня)"""
        likes = UserAction.objects.filter(user_to=request.user, action_type="like")
        serializer = UserActionFromSerializer(likes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def likes(self, request):
        """Список понравившихся пользователей (кого я лайкнул)"""
        likes = UserAction.objects.filter(user_from=request.user, action_type="like")
        serializer = UserActionToSerializer(likes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def dislikes(self, request):
        """Список непонравившихся пользователей (кого я дизлайкнул)"""
        dislikes = UserAction.objects.filter(
            user_from=request.user, action_type="dislike"
        )
        serializer = UserActionToSerializer(dislikes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def views(self, request):
        """История просмотренных профилей"""
        views = UserAction.objects.filter(user_from=request.user, action_type="view")
        serializer = UserActionToSerializer(views, many=True)
        return Response(serializer.data)


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(
            self, "swagger_fake_view", False
        ):  # Предотвращение запроса во время генерации Swagger
            return (
                UserPhoto.objects.none()
            )  # Возвращаем пустой набор данных для Swagger
        return Match.objects.filter(
            Q(user1=self.request.user) | Q(user2=self.request.user), is_active=True
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class InvitationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return CreateInvitationSerializer
        return InvitationSerializer

    def get_queryset(self):
        """Возникает ошибка, т.к. Swagger пытается генерировать схему до аутентификации запроса,
        создаёт фейк-объект вьюсета с параметром swagger_fake_view=True и пытается отправить
        мок-запрос для получения полей ответа. Решение: метод getattr получает атрибуты запроса Swagger
        и, если запрос моковый, то подставляет ответ с пустыми полями.
        """
        if getattr(
            self, "swagger_fake_view", False
        ):  # Предотвращение запроса во время генерации Swagger
            return (
                UserPhoto.objects.none()
            )  # Возвращаем пустой набор данных для Swagger
        return Invitation.objects.filter(
            Q(from_user=self.request.user) | Q(to_user=self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(from_user=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Принять приглашение"""
        invitation = self.get_object()

        if invitation.to_user != request.user:
            return Response(
                {"error": "Можно принимать только свои приглашения"}, status=403
            )

        if invitation.status != "pending":
            return Response({"error": "Приглашение уже обработано"}, status=400)

        invitation.status = "accepted"
        invitation.save()

        # Если это обмен контактами, создаем запись
        if invitation.invitation_type == "contact":
            ContactExchange.objects.get_or_create(invitation=invitation)

        serializer = self.get_serializer(invitation)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Отклонить приглашение"""
        invitation = self.get_object()

        if invitation.to_user != request.user:
            return Response(
                {"error": "Можно отклонять только свои приглашения"}, status=403
            )

        if invitation.status != "pending":
            return Response({"error": "Приглашение уже обработано"}, status=400)

        invitation.status = "rejected"
        invitation.save()

        serializer = self.get_serializer(invitation)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def share_contact(self, request, pk=None):
        """Поделиться контактом в обмене"""
        invitation = self.get_object()

        if invitation.status != "accepted" or invitation.invitation_type != "contact":
            return Response(
                {"error": "Нельзя поделиться контактом для этого приглашения"},
                status=400,
            )

        try:
            contact_exchange = invitation.contact_exchange
        except ContactExchange.DoesNotExist:
            contact_exchange = ContactExchange.objects.create(invitation=invitation)

        # Определяем, кто делится контактом
        if request.user == invitation.from_user:
            contact_exchange.user1_contact_shared = True
            contact_exchange.user1_phone = request.user.phone
            contact_exchange.user1_telegram = request.user.telegram
        elif request.user == invitation.to_user:
            contact_exchange.user2_contact_shared = True
            contact_exchange.user2_phone = request.user.phone
            contact_exchange.user2_telegram = request.user.telegram
        else:
            return Response({"error": "Не авторизован для этого действия"}, status=403)

        # Если обмен завершен, отмечаем время
        if contact_exchange.is_completed():
            contact_exchange.exchanged_at = timezone.now()

        contact_exchange.save()

        serializer = ContactExchangeSerializer(contact_exchange)
        return Response(serializer.data)


class ContactExchangeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ContactExchangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Возникает ошибка, т.к. Swagger пытается генерировать схему до аутентификации запроса,
        создаёт фейк-объект вьюсета с параметром swagger_fake_view=True и пытается отправить
        мок-запрос для получения полей ответа. Решение: метод getattr получает атрибуты запроса Swagger
        и, если запрос моковый, то подставляет ответ с пустыми полями.
        """
        if getattr(
            self, "swagger_fake_view", False
        ):  # Предотвращение запроса во время генерации Swagger
            return (
                UserPhoto.objects.none()
            )  # Возвращаем пустой набор данных для Swagger
        return ContactExchange.objects.filter(
            Q(invitation__from_user=self.request.user)
            | Q(invitation__to_user=self.request.user)
        )

# CBV VIEW-ПРЕДСТАВЛЕНИЯ ДЛЯ ВЕБ-ИНТЕРФЕЙСА

"""
html-карточка пользователя
"""
class UserDetailView(LoginRequiredMixin, DetailView):
    model = User    # шаблон страницы по умолчанию: dating_app\templates\users\user_detail.html
    template_name = "users/user_detail.html"  #  Задаем имя и адрес шаблона employee_detail.html для вывода информации о сотруднике
    # Получаем в карточку сотрудника главное изображение
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stdout.write(f"context: {context}")
        context["main_image"] = self.object.photos.filter(is_main=True).first() # Получаем главное фото безопасно, если его нет
        return context

"""
Представление для социальной авторизации (можно использовать параллельно jwt-соцавторизации)
"""
class CustomSignupView(FormView):
    template_name = "socialaccount/signup.html"
    form_class = SocialSignupForm

    # Переопределяем "регулировщика" запросов dispatch, добавляем:
    # -проверка сессии,
    # -прямой вход при привязанном соцаккаунте,
    # -привязка соцаккаунта по email и вход через html-форму при WEB-входе
    # -привязка соцаккаунта по email и вход минуя html-форму при JWT-входе
    def dispatch(self, request, *args, **kwargs):
        stdout.write(
            "🔄 CustomSignupView: dispatch вызван"
        )  # DEBUG ONLY удалить в продакшен

        # Получаем сохранённые в сессии данные из соцсети, если они есть
        provider = request.session.get("social_provider")
        uid = request.session.get("social_uid")
        email = request.session.get(
            "social_email"
        )  # сохранённый email в сессии при работе pre_social_login
        extra_data = request.session.get("social_extra_data")

        if not provider or not uid:
            stdout.write(
                "❌ Нет данных из соцсети в сессии"
            )  # DEBUG ONLY удалить в продакшен
            messages.error(
                request, "Сессия истекла или данные утеряны"
            )  # Сообщение в html
            return redirect("account_login")

        print("✅ Данные из соцсети найдены в сессии")  # DEBUG ONLY удалить в продакшен

        # 🔑 1. Если API-вход: пропускаем форму, входим/создаём, регистрация по jwt-токену
        if request.session.get("social_login_api"):
            # DEBUG ONLY удалить в продакшен
            stdout.write(
                "📡 API-вход: кастомная обработка (пропуск html-формы, вход и создание пользователя)"
            )

            # 1.1. Проверяем: есть ли уже привязка соцаккаунта к пользователю и, если есть, входим
            try:
                socialaccount = SocialAccount.objects.get(provider=provider, uid=uid)
                login(
                    request,
                    socialaccount.user,
                    backend="allauth.account.auth_backends.AuthenticationBackend",
                )
                stdout.write(
                    f"✅ Вход по привязанному аккаунту: {provider}"
                )  # DEBUG ONLY удалить в продакшен
                return redirect("/api/auth/jwt/callback/")
            except SocialAccount.DoesNotExist:
                stdout.write(
                    "Соцаккаунт не привязан — проверяем email"
                )  # DEBUG ONLY удалить в продакшен

            # 1.2. Проверяем: есть ли пользователь с таким email и, если есть, привязываем соцаккаунт и входим
            if email:
                try:
                    user = User.objects.get(email=email)
                    # DEBUG ONLY удалить в продакшен
                    stdout.write(
                        f"📧 Пользователь с email {email} уже существует — привязываем соцсеть"
                    )
                    # Привязываем соцаккаунт
                    SocialAccount.objects.get_or_create(
                        provider=provider,
                        uid=uid,
                        defaults={"user": user, "extra_data": extra_data},
                    )
                    login(
                        request,
                        user,
                        backend="allauth.account.auth_backends.    AuthenticationBackend",
                    )
                    stdout.write(
                        f"✅ Пользователь {user.email} вошёл, соцсеть привязана"
                    )  # DEBUG ONLY удалить в продакшен
                    return redirect("/api/auth/jwt/callback/")
                except User.DoesNotExist:
                    self.stdout.write("❌ Пользователь с таким email не найден")

            # 1.3 Создаём нового пользователя при соцавторизации с помощью кастомного адаптера users/social_adapters.py
            adapter = get_adapter()  # Получаем кастомный адаптер в объект adapter
            temp_sociallogin = type(
                "SocialLogin",
                (),
                {
                    "account": type(
                        "Account",
                        (),
                        {"provider": provider, "uid": uid, "extra_data": extra_data},
                    )(),
                    "user": None,
                },
            )  # Создаём "на лету" объект класса Sociallogin с "пустым" пользователем user

            user = adapter.new_user(
                request, temp_sociallogin
            )  # Создаём кастомного пользователя user и заполняем его роля
            user.first_name = extra_data.get("first_name", "")
            user.last_name = extra_data.get("last_name", "")
            user.email = email
            gender = extra_data.get("sex", "").lower()
            if gender == "male":
                user.gender = "M"
            elif gender == "female":
                user.gender = "F"
            user.save()

            SocialAccount.objects.create(
                user=user, provider=provider, uid=uid, extra_data=extra_data
            )  # Привязываем нового пользователя
            setup_user_email(request, user, [])

            # 1.4. Очищаем сессию (до логина - сесия наверняка ещё не будет закрыта)
            request.session.pop("social_provider", None)
            request.session.pop("social_uid", None)
            request.session.pop("social_email", None)
            request.session.pop("social_extra_data", None)
            request.session.pop("social_login_api", None)
            request.session.save()

            # 1.5. Входим
            login(
                request,
                user,
                backend="allauth.account.auth_backends.AuthenticationBackend",
            )
            stdout.write(
                f"✅ Новый пользователь {user.email} создан и вошёл в систему"
            )  # DEBUG ONLY удалить в продакшен

            return redirect("/api/auth/jwt/callback/")

        # 2. Веб-вход, регистрация без токена по паролю
        stdout.write(
            "📡 WEB-вход: кастомная обработка (вход и создание пользователя)"
        )  # DEBUG ONLY удалить в продакшен
        # 2.1. Проверяем: есть ли уже привязка соцаккаунта к пользователю и, если есть, входим
        try:
            socialaccount = SocialAccount.objects.get(
                provider=provider, uid=uid
            )  # DEBUG ONLY удалить в продакшен
            stdout.write(f"Выполняется вход по привязанному аккаунту {provider}")
            login(
                self.request,
                socialaccount.user,
                backend="allauth.account.auth_backends.AuthenticationBackend",
            )
            stdout.write(
                f"✅ Пользователь {email} вошёл в систему"
            )  # DEBUG ONLY удалить в продакшен
            return redirect("/")  # Редирект на главную страницу (пока нет фронтенда)
        except SocialAccount.DoesNotExist:
            stdout.write(
                "Соцаккаунт не привязан — проверяем email"
            )  # DEBUG ONLY удалить в продакшен

        # 2.2. Проверяем: есть ли пользователь с таким email и, если есть, привязываем соцаккаунт и входим
        if email:
            try:
                user = User.objects.get(email=email)
                # print DEBUG ONLY удалить в продакшен
                self.stdout.write(
                    f"📧 Пользователь с email {email} уже существует — привязываем соцсеть"
                )
                # Привязываем соцаккаунт
                SocialAccount.objects.get_or_create(
                    provider=provider,
                    uid=uid,
                    defaults={"user": user, "extra_data": extra_data},
                )
                login(
                    request,
                    user,
                    backend="allauth.account.auth_backends.AuthenticationBackend",
                )
                stdout.writeint(
                    f"✅ Пользователь {user.email} вошёл, соцсеть привязана"
                )  # print DEBUG ONLY удалить в продакшен
                return redirect(
                    "/"
                )  # Редирект на главную страницу (пока нет фронтенда)
            except User.DoesNotExist:
                stdout.write(
                    "❌ Пользователь с таким email не найден"
                )  # print DEBUG ONLY удалить в продакшен

        # 2.3 Показываем форму соцавторизации , зарегистрированную в settings, user/forms.py
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # Достаём данные из сессии
        extra_data = self.request.session.get("social_extra_data")

        # Создаём фейковый sociallogin для формы
        kwargs["sociallogin"] = type(
            "SocialLogin",
            (),
            {
                "account": type(
                    "Account",
                    (),
                    {
                        "provider": self.request.session.get("social_provider"),
                        "uid": self.request.session.get("social_uid"),
                        "extra_data": extra_data,
                    },
                )(),
                "user": None,
            },
        )

        return kwargs

    def form_valid(self, form):
        adapter = get_adapter()
        extra_data = self.request.session.get("social_extra_data")

        # 1. Создаём temp_sociallogin для new_user() — с user = None
        temp_sociallogin = type(
            "SocialLogin",
            (),
            {
                "account": type(
                    "Account",
                    (),
                    {
                        "provider": self.request.session.get("social_provider"),
                        "uid": self.request.session.get("social_uid"),
                        "extra_data": extra_data,
                    },
                )(),
                "user": None,
            },
        )

        # 2. Создаём пользователя
        user = adapter.new_user(self.request, temp_sociallogin)

        # 3. Устанавливаем sociallogin в форму
        form.sociallogin = type(
            "SocialLogin", (), {"account": temp_sociallogin.account, "user": user}
        )

        # 4. Заполняем пользователя кастомным методом signup() из формы SocialSignupForm
        # (email привязывается в signup())
        user = form.signup(self.request, user)

        # 5. Вручную логиним с указанием backend, так как в settings.py их указано несколько
        login(
            self.request,
            user,
            backend="allauth.account.auth_backends.AuthenticationBackend",
        )

        # 6. Очищаем сессию
        self.request.session.pop("social_provider", None)
        self.request.session.pop("social_uid", None)
        self.request.session.pop("social_extra_data", None)
        self.request.session.save()

        # print DEBUG ONLY удалить в продакшен
        stdout.write(
            f"✅ Пользователь {user.email} успешно зарегистрирован через соцсеть"
        )

        return redirect("/")  # Редирект на главную страницу (пока нет фронтенда)

    def form_invalid(self, form):
        stdout.write(
            "❌ Ошибки в форме: %s", form.errors
        )  # print DEBUG ONLY удалить в продакшен
        return super().form_invalid(form)


# SocialLoginView — делаем редирект на соцсеть (API) при соцавторизации
class SocialLoginView(APIView):
    """
    API-вход: /api/auth/social/<str:provider>/login/
    Редиректим на allauth
    """

    permission_classes = [AllowAny] 

    def get(self, request, provider):
        stdout.write(
            "🚀 API-вход: SocialLoginView вызван"
        )  # print DEBUG ONLY удалить в продакшен
        request.session["social_login_api"] = True  # Ставим флаг API-входа в сессии
        request.session["social_provider"] = (
            provider  # Указываем провайдера соцаккаунта
        )
        request.session.save()  # Сохраняем сессию
        # print DEBUG ONLY удалить в продакшен
        stdout.write(
            f"🚀 API-вход: флаги 'social_login_api'={request.session['social_login_api']}, 'social_provider'={request.session['social_provider']} установлены в сессии"
        )
        return redirect(f"/accounts/{provider}/login/?process=login")


# SocialCallbackView — завершаем API-вход с соцавторизацией
class SocialCallbackView(APIView):
    """
    Вызываем allauth после входа
    """

    permission_classes = [AllowAny]  # Разрешить всем

    def get(self, request, provider):
        if "socialaccount_state" not in request.session:  # Проверяем валидность сессии
            return redirect(f"{FRONTEND_URL}?error=session_expired")
        return complete_social_login(request)  # Завершаем подтверждение соцаккаунта


# После подтверждения соцаккаунта генерируем JWT и авторизуемся передачей токенов на html-редирект
def jwt_callback_redirect_view(request):
    """
    Вызываем после входа → генерируем JWT → редиректим на фронтенд с токенами в хеше 
    для безопасности (токены не будут переданы на сервер, ФРОНТЕНД должен читать хеши,
    чтобы увидеть токены и сохранить их)
    """
    if not request.user.is_authenticated:
        return redirect(f"{FRONTEND_URL}?error=not_authenticated")

    refresh = RefreshToken.for_user(request.user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    stdout.write(
        f"✅ JWT выдан для {request.user.email}"
    )  # print DEBUG ONLY удалить в продакшен

    # Для продакшен FRONTEND должен уметь читать хеши: js> window.location.hash,
    # сохранять токены и очищать хеш: js> window.history.replaceState({}, document.title, "/")
    redirect_url = f"{FRONTEND_URL}#token={access_token}&refresh={refresh_token}"

    return redirect(redirect_url)


# Представление-функция для главной апи-страницы 127.0.0.1:8000/api/
@api_view(["GET"])  # Из функции делаем представление
@permission_classes(
    [AllowAny]
)  #  добавляем AllowAny, IsAuthenticated уже настроен в сеттингс
@authentication_classes([SessionAuthentication, JWTAuthentication])
def api_root(request):
    """
    🎯 API Root - информация о доступных эндпоинтах
    """
    version = "1.0.0"

    # Определяем тип аутентификации
    auth_jwt = bool(
        request.successful_authenticator
        and "JWT" in str(type(request.successful_authenticator))
    )
    auth_social = bool(request.user.is_authenticated and not auth_jwt)

    endpoints = {}
    endpoints["ДЛЯ ВСЕХ авторизация/регистрация/документация"] = {
        "комбо: WEB вход по логин-пароль/WEB и JWT соцавторизация/Django-регистрация(токен не создаётся)/удаление аккаунта": {
            "method": "GET, PUT",
            "url": "/login/",
            "description": "Страница входа/регистрации/удаления аккаунта",
            "authentication_required": False,
        },
        "получить jwt-токен для заголовка headers:'Authorization': `Bearer ${token}`": {
            "method": "POST",
            "url": "/api/token/",
            "description": "Получить JWT токены (для зарегистрированных пользователей)",
            "authentication_required": False,
        },
        "вход по паролю WEB (Browsable API) токен-авторизация": {
            "method": "GET",
            "url": "/api-auth/login/",
            "description": "Вход через сессию (для зарегистрированных пользователей)",
            "authentication_required": False,
        },
        "WEB-авторизация/WEB-регистрация/WEB-авторизация через соцсети": {
            "method": "GET",
            "url": "/accounts/login/",
            "description": "WEB Вход/регистрация",
            "authentication_required": False,
        },
        "Django-регистрация": {
            "method": "POST",
            "url": "/register/",
            "description": "Django-регистрация (в сессии, токен не создаётся)",
        },
        "documentation swagger": {
            "method": "GET",
            "url": "/swagger/",
            "description": "Интерактивная документация API",
            "authentication_required": False,
        },
        "documentation redoc": {
            "method": "GET",
            "url": "/redoc/",
            "description": "Интерактивная документация API",
            "authentication_required": False,
        },
    }

    if (not auth_jwt) and (not auth_social) and (request.user.is_authenticated):
        # Базовые endpoints для django-авторизованных пользователей
        endpoints["Базовые endpoints для django-авторизованных пользователей"] = {
            "logout": {
                "method": "GET",
                "url": "/logout/",
                "description": "Выход из сессии",
            },
            "unregister": {
                "method": "POST",
                "url": "/unregister/",
                "description": "Выход из сессии",
            },
        }

    if auth_jwt or auth_social:
        # защищенные endpoints только для токен_авторизованных
        endpoints["защищенные АПИ-endpoints"] = {
            "auth_jwt refresh": {
                "method": "POST",
                "url": "/api/token/refresh/",
                "description": "Обновить JWT access токен",
                "authentication_required": False,
            },
            "drf_logout": {
                "method": "GET",
                "url": "/api/logout/",
                "description": "Выход из сессии",
                "authentication_required": False,
            },
            "profile": {
                "method": "GET,PUT,PATCH",
                "url": "/api/users/profile/",
                "description": "Профиль текущего пользователя",
            },
            "received_likes": {
                "method": "GET",
                "url": "/api/history/received_likes/",
                "description": "Кто лайкнул меня",
            },
            "random_profile": {
                "method": "GET",
                "url": "/api/interactions/random_profile/",
                "description": "Случайный профиль для оценки",
            },
            "chatroom_list": {
                "method": "GET",
                "url": "/api/chatroom/",
                "description": "Список чатов текущего пользователя",
            },
        }
        # Добавляем админские endpoints
        if request.user.is_staff or request.user.is_superuser:
            endpoints["admin"] = {
                "admin_panel": {
                    "method": "GET",
                    "url": "/admin/",
                    "description": "Панель администратора",
                },
                "user_list": {
                    "method": "GET",
                    "url": "/api/users/",
                    "description": "Список всех пользователей (только для админов)",
                },
            }

    return Response(
        {
            "version": version,
            "message": "🎯 Welcome to Dating Platform API",
            "authentication": {
                "required": True,
                "current_user": {
                    "status": (
                        "authenticated"
                        if request.user.is_authenticated
                        else "anonymous"
                    ),
                    "email": (
                        request.user.email if request.user.is_authenticated else None
                    ),
                    "is_staff": (
                        request.user.is_staff
                        if request.user.is_authenticated
                        else False
                    ),
                },
            },
            "endpoints": endpoints,
        }
    )


# Представление-функция для возможности выхода по ссылке 127.0.0.1:8000/api/logout/
@api_view(["GET"])
def api_logout(request):
    """Безопасный выход через GET — только для Browsable API"""
    logout(request)
    return Response({"detail": "Вы успешно вышли"})
