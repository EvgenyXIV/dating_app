.PHONY: up down build logs shell migrate test clean

# Запуск всех сервисов
up:
	docker-compose up --build

# Запуск в фоновом режиме
upd:
	docker-compose up --build -d

# Остановка сервисов
down:
	docker-compose down

# Пересборка и запуск
rebuild:
	docker-compose down
	docker-compose up --build

# Просмотр логов
logs:
	docker-compose logs -f web

# Просмотр логов БД
logs-db:
	docker-compose logs -f db

# Зайти в контейнер
shell:
	docker-compose exec web bash

# Выполнить миграции
migrate:
	docker-compose exec web python manage.py migrate

# Создать суперпользователя
createsuperuser:
	docker-compose exec web python manage.py createsuperuser

# Заполнить тестовыми данными
mock-data:
	docker-compose exec web python manage.py generate_mock_data --count 1000

# Запуск тестов
test:
	docker-compose exec web python manage.py test

# Очистка (осторожно!)
clean:
	docker-compose down -v
	docker system prune -f

# Проверка статуса сервисов
status:
	docker-compose ps

# Backup базы данных
backup:
	docker-compose exec db pg_dump -U postgres dating_db > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Restore базы данных
restore:
	docker-compose exec -T db psql -U postgres dating_db < $(file)

# Вывод структуры папок с файлами
tree /f
