from sys import stdout
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.hashers import make_password   # Для хеширования паролей
from django.db import connection                        # Для очистки базы перед заполнением моковыми данными
from django.utils import timezone                       # Для создания даты создания пользователя
from django.core.exceptions import ValidationError 
from psycopg2.extras import execute_values              # Для пакетного создания записей в БД

from io import StringIO
import random
from users.models import User, UserAction, Match, UserPhoto
from chat.models import ChatRoom

# Для обработки изображений (создание иконки платформы знакомств, ресайз фото пользователей) 
from PIL import Image
from dating_app import settings
import os
import uuid                                             # Для генерации уник.идентификат. для фото


# Очистка таблиц, включая связанные, и сброс последовательностей первичного ключа
with connection.cursor() as cursor:
    stdout.write(f"Очистка таблиц{'\n'}")
    tables = [
        "users_user",
        "users_userphoto",
        "socialaccount_socialaccount",
        #   "token_blacklist_blacklistedtoken",
        #   "token_blacklist_outstandingtoken"
    ]
    for table in tables:
        cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
        cursor.execute(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1")
stdout.write(f"таблицы {tables} очищены{'\n'}")


# сброс последовательностей первичного ключа в таблицах указанных django-приложений
def reset_id_sec():
    output = StringIO()
    apps = ["users", "chat", "socialaccount", "token_blacklist"]
    call_command("sqlsequencereset", apps, stdout=output)
    sql = output.getvalue()
    with connection.cursor() as cursor:
        cursor.execute(sql)
    return stdout.write(f"Первичные ключи в приложениях {apps} сброшены{'\n'}")


reset_id_sec()

# Создаём иконку приложения
stdout.write("Создаём иконку приложения...\n")
favicon_ico = os.path.join(settings.BASE_DIR, "static", "favicon.ico")
favicon_jpg = os.path.join(settings.BASE_DIR, "static", "favicon.jpg")
if not os.path.exists(favicon_ico):
    try:
        img = Image.open(favicon_jpg)
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        img.save(favicon_ico, format="ICO", sizes=[(64, 64), (32, 32), (16, 16)])
        stdout.write("favicon.ico успешно создан\n")
    except Exception as e:
        stdout.write(f"Ошибка при создании favicon: {e}\n")
else:
    stdout.write("favicon.ico уже существует\n")


class Command(BaseCommand):
    help = "Генерация тестовых данных для платформы знакомств"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=3000,
            help="Количество пользователей для создания",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Очистить существующие данные"
        )

    def handle(self, *args, **options):
        """Создание или получение суперпользователя с id=1, ORM методом create_superuser"""
        self.stdout.write("Создание или получение суперпользователя admin@admin.ru")

        User.objects.create_superuser(  # Создаем суперпользователя методом create_superuser
            email="admin@admin.ru",
            password="password",  # Пароль вводится в виде строки, но будет хеширован методом make_password
            first_name="admin",
            last_name="admin",
            gender="M",
            age=30,
            city="Москва",
        )
        self.stdout.write("Создан суперпользователь admin@admin.ru / password с id=1")

        # # 100% вариант создания уникального суперюзера:
        # # Безопасно при нескольких запусках
        # # Не создаёт дубликатов
        # # Если пользователь уже есть — просто обновляются права
        # # Создание или получение суперпользователя с id=1, с принудительным хешированием пароля и назначением вручную всех прав
        # try:
        #     admin, created = User.objects.get_or_create(
        #         email="admin@admin.ru",
        #         defaults={
        #             'first_name': 'admin',
        #             'last_name': 'admin',
        #             'gender': 'M',
        #             'age': 30,
        #             'city': 'Москва',
        #             'is_staff': True,
        #             'is_superuser': True,
        #         }
        #     )
        #     if created:
        #         admin.set_password('password')
        #         admin.save()
        #         self.stdout.write(self.style.SUCCESS('✅ Суперпользователь admin@admin.ru создан'))
        #     else:
        #         self.stdout.write('Суперпользователь уже существует. Обновляем права...')

        #     # --- НАЗНАЧАЕМ ВСЕ ПРАВА НА ВСЕ МОДЕЛИ ---
        #     from django.contrib.auth.models import Permission

        #     self.stdout.write('Назначение ВСЕХ прав на ВСЕ модели суперпользователю...')

        #     # Получаем ВСЕ права в системе
        #     all_perms = Permission.objects.all()

        #     # Назначаем пользователю
        #     admin.user_permissions.set(all_perms)
        #     admin.save()

        #     self.stdout.write(
        #     "Создан суперпользователь admin@admin.ru / password с id=1"
        #     )
        #     self.stdout.write(
        #         f'✅ Назначено {all_perms.count()} прав на ВСЕ модели'
        #     )

        # except Exception as e:
        #     self.stdout.write(self.style.ERROR(f'Ошибка при настройке суперпользователя: {e}'))
        # self.stdout.write(
        #     "Создан суперпользователь admin@admin.ru / password с id=1"
        # )

        """Создание тестового пользователя с id=2, ORM методом create_user"""
        self.stdout.write(
            "Создание тестового пользователя"
        )  # Выводим сообщение в консоль
        User.objects.create_user(
            email="test@test.ru",
            password="password",  # будет хеширован автоматически
            first_name="Test",
            last_name="User",
            gender="M",
            age=30,
            city="Москва",
            hobbies="путешествия, кофе, книги",
            status="single",
            phone="+79001234567",
            is_active=True,
        )
        self.stdout.write(
            "Создан тестовый пользователь: test@test.ru / password с id=2"
        )  # Выводим сообщение в консоль

        """Создание остальных пользователей через пакетный SQL запрос"""
        count = 101
        genders = [gend[0] for gend in User.GENDER_CHOICES]
        self.stdout.write(f"genders {genders}")
        statuses = [stat[0] for stat in User.STATUS_CHOICES]
        self.stdout.write(f"statuses {statuses}")
        cities = ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань"]
        hobbies_ = [
            "Путешествия,фотография,кулинария",
            "Спорт,музыка,чтение",
            "Кино,видеоигры,программирование",
            "Танцы,пение,рисование",
            "Йога,медитация,вегетарианство",
            "Автомобили,мотоциклы,техника",
            "Наука,IT,новые технологии",
            "Искусство,театр,музеи",
            "Природа,походы,рыбалка",
            "Бизнес,инвестиции,саморазвитие",
            "",
        ]

        self.stdout.write(f"Создание {count-3} дополнительных пользователей...")
        users = []
        for i in range(3, count):  # count-2 новых пользователей
            first_name = f"user_{i}"
            last_name = first_name
            password = make_password("password")  # Хешируем пароль
            email = f"{first_name}@example.com"  # Создаем email для теста
            gender = random.choice(genders)
            age = random.randint(18, 65)
            city = random.choice(cities)
            hobbies = random.choice(hobbies_).split(", ")
            status = random.choice(statuses)
            phone = f'{first_name}-phone: "pnone-number"'
            date_joined = f"{timezone.now()}"  # Дата создания пользователя
            last_active = f"{timezone.now()}"

            """Пополняем список кортежей с данными пользователей"""
            users.append(
                (
                    first_name,
                    last_name,
                    password,
                    email,
                    gender,
                    age,
                    city,
                    hobbies,
                    status,
                    phone,
                    date_joined,
                    last_active,
                    False,  # is_verified
                    None,  # last_login
                    False,  # is_staff
                    False,  # is_superuser
                    True,  # is_active
                    False,  # is_private
                    0,  # likes_count
                )
            )

        with connection.cursor() as cursor:
            # Используем 1 SQL запрос для пакетного создания пользователей со значениями полей из списка кортежей users
            # с помощью параметризованного запроса VALUES %s, который принимает список кортежей users
            # Работает функция execute_values из psycopg2.extras
            # !Все обязательные поля (NOT NULL), кроме id, должны быть заполнены! при SQL запросе
            execute_values(
                cursor,
                """
                INSERT INTO users_user(
                first_name,
                last_name,
                password,
                email,
                gender,
                age,
                city,
                hobbies,
                status,
                phone,
                date_joined,
                last_active,
                is_verified,
                last_login,
                is_staff,
                is_superuser,
                is_active,
                is_private,
                likes_count
                )
                VALUES %s
                RETURNING id
            """,
                users,  # Список кортежей с данными пользователей
            )
            user_ids = [
                row[0] for row in cursor.fetchall()
            ]  # Получаем список id пользователей для создания сборов и платежей
        self.stdout.write(
            f"Создано {len(user_ids)} пользователей, для всех пароль password"
        )  # Выводим сообщение в консоль

        # Создаем фотографии пользователей пакетным SQL запросом
        self.stdout.write("Создание фото пользователей...")
        photos = []
        image_path = os.path.join(settings.MEDIA_ROOT, "user_photos", "default_avatar.jpg")
        
        if not os.path.exists(image_path):
            self.stdout.write("ERROR: Файл default_avatar.jpg не найден")
            return
        try:
            img = Image.open(image_path)

            # Устанавливаем высоту 300px, сохраняем пропорции
            new_height = 300
            new_width = int(new_height * img.width / img.height)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        except Exception as e:
            raise ValidationError(f"Ошибка при обработке фото: {e}")
        for user_id in user_ids:
            for i in range(random.randint(1, 5)):
                # Генерируем уникальное имя фото
                photo_uuid = "default_avatar" + uuid.uuid4().hex
                filename = f"user_photos/{photo_uuid}.jpg"   # Путь для БД

                # Сохраняем изменённое изображение
                img.save(os.path.join(settings.MEDIA_ROOT, filename))
                
                user_id = user_id
                is_main = i == 0
                created_at = timezone.now()
                # created_at = f"{timezone.now()}"

                """Пополняем список кортежей с данными фото пользователей"""
                photos.append((user_id, filename, is_main, created_at))
        with connection.cursor() as cursor:
            # Используем 1 SQL запрос для пакетного создания пользователей со значениями полей из списка кортежей users
            # с помощью параметризованного запроса VALUES %s, который принимает список кортежей users
            # Работает функция execute_values из psycopg2.extras
            # !Все обязательные поля (NOT NULL), кроме id, должны быть заполнены! при SQL запросе
            execute_values(
                cursor,
                """
                INSERT INTO users_userphoto(
                user_id,
                image,
                is_main,
                created_at
                )
                VALUES %s
                RETURNING id
            """,
                photos,  # Список кортежей с данными фото пользователей
            )
            photo_ids = [
                row[0] for row in cursor.fetchall()
            ]  # Получаем список id фото пользователей
        self.stdout.write(
            f"Создано {len(photo_ids)} фото пользователей"
        )  # Выводим сообщение в консоль

        """Создание взаимных лайков и мэтчей"""
        self.stdout.write("Создание взаимных лайков и мэтчей...")
        self.create_matches()

    def create_matches(self):
        """Создание взаимных лайков и мэтчей. ORM метод get_or_create() исключает дублирование пар пользователей"""
        all_users = list(User.objects.all())

        for i in range(min(50, len(all_users) // 2)):
            user1 = random.choice(all_users)
            user2 = random.choice(all_users)

            if user1 != user2:
                # Создаем взаимные лайки
                UserAction.objects.get_or_create(
                    user_from=user1, user_to=user2, action_type="like"
                )

                UserAction.objects.get_or_create(
                    user_from=user2, user_to=user1, action_type="like"
                )

                # Создаем мэтч
                match, created = Match.objects.get_or_create(user1=user1, user2=user2)

                if created:
                    # Создаем чат комнату
                    ChatRoom.objects.get_or_create(user1=user1, user2=user2)
