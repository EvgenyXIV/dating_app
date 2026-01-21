#!/bin/bash
# Файл для инициализации и запуска Django приложения в Docker контейнере

set -e  # Прерывать скрипт при первой ошибке

echo "=== Запуск entrypoint.sh ==="
echo "SQL_HOST: $SQL_HOST"
echo "SQL_USER: $SQL_USER"
echo "SQL_DATABASE: $SQL_DATABASE"

# Создание функции ожидания PostgreSQL
wait_for_postgres() {                       # Функция ожидания PostgreSQL
    echo "Ожидание PostgreSQL..."           # выводится сообщение
    # Пока не подключится к postgresql-client, идёт цикл. с паузой 1 сек.
    while ! pg_isready -h $SQL_HOST -U $SQL_USER; do                 # Если postgresql-client установлен в Dockerfile
    # while ! curl --silent --head --fail http://$SQL_HOST:5432; do   # Если curl установлен в Dockerfile
    # while ! nc -z $SQL_HOST 5432; do                                # Если postgresql-client, curl не установлены
        sleep 1
        echo "Ожидание PostgreSQL..."                                   # Отладочный вывод в консоли Docker
        echo "POSTGRES_HOST: "$SQL_HOST, "POSTGRES_PORT: "$SQL_PORT     # Отладочный вывод в консоли Docker
    done
    echo "POSTGRES_HOST: "$SQL_HOST, "POSTGRES_PORT: "$SQL_PORT         # Отладочный вывод в консоли Docker
    echo "PostgreSQL готов"
}

# Создание функции проверки наличия и создание пустой базы данных в случае отсутствия.
# Временный пароль PGPASSWORD автоматически очищается после выполнения команд
create_db() {
    echo "Проверка наличия базы данных $SQL_DATABASE"
    if PGPASSWORD="$SQL_PASSWORD" psql -h "$SQL_HOST" -U "$SQL_USER" -c "SELECT 1 FROM pg_database WHERE datname = '$SQL_DATABASE'" | grep -q 1; then
        echo "База данных  $SQL_DATABASE уже существует"
    else
        echo "Создание базы данных $SQL_DATABASE"
        PGPASSWORD="$SQL_PASSWORD" psql -h "$SQL_HOST" -U "$SQL_USER" -c "CREATE DATABASE $SQL_DATABASE;"
        echo $PGPASSWORD, $SQL_HOST, $SQL_USER, $SQL_PASSWORD, $SQL_DATABASE
        if [ $? -eq 0 ]; then
            echo "База данных $SQL_DATABASE успешно создана"
        else
            echo "Ошибка создания базы данных $SQL_DATABASE"
            exit 1
        fi
    fi
}

# Обработка PostgreSQL
wait_for_postgres       # Выполняется функция ожидания PostgreSQL.
create_db               # Выполняется функция проверки наличия и создания пустой базы данных в случае отсутствия.


# Выполнение миграций
python manage.py makemigrations     # Для разработки, в продакшен закомментировать(удалить)
python manage.py migrate --noinput

# # Создание суперпользователя, если не существует
# python manage.py shell -c "                     # Выполнение команд в интерпретаторе Python
# from users.models import User
# if not User.objects.filter(is_superuser=True).exists():
#     print('Суперпользователь не существует, создание...')
#     user = User.objects.create_superuser(
#         email = '$SUPERUSER_EMAIL',
#         password = '$SUPERUSER_PASSWORD',
#         first_name = '$SUPERUSER_FIRST_NAME',
#         last_name = '$SUPERUSER_LAST_NAME',
#         gender = 'M',
#         age = 30,
#         city = 'Москва'
#     )
#     print('Суперпользователь успешно создан')
# else:
#     print('Суперпользователь уже существует')
# "

# echo "Создание суперпользователя..."
# if python manage.py createsuperuser; then
#     echo "Суперпользователь успешно создан"
#     if [ "$SUPERUSER_EMAIL" != "" ] && [ "$SUPERUSER_PASSWORD" != "" ]; then
#         echo "Установка логина и пароля суперпользователя..."
#         if python manage.py createsuperuser --email "$SUPERUSER_EMAIL" --password "$SUPERUSER_PASSWORD"; then
#             echo "Логин и пароль суперпользователя успешно установлены"
#         fi
#     fi
# fi

echo "Сбор статических файлов..."
python manage.py collectstatic --noinput --clear

echo "Генерация моковых данных, в т.ч. суперюзера admin и тестового пользователя Test"
python manage.py generate_mock_data

# Запуск команды по умолчанию, задаётся в DOCKER-COMPOSE
exec "$@"