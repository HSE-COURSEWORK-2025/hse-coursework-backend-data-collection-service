# HSE Coursework: Data Collection API

## Описание

Этот репозиторий содержит сервис сбора и предоставления пользовательских данных. Сервис агрегирует данные из различных источников, сохраняет их в базе данных и предоставляет обработанные данные. Также сервис имеет возможность интеграции со сторонними системами путем передачи данных пользователя в FHIR-формате.


![](https://github.com/HSE-COURSEWORK-2025/hse-coursework-backend-data-collection-service/blob/master/swagger_demo.png)

## Основные возможности
- Приём и отправка на обработку сырых данных пользователя. На обработку данные отправляются путем отправки в очередь Kafka, из которой читает данные сервис [обработки данных](https://github.com/HSE-COURSEWORK-2025/hse-coursework-drammatiq-data-collector)

- Выдача обработанных данных, найденных выбросов и прогнозов ML-модели
- Трансляция прогресса выгрузки данных
- Выгрузка данных в FHIR-формате


## Структура проекта

- `app/` — основной код приложения
  - `api/` — роутеры FastAPI (v1, root)
  - `models/` — Pydantic-схемы
  - `services/` — бизнес-логика, работа с БД, Kafka, Redis, FHIR
  - `settings.py` — глобальные настройки приложения
- `deployment/` — манифесты Kubernetes (Deployment, Service)
- `requirements.txt` — зависимости Python
- `Dockerfile` — сборка Docker-образа
- `launcher.py`, `launch_app.sh` — запуск приложения

## Быстрый старт (локально)

1. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Создайте файл `.env` или используйте `.env.development`**
3. **Запустите приложение:**
   ```bash
   python launcher.py
   ```
   или через Uvicorn:
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

4. **(Опционально) Запустите Kafka и Redis локально:**
   ```bash
   docker-compose -f kafka-local-docker-compose.yaml up -d
   ```

## Переменные окружения

- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — OAuth2 Google
- `GOOGLE_REDIRECT_URI` — URI для редиректа Google OAuth
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` — параметры БД
- `REDIS_HOST`, `REDIS_PORT` — параметры Redis
- `KAFKA_BOOTSTRAP_SERVERS` — адрес Kafka
- `SECRET_KEY` — секрет для подписи JWT
- `ROOT_PATH`, `PORT` — путь и порт приложения
- `DOMAIN_NAME` — домен для формирования ссылок

Пример `.env`:
```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
ROOT_PATH=/data-collection-api
PORT=8080
DB_HOST=localhost
...
```

## Сборка и запуск в Docker

```bash
docker build -t awesomecosmonaut/data-collection-api-app .
docker run -p 8080:8080 --env-file .env awesomecosmonaut/data-collection-api-app
```

## Деплой в Kubernetes

1. Соберите и отправьте образ:
   ```bash
   ./deploy.sh
   ```
2. Остановить сервис:
   ```bash
   ./stop.sh
   ```
3. Манифесты находятся в папке `deployment/` (Deployment, Service)

## Метрики и документация
- Swagger UI: `/data-collection-api/docs`
- OpenAPI: `/data-collection-api/openapi.json`
- Метрики Prometheus: `/data-collection-api/metrics`
