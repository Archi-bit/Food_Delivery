# Отчёт проверок — 8 октября 2026, Бишкек

## Фактически выполнено

| Проверка | Результат |
|---|---|
| Исходный backend до переноса | 29 тестов, OK |
| Backend после переноса, SQLite | Последний полный прогон: 40 cases, 38 OK, 2 PostgreSQL-only проверки пропущены |
| Backend на локальной PostgreSQL 16.15 | 40 cases полного прогона — OK; дополнительный UploadTests (1 case) — OK |
| PostgreSQL конкурентность | Два параллельных добавления сохраняют quantity=2; два checkout создают один заказ, второй получает 400 |
| Seed | Два отдельных теста: идемпотентность, неизменность исходного ресторана, количество файлов/записей, отсутствие staff/паролей, запрет вне DEMO_MODE — OK |
| Сохранность исходной SQLite | Все 107 исходных записей всех таблиц с id сверены с резервной копией: содержимое не изменилось |
| Django check | 0 ошибок |
| Миграции | migrate выполнен; makemigrations --check --dry-run: No changes detected |
| OpenAPI | spectacular --validate и HTTP /api/schema/: OK |
| Django static | collectstatic: 154 файла |
| Production security check | DEBUG=0, HTTPS flags: только ожидаемый security.W004 — HSTS намеренно 0 до настройки HTTPS |
| Python зависимости | pip check: No broken requirements found; версии сохранены в requirements.lock.txt |
| TypeScript | npm run typecheck и tsc в production build: OK |
| ESLint | npm run lint: OK |
| Frontend unit/API-client tests | 14 Vitest cases, 2 файла, OK |
| Production build | Vite 8.3.4: OK; карта загружается отдельным lazy chunk |
| npm audit | После финальных зависимостей: 0 vulnerabilities |
| Playwright Chromium | 4 сценария, desktop и Pixel 7: OK; последний прогон 13.3 секунды |
| Gunicorn | Реальный запуск DEBUG=0: health, каталог, schema, admin/login отвечают 200 |
| React production preview | Реальный запуск собранного React: /, /restaurants/1 и /profile отвечают SPA HTML |
| Compose YAML | Оба файла разобраны PyYAML, сервисы/структура корректны на уровне YAML |

Полные backend-прогоны включают регистрацию/JWT, permissions, поиск/сортировку меню, отзывы, корзину, ограничения количества, checkout, минимальную сумму/закрытый ресторан/недоступные блюда, фиксацию стоимости, защиту чужих данных, профиль без повышения привилегий, token refresh, demo payment/доставку и seed. Дополнительная upload-проверка подтверждает отклонение GIF аватара. PostgreSQL использовалась из отдельного локального кластера внутри backend/.test-data, порт 55432; это не Docker PostgreSQL.

JWT frontend-тесты проверяют Bearer, отсутствие token storage, refresh, обновление auth/me, ограничение повторных 401 и отсутствие восстановления сессии после выхода. UI-тесты проверяют loading/error/данные, alt/fallback изображений и сом.

Playwright проверяет регистрацию → выход → JWT-вход → каталог/поиск → меню → добавление → корзину → контакты/адрес → checkout → demo payment → продвижение статуса → историю → отзыв. Дополнительно проверены сортировка, пагинация, пустое состояние и отсутствие горизонтального переполнения. Ошибка сети тайлов карты симулируется локально; выбор локального адреса продолжает работать. Автоматические тесты не обращаются к тайлам OSM. Снимки каталогов и ресторанов сохранены в frontend/test-results, проверены визуально. Это не полноценный аудит WCAG или всех браузеров.

## Исправленные ошибки во время проверок

- Ошибка TypeScript на разном типе Axios mutation ответа — исправлена.
- Node 18 не совместим с актуальными tools; проверки переведены на Node 22.23.3, требование Node 22.13+ задокументировано.
- Обнаруженные npm audit уязвимости старого Vitest устранены обновлением.
- Отсутствующие optional native Vite bindings установлены; последующая сборка прошла.
- Мобильный профиль с длинным username перекрывал кнопку выхода — layout исправлен, повторный Playwright прошёл.
- JWT refresh ошибочно исключал auth/me — исправлено и покрыто отдельным тестом.
- Nginx теперь сохраняет HTTP Host вместе с портом, чтобы media URL корректно работали на localhost:8080.

## Не выполнено и почему

- `docker compose config`, Docker build/up и контейнерные healthchecks: Docker отсутствует (`docker: command not found`). YAML-парсинг не заменяет Compose validation.
- `nginx -t`, фактический Nginx proxy/static/media, volumes и HTTPS: Nginx отсутствует; конфигурации подготовлены, требуют проверки в Docker.
- PostgreSQL 17 из Compose не запускалась; фактические PostgreSQL-тесты выполнены на доступной локальной версии 16.
- Выпуск/renewal Let's Encrypt, AWS deploy, реальные расходы: не выполнялись; нет разрешения на облачные ресурсы.
- Доступность внешних OSM тайлов не гарантируется и не проверялась ботом; проверен offline fallback.
- Нет Safari/Firefox, нагрузочного теста, полного security/WCAG-аудита, restore drill на Docker volumes.

