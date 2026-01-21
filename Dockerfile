FROM python:3.12-slim

WORKDIR /usr/src/dating_app

# Запрещаем копирование файлов .pyc и .pyo, которые создаются при компиляции
ENV PYTHONDONTWRITEBYTECODE=1
# Запрещаем вывод stdout stderr для логов 
ENV PYTHONUNBUFFERED=1

# Установка системных зависимостей
# gcc                           Пакет может понадибиться для компиляции C/C++ - приложений
# libpq-dev                     Пакет разработки для PostgreSQL (нужен для psycopg2)
# postgresql-client             Клиентские утилиты PostgreSQL (нужны для создания базы данных)
# netcat-openbsd                Пакет для тестирования сетевого взаимодействия и доступа к портам
# rm -rf /var/lib/apt/lists/*   Очищаем кэш apt после установки
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
# Копирование requirements (без кэширования для устойчивости работы приложений) и установка Python зависимостей
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копирование всего проекта (в т.ч. entrypoint.sh)
COPY . .

# Создание директории для медиа файлов
RUN mkdir -p /usr/src/dating_app/media/user_photos

# в среде Linux для совместимости после правки entrypoint.sh в Windows
RUN sed -i 's/\r$//g' /usr/src/dating_app/entrypoint.sh

# Сделать entrypoint исполняемым
RUN chmod +x /usr/src/dating_app/entrypoint.sh

# Точка входа
ENTRYPOINT ["/usr/src/dating_app/entrypoint.sh"]

# Команда по умолчанию
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
