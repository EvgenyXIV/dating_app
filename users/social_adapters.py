from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from .forms import SocialSignupForm
from django.contrib.auth import get_user_model  # Для получения кастомной модели User

from sys import stdout


User = get_user_model()  # Получаем кастомную модель User


class SocialAccountAdapter(DefaultSocialAccountAdapter):

    # переопределяем new_user для создания пользователя без username
    def new_user(self, request, sociallogin):
        """
        Создаём пользователя без username
        """
        from allauth.account.utils import user_email

        user = User()  # Используем кастомную модель
        email = sociallogin.account.extra_data.get(
            "email"
        ) or sociallogin.account.extra_data.get("default_email")
        user_email(user, email)  # Сохраняем email
        return user

    def get_signup_form(self, request, sociallogin):
        self.stdout.write("🔐 Дамп сессии:")  # DEBUG ONLY удалить в продакшен
        for key, value in request.session.items():
            stdout.write(f"  {key}: {value}")
        stdout.write(
            "🔧 Тип sociallogin:", type(sociallogin)
        )  # DEBUG ONLY удалить в продакшен
        return SocialSignupForm(
            sociallogin=sociallogin
        )  # передаём sociallogin из сессии в форму

    def populate_user(
        self, request, sociallogin, data
    ):  # переопределяем populate_user, делаем непустым
        # Проверяем входящие данные
        stdout.write(
            f"Полученные данные от соцсети: {data}"
        )  # DEBUG ONLY удалить в продакшен
        stdout.write(
            f"Extra data: {sociallogin.account.extra_data}"
        )  # DEBUG ONLY удалить в продакшен

        """
        Создаём и заполняем пользователя, используя кастомную модель из new_user() и extra_data
        """
        user = self.new_user(request, sociallogin)

        try:
            extra_data = sociallogin.account.extra_data
            user.first_name = extra_data.get("first_name", "").strip()
            user.last_name = extra_data.get("last_name", "").strip()
            # Email: из нескольких возможных полей
            user.email = (
                extra_data.get("default_email")
                or extra_data.get("email")
                or extra_data.get("emails", [None])[0]
                or ""
            ).strip()

            # Обработка пола
            gender = extra_data.get("sex", "").lower()
            if gender == "male":
                user.gender = "M"
            elif gender == "female":
                user.gender = "F"

            return user
        except Exception as e:
            stdout.write(
                f"Ошибка при заполнении полей: {str(e)}"
            )  # DEBUG ONLY удалить в продакшен
            return user

    def pre_social_login(self, request, sociallogin):
        """
        Сохраняем ВСЁ, что нужно, в сессию вручную — без зависимости от allauth
        """
        self.stdout.write(
            "🔥 pre_social_login: вызван"
        )  # DEBUG ONLY удалить в продакшен
        extra_data = sociallogin.account.extra_data
        stdout.write(f"extra_data= {extra_data}")

        # Принудительно сохраняем нужные данные в сессию
        request.session["social_provider"] = sociallogin.account.provider
        request.session["social_uid"] = sociallogin.account.uid
        request.session["social_extra_data"] = extra_data  # все данные

        # Сохраняем email в сессии — важно для входа существующего пользователя
        email = (
            extra_data.get("default_email")
            or extra_data.get("email")
            or extra_data.get("emails", [None])[0]
        )
        if email:
            request.session["social_email"] = email
            # DEBUG ONLY удалить в продакшен
            stdout.write(
                f"📧 Email сохранён в сессии: {email} {request.session['social_email']}"
            )

        request.session.save()
        # DEBUG ONLY удалить в продакшен
        stdout.write("✅ Данные соцсети сохранены вручную в сессию")
        stdout.write(
            f"👤 Пользователь: {extra_data.get('first_name')} {extra_data.get('last_name')}"
        )

    def is_auto_signup_allowed(self, request, sociallogin):
        # Всегда False иначе регистрация сорвётся из-за отсутсвия user в sociallogin (подстраховка)
        return False

    # Устанавливаем флаг выбора способа входа: WEB-вход или JWT-вход
    def get_login_redirect_url(self, request):
        # Если JWT-вход — редиректим на FRONTEND_URL с передачей через хеш в заголовке токенов
        if request.session.get("social_login_api"):
            return "/api/auth/jwt/callback/"
        # Если WEB-вход - Кастомная соцрегистрация
        return "/accounts/3rdparty/signup/"