## Повторение

Команды локальных проверок — в README. Для полного production smoke после Playwright: `NODE_BINARY=node .venv/bin/python scripts/smoke_production.py` из корня. Scripts используют отдельные данные, не исходную SQLite. Запускайте backend-тесты из backend: запуск manage.py test из корня без app labels может найти 0 тестов. PostgreSQL-only concurrency tests на SQLite пропускаются намеренно.

## Проверка исправления Node.js

После ошибки styleText на системном Node 18.19.1 установлен проектный node@22.23.3. Без дополнительного PATH запущены npm run build, npm run lint и npm test: все прошли, 14 тестов OK. Обычный npm run dev с отдельным тестовым портом 15175 вывел Vite ready; несовместимость runtime устранена. Docker build stage изменён на Debian-based Node; Docker-сборка по-прежнему не проверена из-за отсутствия Docker.

## Сохранение входа после обновления страницы

- Полный backend-прогон SQLite: 50 cases, OK, 2 ожидаемых PostgreSQL-only skips.
- 9 новых browser-session тестов: постоянная HttpOnly cookie на 7 дней, повторное получение access, регистрация, Secure HTTPS cookies, CSRF для login/register/logout, запрет чужого Origin, неактивный пользователь, отзыв сессии и запрет replay после выхода. После добавления no-store повторно выполнен целевой набор.
- Frontend: 18 unit/API-client тестов OK; TypeScript/production build/ESLint OK.
- Playwright: 4 desktop/mobile сценария OK (14.4 сек.), дополнены обновлением профиля после регистрации, обновлением корзины после JWT-входа и обновлением после выхода. Cookie HttpOnly проверена через browser context.
- OpenAPI валидируется; новых модельных миграций нет. Старые JWT endpoints сохранены.
- При первом E2E выявлен отказ CSRF из-за Host rewrite в Vite; proxy changeOrigin=false исправил Origin/Host, повторный прогон прошёл.
- Для этой доработки PostgreSQL/Docker/Nginx отдельно не проверялись. Требуется перезапустить Vite после изменения его конфигурации и войти один раз для создания постоянной сессии.

## Фильтры категорий еды

- `.venv/bin/python backend/manage.py test restaurants orders users --verbosity 1`: 54 cases, OK (52 passed, 2 ожидаемых PostgreSQL-only skips). Новые проверки: доступность блюда, категория/название, кириллица, отсутствие дубликатов, сохранение рейтинга, совместный поиск/open, все пять категорий, десерты с чизкейком, очистка и неизвестный slug (400).
- `npm run build --prefix frontend`, `npm run lint --prefix frontend`, `npm test --prefix frontend`: OK, TypeScript и production build прошли, 18 tests passed.
- OpenAPI: `manage.py spectacular --validate` OK, новый параметр документируется автоматически.
- Первый полный Playwright запуск: прежние 4 сценария прошли; 2 новых обнаружили ошибку ожидания теста («Маргарита» относится к категории пиццы, но не содержит слово «Пицца»). Проверка исправлена с учётом названия и регистра.
- Повторный `npm run test:e2e --prefix frontend -- --grep 'Категории еды'`: 2 passed (6.2 сек.). Реальные Django/Vite API, desktop/mobile: 2 различных меню → выбор пиццы оставляет 1 ресторан → reload сохраняет выбор → лагман меняет ресторан → «Все» возвращает 2; проверены все категории блюд, сброс страницы и чизкейк в десертах.
- E2E данные создавались только в `backend/.test-data/e2e.sqlite3`, рабочая база не изменялась. PostgreSQL/Docker/Nginx для этой доработки не запускались.

## Поиск ресторанов без учёта регистра

- `.venv/bin/python backend/manage.py test restaurants orders users --verbosity 1`: 59 cases, OK (57 passed, 2 ожидаемых PostgreSQL-only skips), 28.244 сек.
- 5 новых backend-тестов: нижний/верхний/смешанный регистр кириллицы, подстроки, пробелы, описания, блюда/категории, сочетание с food_category/open/ordering/page, отсутствие ложного совпадения по % и _, Unicode «ё» и Café.
- `npm run test:e2e --prefix frontend -- --grep 'Поиск ресторана'`: 2 passed (4.5 сек.), desktop/mobile. Все варианты «базилик и тесто» находят один и тот же ресторан через реальный API; сочетание с пиццей и обновление страницы проверены. База изолирована, пользовательские данные не изменялись.
- `npm run lint --prefix frontend` и `manage.py spectacular --validate`: OK. Frontend application code не менялся, изменены только E2E проверки; production build для этой доработки повторно не запускался.
- PostgreSQL/Docker/Nginx для этой доработки не запускались.
