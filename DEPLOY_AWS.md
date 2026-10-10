# Будущее развёртывание на AWS EC2 / Ubuntu

**Только инструкция. AWS платный, бесплатность EC2 не гарантируется. В рамках проекта ресурсы не создаются. Выполняйте этот раздел только после отдельного разрешения владельца и согласования бюджета.** Локальный Docker Compose не требует облачного аккаунта.

Официальные источники: [EC2 Security Groups](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules-reference.html), [SSH](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-linux-inst-ssh.html), [Docker Ubuntu](https://docs.docker.com/engine/install/ubuntu/), [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/), [Certbot](https://certbot.eff.org/).

## EC2 и доступ

1. После разрешения создайте Ubuntu 24.04 LTS x86_64 EC2, encrypted gp3 диск от 20 ГБ. Для небольшого портфолио ориентир — 2 vCPU/2–4 ГБ RAM; сборка frontend на 1 ГБ может завершиться OOM. Конкретный instance type выбирайте после проверки актуальных региональных тарифов. Не предполагайте free tier.
2. Security Group: TCP 22 только с вашего IP; TCP 80/443 с внешних адресов. Не открывайте 5432, 8000 и Docker daemon. Используйте SSH-ключ, не храните его в репозитории. Не создавайте RDS, NAT Gateway или другие оплачиваемые сервисы для этого проекта.
3. Подключение: `chmod 600 key.pem`, затем `ssh -i key.pem ubuntu@SERVER_IP`.
4. Установите обновления и Docker по официальной Ubuntu-инструкции Docker. Проверьте `docker version` и `docker compose version`. Если добавляете пользователя в группу docker, помните: она даёт root-доступ. Можно использовать `sudo docker`.
5. Установите Git, клонируйте репозиторий, `cd food_delivery`. Не копируйте локальную `.venv`, SQLite, node_modules и `.env` в образ.

## Установка Docker на Ubuntu 24.04 x86_64

Команды выполняются только на отдельно разрешённом будущем сервере. Для другой версии Ubuntu замените `noble` на её codename, для другой архитектуры — `amd64` на подходящую.

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<'DOCKER_REPO'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
DOCKER_REPO
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

Ниже команды предполагают доступ к docker без sudo; иначе используйте sudo. Клонирование: `git clone <URL-вашего-репозитория> food_delivery`, затем `cd food_delivery`. Приватный SSH deploy key храните вне репозитория и не давайте приложению AWS credentials.

## Конфигурация и запуск

```bash
cp .env.example .env
chmod 600 .env
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Сгенерируйте независимые `DJANGO_SECRET_KEY` и `POSTGRES_PASSWORD`. Установите:

```dotenv
DJANGO_DEBUG=0
DEMO_MODE=0
DJANGO_ALLOWED_HOSTS=food.example.com,localhost,127.0.0.1,backend
DJANGO_CSRF_TRUSTED_ORIGINS=https://food.example.com
DJANGO_SSL_REDIRECT=0
DJANGO_HSTS_SECONDS=0
HTTP_PORT=80
```

Замените домен на принадлежащий вам. HTTP-конфигурация нужна для первоначальной настройки сертификата; не передавайте логины по публичному HTTP. Сертификаты Let's Encrypt бесплатны, домен при необходимости приобретается отдельно только владельцем.

```bash
docker compose config --quiet
docker compose build
docker compose up -d db
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py collectstatic --noinput
docker compose run --rm backend python manage.py createsuperuser
docker compose up -d
docker compose ps
curl -f http://127.0.0.1/api/health/
```

Демоданные не создаются автоматически. Для отдельной учебной демонстрации можно явно включить DEMO_MODE и запустить seed; для настоящего production он выключен. Не переносите аккаунты с известными учебными паролями.

## Домен и HTTPS

Настройте A record существующего домена на IP EC2. Учитывайте, что публичный IPv4 AWS оплачивается; остановка instance не всегда прекращает связанные расходы.

Установите Certbot официальным способом. Для простого standalone-выпуска на сервере остановите Nginx:

```bash
docker compose stop nginx
sudo certbot certonly --standalone -d food.example.com
```

Создайте `compose.https.yaml` (не содержит секретов) в корне:

```yaml
services:
  nginx:
    ports: !override
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/https.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - /var/www/certbot:/var/www/certbot:ro
```

Требуется современный Compose v2 с `!override`. Скопируйте `nginx/https.conf.example` в `nginx/https.conf`, замените домен. До запуска проверьте наличие сертификатов. Установите `DJANGO_SSL_REDIRECT=1`, сохраните `DJANGO_HSTS_SECONDS=0` до проверки HTTPS. Внутренний health endpoint освобождён от redirect.

```bash
docker compose -f compose.yaml -f compose.https.yaml config --quiet
docker compose -f compose.yaml -f compose.https.yaml up -d
docker compose -f compose.yaml -f compose.https.yaml exec nginx nginx -t
curl -f https://food.example.com/api/health/
curl -I https://food.example.com/profile
```

После первоначального standalone-выпуска переведите renewal на webroot, чтобы не останавливать Nginx:

```bash
sudo mkdir -p /var/www/certbot
sudo certbot reconfigure --cert-name food.example.com --webroot -w /var/www/certbot
sudo certbot renew --dry-run
```

Certbot timer должен быть включён. Настройте root deploy-hook, выполняющий из абсолютного каталога проекта `docker compose -f compose.yaml -f compose.https.yaml exec -T nginx nginx -s reload`. Проверьте hook вручную. Не храните приватные ключи сертификатов в Git. После подтверждения HTTPS можно постепенно включать HSTS, например 3600 секунд; не включайте preload/includeSubDomains без понимания последствий.

WebSocket не используется приложением, поэтому upgrade proxy не нужен. Нельзя доверять произвольному внешнему X-Forwarded-Proto: Nginx переопределяет его; backend не публикуется наружу.

## Проверка, диагностика, обновления

Проверьте SPA deep links, регистрацию/вход, меню, корзину, checkout, профиль/историю, Admin и изображения. Используйте HTTPS для всех пользовательских запросов.

```bash
docker compose logs --tail=100 backend nginx db
docker compose exec backend python manage.py check --deploy
docker compose ps
docker stats --no-stream
df -h
```

Для HTTPS во всех командах Compose добавляйте `-f compose.yaml -f compose.https.yaml`. Перед обновлением сделайте backup. Затем `git pull --ff-only`, `docker compose build`, выполните миграции и collectstatic через `run --rm`, затем `up -d`. Оцените совместимость миграций со старой версией перед rolling updates. Для этого одного сервера возможен краткий простой. Rollback кода не отменяет миграции автоматически.

## Backup и восстановление

Секреты не передавайте параметрами командной строки. Пароль уже доступен внутри контейнера.

```bash
mkdir -p backups
chmod 700 backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/database.dump
docker compose exec -T backend tar -czf - -C /app media > backups/media.tar.gz
```

Храните зашифрованные копии отдельно от диска сервера. SQLite backup из старого проекта не является PostgreSQL dump. Для переноса реальных данных сперва тестируйте `dumpdata/loaddata` на отдельной БД, проверьте пользователей, отношения, sequences и media; не заменяйте существующую БД без backup.

Восстанавливайте в **новую пустую БД** для проверки, не перезаписывайте рабочую:

```bash
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" food_restore'
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d food_restore --no-owner --exit-on-error' < backups/database.dump
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d food_restore -c "SELECT count(*) FROM orders_order;"'
```

Проверив результат, планируйте переключение `POSTGRES_DB` отдельно. Media восстановите сначала в отдельный каталог и сверяйте с БД. Плановые backup/restore проверки обязательны. Не выполняйте `down -v`, не удаляйте volumes и не используйте `pg_restore --clean` без отдельного решения владельца.

## Мониторинг и расходы

Локально доступны healthchecks, stdout-логи, docker stats и дисковая статистика. Настройте log rotation Docker, контроль свободного места, ежедневные backups и проверку сертификата. Никаких платных monitoring API не требуется. Если AWS когда-либо разрешён, настройте budget alerts владельцем, но учитывайте: alerts не являются жёстким лимитом расходов. Проверяйте instance, EBS, snapshots, IPv4, трафик и ресурсы во всех регионах. Держите AWS credentials вне приложения; этому Compose AWS API не нужны.
