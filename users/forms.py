"""
Кастомная форма allauth для завершения регистрации после входа через соцсеть (Yandex, Google и т.д.).
ДОЛЖНА содержать встроенный метод .signup(request, user), иначе allauth выдаст ошибку
ВАЖНО:
- allauth не может автоматически обработать IntegerField и ChoiceField → форма создаётся вручную
- Создаём форму на основе forms.Form и используем allauth-адаптер вручную

Поля:
- first_name, last_name — из соцсети или ввод вручную
- gender, age, city — обязательные поля в нашей модели User
- email — поле скрыто (уже пришёл из соцсети), но используется для регистрации
- password1, password2 — стандартная проверка пароля

Адаптер allauth:
- Создаёт пользователя
- Хэширует пароль
- Проверяет уникальность email
"""

from sys import stdout
from django import forms
from django.contrib.auth import get_user_model  # Получаем кастомную модель User
from allauth.account.utils import (
    setup_user_email,
)  # Для автоматической привязки email к пользователю
from allauth.socialaccount.models import SocialLogin  # Для получения данных из соцсети

# Получаем модель пользователя (в нашем случае — users.User)
User = get_user_model()


class SocialSignupForm(forms.Form):
    """
    Форма для завершения регистрации после входа через соцсеть.
    Используется, когда SOCIALACCOUNT_AUTO_SIGNUP = False.
    """

    # Основные поля профиля
    first_name = forms.CharField(max_length=100, label="Имя", required=True)
    last_name = forms.CharField(max_length=100, label="Фамилия", required=True)
    gender = forms.ChoiceField(
        choices=User.GENDER_CHOICES,  # Используем выбор из модели User: ('M', 'Мужской'), ('F', 'Женский')
        label="Пол",
        widget=forms.RadioSelect,  # Отображаем как радио-кнопки (удобно для выбора)
        required=True,
    )
    age = forms.IntegerField(
        label="Возраст",
        min_value=16,  # Минимум — 16 лет
        max_value=120,  # :)
        required=True,
    )
    city = forms.CharField(
        max_length=100,
        label="Город",
        widget=forms.TextInput(attrs={"placeholder": "Например: Москва"}),
        required=True,
    )

    # Служебные поля (не отображаются пользователю напрямую, но нужны)
    email = forms.EmailField(
        widget=forms.TextInput(
            attrs={"readonly": "readonly"}
        ),  # email показывается как readonly
        required=True,
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(),  # Поле для ввода пароля (с маскировкой)
        label="Пароль",
        required=True,
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(),  # Поле для подтверждения пароля
        label="Подтверждение пароля",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        """
        Инициализация формы.
        """
        stdout.write(
            "🔥 SocialSignupForm.__init__ вызван"
        )  # print DEBUG ONLY удалить в продакшен
        self.sociallogin = kwargs.pop("sociallogin", None)
        if self.sociallogin:
            # print DEBUG ONLY удалить в продакшен
            self.stdout.write(
                "✅ sociallogin передан:",
                self.sociallogin.account.extra_data.get("email"),
            )
        else:
            self.stdout.write(
                "❌ ОШИБКА: sociallogin НЕ передан!"
            )  # print DEBUG ONLY удалить в продакшен

        super().__init__(
            *args, **kwargs
        )  # Вызываем родительский конструктор, передавая в допустимые аргументы

        # print DEBUG ONLY удалить в продакшен
        stdout.write(
            "=== SocialSignupForm: kwargs keys ===", list(kwargs.keys())
        )  # Выводим список ключей встроенной формы авторизации

        # Если есть данные из соцсети — подставляем их как начальные значения
        extra_data = {}
        if self.sociallogin and self.sociallogin.account.extra_data:
            # print DEBUG ONLY удалить в продакшен
            self.stdout.write(
                "есть данные из соцсети — подставляем их как начальные значения"
            )
            extra_data = self.sociallogin.account.extra_data
            self.fields["first_name"].initial = extra_data.get("first_name", "")
            self.fields["last_name"].initial = extra_data.get("last_name", "")
            self.fields["gender"].initial = (
                "M" if extra_data.get("sex") == "male" else "F"
            )
            self.fields["city"].initial = "Москва..."  # или оставить пустым

        email = (
            extra_data.get("default_email")
            or extra_data.get("email")
            or extra_data.get("emails", [None])[0]
        )
        if email:
            self.fields["email"].initial = email
            self.fields["email"].widget.attrs[
                "value"
            ] = email  # Для отображения в шаблоне
            self.stdout.write(
                f"📧 Email установлен в форме: {email}"
            )  # print DEBUG ONLY удалить в продакшен
        else:
            self.stdout.write(
                "❌ Email не найден в данных соцсети"
            )  # print DEBUG ONLY удалить в продакшен

    def clean(self):
        """
        Проверка на уровне формы.
        Проверяем, что пароли совпадают.
        Остальное (email, уникальность) проверяет allauth — нам не нужно дублировать.
        """
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            # Добавляем ошибку к полю password2
            self.add_error("password2", "Пароли не совпадают")

        return cleaned_data

    def signup(self, request, user):
        """
        Обязательный метод для allauth. Вызывается после создания пользователя.
        Здесь:
        - Заполняем поля
        - Устанавливаем пароль
        - Сохраняем
        - Связываем email
        """
        # Заполняем дополнительные поля из формы
        try:
            # print DEBUG ONLY удалить в продакшен
            stdout.write(f"Заполнение дополнительных полей для пользователя {user.id}")
            user.first_name = self.cleaned_data["first_name"]
            user.last_name = self.cleaned_data["last_name"]
            user.email = self.cleaned_data["email"]
            user.gender = self.cleaned_data["gender"]
            user.age = self.cleaned_data["age"]
            user.city = self.cleaned_data["city"]
            user.set_password(self.cleaned_data["password1"])

            # СОХРАНЯЕМ ПОЛЬЗОВАТЕЛЯ — чтобы появился id - иначе ошибка остутствия id при сохранении в БД
            user.save()
            self.stdout.write(
                f"Пользователь сохранён в БД, id = {user.id}"
            )  # DEBUG ONLY удалить в продакшен

            if self.sociallogin:
                self.sociallogin.user = user
                setup_user_email(request, user, [])

            return user

        except Exception as e:
            stdout.write(
                f"Ошибка при заполнении дополнительных полей: {e}"
            )  # DEBUG ONLY удалить в продакшен
            return user
