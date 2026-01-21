from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from chat.views import ChatRoomViewSet
from . import views

urlpatterns = [
    path("root/", views.api_root, name="api_root")
]  # Эндпойнт гл.страницы апи

# API-эндпойнты для соцсетей
urlpatterns.extend(
    [
        path(
            "auth/social/<str:provider>/login/",
            views.SocialLoginView.as_view(),
            name="social_login",
        ),
        path(
            "auth/social/<str:provider>/callback/",
            views.SocialCallbackView.as_view(),
            name="social_callback",
        ),
        path(
            "auth/jwt/callback/", views.jwt_callback_redirect_view, name="jwt_callback"
        ),
    ]
)

# API-эндпойнты
router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="user")
router.register(r"photos", views.UserPhotoViewSet, basename="photo")
router.register(r"interactions", views.InteractionViewSet, basename="interaction")
router.register(r"history", views.HistoryViewSet, basename="history")
router.register(r"matches", views.MatchViewSet, basename="match")
router.register(r"invitations", views.InvitationViewSet, basename="invitation")
router.register(
    r"contact-exchanges", views.ContactExchangeViewSet, basename="contactexchange"
)
router.register(r"chatroom", ChatRoomViewSet, basename="chatroom")

urlpatterns.extend(
    [
        path("", include(router.urls)),
        path("logout/", views.api_logout, name="api_logout"),                       # html-Выход из системы
        path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),    # Получить токены по логин/пароль (для зарегистрированных)
        path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),   # Обновить токен
        path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),      # Валидация токена
    ]
)