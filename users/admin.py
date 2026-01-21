from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserPhoto, UserAction, Match


# Регистриуем  в админке инлайн для изображений сотрудника в табличном виде
class UserPhotoInline(admin.TabularInline):
    model = UserPhoto
    extra = 1
    max_num = 7

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Убираем username из полей по умолчанию модели UserAdmin и добавлем поля для регистрации нового пользователя
    fieldsets = (  # Указываем все поля формы в явном виде (без username)
        (None, {"fields": ("email", "password")}),
        (
            "Личная информация",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "gender",
                    "age",
                    "city",
                    "hobbies",
                    "status",
                    "phone",
                )
            },
        ),
        (
            "Разрешения",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_verified",
                    "is_private",
                )
            },
        ),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (  # Добавляем поля для регистрации нового пользователя
        (
            None,
            {
                "classes": ("wide",),  # Для удобочитаемости широких полей
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    list_display = [
        "id",
        "email",
        "first_name",
        "last_name",
        "gender",
        "age",
        "city",
        "status",
        "is_staff",
    ]  # поля для отображения в списке админки
    list_filter = [
        "gender",
        "status",
        "is_private",
        "is_staff",
        "is_superuser",
        "is_active",
    ]  # Добавляем фильтры для списка админки
    search_fields = [
        "email",
        "first_name",
        "last_name",
        "city",
    ]  # Добавляем поля для поиска в списке админки
    ordering = [
        "email"
    ]  # Устанавливаем порядок сортировки по email (по умолчанию  было бы username)
    readonly_fields = ["last_login", "date_joined"]  # Ограничиваем редактируемые поля

    inlines = [UserPhotoInline]
    
    # # Иногда нужно переопределить поля поиска для устранения конфликта родительского поиска с отсутствием поля username
    # def get_search_fields(self, request):
    #     # Явно возвращаем поля для поиска в админке (иначе поле поиска в форме и может не отобразиться)
    #     return ["email", "first_name", "last_name", "city"]


@admin.register(UserPhoto)
class UserPhotoAdmin(admin.ModelAdmin):
    list_display = ["user", "image", "is_main"]

@admin.register(UserAction)
class UserActionAdmin(admin.ModelAdmin):
    list_display = ["user_from", "user_to", "action_type", "created_at"]


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ["user1", "user2", "created_at"]
