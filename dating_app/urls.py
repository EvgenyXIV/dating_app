"""
URL configuration for dating_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from decouple import config
import debug_toolbar  # DjDT нужен только в режиме разработки для отладки
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from users.views import CustomSignupView, UserDetailView

# Схема API для документирования API для знакомств
schema_view = get_schema_view(
    openapi.Info(
        title="Платформа знакомств API",
        default_version="v1",
        description="""
        API для платформы знакомств

                Особенности:
        - JWT аутентификация
        - Social Auth (Google, Mail.ru, Yandex)
        - Поиск партнеров по различным критериям
        - Система лайков/дизлайков, мэтчи, история
        - WebSocket чаты для мэтчей
        
                Авторизация:
        Получите JWT токен автономно через `/api/token/` и используйте в заголовках:
        -H `Authorization: Bearer <your_token>` (вводите токен с Bearer и без кавычек)
        Или
        Зарегистрируйтесь 

        """,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@datingapp.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),  # Админка
    path("api/", include("users.urls")),  # API endpoints через роутер
    path(
        "accounts/3rdparty/signup/", CustomSignupView.as_view(), name="social_signup"
    ),  # Кастомная авторизация через социальные сети 
    path(
        "accounts/", include("allauth.urls")
    ),  # Авторизация через социальные сети по встроенным формам allauth
        path("user/<int:pk>/", UserDetailView.as_view(), name="user_detail"
             
    ), # html-вывод данных пользователя
    path(
        "api-auth/", include("rest_framework.urls")
    ),  # Авторизация через REST Framework
    path("favicon.ico/", RedirectView.as_view(url="/static/favicon.ico")),
    # Swagger документация, Swagger UI схемы
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    # Выгружаем JSON/YAML схемы
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    # HTML шаблоны
    path("", TemplateView.as_view(template_name="api_root.html"), name="home"),
    path("login/", TemplateView.as_view(template_name="login.html"), name="login"),
    path("logout/", TemplateView.as_view(template_name="logout.html"), name="logout"),
    path(
        "register/",
        TemplateView.as_view(template_name="profile_register.html"),
        name="register",
    ),
    # Прямой путь для удаления аккаунта (ещё можно из API шаблона профиля пользователя)
    path(
        "unregister/",
        TemplateView.as_view(template_name="profile_unregister.html"),
        name="unregister",
    ),
]

# В режиме разработки включаем панель отладки DjDT и обслуживаем статические и медиа файлы напрямую
# (в продакшен обработка медиафайлов на стороннем сервере Nginx, Apache)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
