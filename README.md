# Тамак — доставка еды в Бишкеке

Учебный fullstack-сервис: существующий Django REST Framework backend, React/TypeScript, PostgreSQL, Docker и Nginx. Русский интерфейс, цены в сомах. Все новые рестораны вымышлены; платежи и доставка — явно обозначенные учебные симуляции. Платные API, аккаунты, карты и ключи не нужны.

## Локальный запуск без Docker

Python 3.12+, Node.js 22.13+ (актуальный Node 22 LTS). Из корня:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock.txt
cd backend
../.venv/bin/python manage.py migrate
DEMO_MODE=1 ../.venv/bin/python manage.py seed_demo
../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

В другом терминале из корня:

```bash
cd frontend
npm ci
npm run dev
```

В frontend закреплён локальный Node.js 22.23.3 как devDependency. `npm run dev`, build и тесты автоматически используют `frontend/node_modules/.bin/node`, даже если системный `node --version` показывает 18. Для чистой установки зависимостей рекомендуется Node 22.13+; если установлен nvm, выполните `nvm install && nvm use` в frontend (версия указана в `.nvmrc`). Глобальная установка Node не изменяется. Docker frontend использует Debian-based Node для совместимости с локальным бинарником.

Откройте http://localhost:5173. Vite проксирует `/api/` и `/media/` на Django. Зарегистрируйте свой аккаунт. Админ создаётся вручную: `../.venv/bin/python manage.py createsuperuser` из backend. Новых публичных паролей администратора нет.

SQLite перенесена в `backend/db.sqlite3`; её исходная резервная копия — `backups/pre-reorganization.sqlite3`. Они исключены из Git. Исходные миграции сохранены, добавлена миграция отдельной учебной оплаты. Старые пользователи и записи не удалялись: если раньше запускался старый seed, смените известные пароли существующих admin/demo вручную через `changepassword`.

## Бесплатный запуск через Docker Compose

Установите Docker Engine и Compose v2. Создайте `.env` по примеру и заполните **два разных случайных секрета**:

```bash
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Поместите результат в `DJANGO_SECRET_KEY`, повторите для `POSTGRES_PASSWORD`. Для учебной демонстрации установите `DEMO_MODE=1` в `.env`. По умолчанию production-конфигурация отключает демофункции.

```bash
docker compose config --quiet
docker compose build
docker compose up -d db
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py collectstatic --noinput
docker compose run --rm backend python manage.py seed_demo
docker compose up -d
docker compose ps
```

http://localhost:8080. Seed выполняйте только с `DEMO_MODE=1`. Самостоятельного заполнения БД при запуске нет. PostgreSQL и файлы сохраняются в volumes. Команда `docker compose down` сохраняет данные; не добавляйте `-v`.

Для hot reload Django: те же команды с `docker compose -f compose.yaml -f compose.dev.yaml`. React можно разрабатывать отдельно через Vite; Nginx в dev Compose показывает production build, а не Vite. Пересоберите frontend для обновления этой сборки.

## Структура

- `backend/`: исходные config/users/restaurants/orders, миграции, API, Admin, seed, Gunicorn.
- `frontend/src/`: API-клиент, типы, хуки, компоненты, страницы.
- `nginx/`: маршрутизация SPA/API/Admin/static/media, пример HTTPS.
- `compose.yaml`, `compose.dev.yaml`: PostgreSQL, backend, сборка React и Nginx.
- `IMPLEMENTATION_PLAN.md`, `PROGRESS.md`, `TEST_REPORT.md`, `DEPLOY_AWS.md`: план, состояние, проверки и инструкция будущего развёртывания.

## API и пользовательские сценарии

Существующие маршруты `/api/auth/register/`, `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/me/`, `/api/restaurants/`, `/api/categories/`, `/api/menu-items/`, `/api/reviews/`, `/api/cart/`, `/api/orders/` сохранены.

- Корзина: POST `/api/cart/items/`, PATCH/DELETE `/api/cart/items/{id}/`, POST `/api/cart/clear/`.
- Оформление: POST `/api/orders/checkout/`, сервер проверяет цены, доступность, ресторан и минимум, фиксирует цены и атомарно очищает корзину.
- DEMO_MODE: POST `/api/orders/{id}/demo-payment/` с `{"success":true}` или `false`; POST `/api/orders/{id}/demo-advance/` продвигает оплаченный учебный заказ на один шаг. Повтор оплаты идемпотентен. При выключенном режиме оба маршрута возвращают 404.
- Browser auth: GET `/api/auth/csrf/`, GET `/api/auth/session/`, POST `/api/auth/session/login/`, POST `/api/auth/session/register/`, POST `/api/auth/session/logout/`.
- `/api/health/`: проверяет соединение с БД и сообщает доступность деморежима.
- `/api/schema/`, `/api/schema/swagger-ui/`, `/api/schema/redoc/`: реальная схема.
- `/admin/`: штатная Django Admin.

Вход в браузере сохраняется 7 дней через серверную сессию Django и HttpOnly cookie (SameSite=Lax, Secure при production HTTPS). При обновлении React сначала восстанавливает access JWT через `/api/auth/session/`, затем открывает защищённую страницу. Access остаётся в памяти; токены не сохраняются в localStorage/sessionStorage. После истечения access выполняется одно объединённое восстановление через сессию. Выход удаляет серверную сессию и cookie. Вход, регистрация и выход браузера защищены CSRF; Axios отправляет X-CSRFToken из csrftoken cookie. Vite и Nginx сохраняют исходный Host для проверки Origin. Старые JWT endpoints работают как раньше для сторонних API-клиентов. Same-origin Vite/Nginx устраняет необходимость открывать CORS всем доменам. Для будущего отдельного origin потребуется явная allowlist. Контакты сохраняются в профиле перед checkout, адрес сохраняется в заказе.

## Проверки

```bash
cd backend
../.venv/bin/python manage.py test
../.venv/bin/python manage.py check
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/python manage.py spectacular --validate --file /tmp/schema.yaml
cd ../frontend
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
```

См. TEST_REPORT.md для фактически выполненных команд. E2E запускает свои Django/Vite серверы с отдельной временной БД; браузер установите командой `npx playwright install chromium`.

## Изображения и ограничения

Seed генерирует локальные JPEG-иллюстрации блюд средствами Pillow, без сторонних изображений или сетевых URL. Исходный генератор находится в `backend/restaurants/management/commands/seed_demo.py`; это оригинальные нейтральные изображения проекта. Деморестораны имеют 6 категорий, 13 блюд и 3 отзыва каждый. Адреса явно учебные, демо-контакты с доменом example.invalid перечислены в описании. Ресторан не содержит поля телефона; существующая схема сохранена.

Бесплатная карта Leaflet/OpenStreetMap открывается только по нажатию, с видимой атрибуцией и обычным браузерным кешированием; адрес не отправляется в геокодер. При недоступности тайлов остаётся локальный выбор учебных адресов и ручной ввод. См. [правила OSM](https://operations.osmfoundation.org/policies/tiles/). Email/SMS провайдеры и реальные курьеры не подключены; email backend — console, демо-SMS показывается внутри заказа. Статусы в учебном режиме продвигаются пользователем, в обычном — staff через API/Admin. Проверка телефона проверяет формат, не владение номером. Реальная оплата отсутствует. Перед настоящим production нужны HTTPS, аудит безопасности, тесты PostgreSQL/конкурентных операций и резервное копирование. AWS здесь только будущая инструкция: **ресурсы не создавались**.
