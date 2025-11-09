# 🚀 Deployment Guide for upgrade-studio-bot

Цей гайд описує, як розгорнути upgrade-studio-bot на VPS сервері з доменом admin.upgrade21.com.

## 📋 Передумови

### 1. VPS Сервер
- **ОС**: Ubuntu 20.04+ або Debian 11+
- **RAM**: мінімум 2GB
- **Диск**: мінімум 20GB
- **CPU**: 1 ядро (рекомендовано 2+)

### 2. Домен та DNS
- Домен `admin.upgrade21.com` має бути зареєстрованим
- DNS A-запис `admin.upgrade21.com` має вказувати на IP адресу VPS
- Порти 22, 80, 443 мають бути відкриті

### 3. Доступ
- SSH доступ до сервера
- Користувач з sudo правами (НЕ root)

## 🛠️ Швидкий старт

### Крок 1: Підключення до сервера
```bash
ssh your_user@your_server_ip
```

### Крок 2: Завантаження та запуск setup скрипту
```bash
# Завантажити repository
git clone https://github.com/bogdoc077/upgrade-studio-bot.git
cd upgrade-studio-bot/deployment

# Зробити скрипти виконуваними
chmod +x *.sh

# Запустити налаштування сервера
./setup_server.sh
```

### Крок 3: Налаштування змінних оточення
Відредагуйте файл `.env` в `/opt/upgrade-studio-bot/`:
```bash
sudo nano /opt/upgrade-studio-bot/.env
```

**Обов'язково оновіть:**
- `BOT_TOKEN` - токен вашого Telegram бота
- `STRIPE_PUBLISHABLE_KEY` - Stripe publishable key
- `STRIPE_SECRET_KEY` - Stripe secret key
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook secret
- `JWT_SECRET` - секрет для JWT токенів
- `ADMIN_DEFAULT_PASSWORD` - пароль для першого адміна

### Крок 4: Налаштування Nginx та SSL
```bash
sudo ./setup_nginx.sh
```

### Крок 5: Запуск сервісів
```bash
sudo systemctl start upgrade-bot upgrade-api upgrade-admin
sudo systemctl status upgrade-bot upgrade-api upgrade-admin
```

## 🔧 Структура сервісів

### Systemd сервіси:
- **upgrade-bot** - Telegram бот (порт: внутрішній)
- **upgrade-api** - FastAPI сервер (порт: 8000)
- **upgrade-admin** - Next.js адмін панель (порт: 3000)

### Nginx конфігурація:
- **/** - Адмін панель (Next.js)
- **/api/** - API ендпоінти (FastAPI)
- **/webhook** - Telegram webhook

## 📁 Файлова структура на сервері

```
/opt/upgrade-studio-bot/
├── admin-panel/          # Next.js адмін панель
├── api/                  # FastAPI сервер
├── bot/                  # Telegram бот
├── database/             # Database утиліти
├── deployment/           # Deployment скрипти
├── venv/                # Python virtual environment
├── .env                 # Змінні оточення
└── ...
```

## 🚀 Оновлення проекту

Для розгортання оновлень використовуйте:
```bash
cd /opt/upgrade-studio-bot/deployment
sudo ./deploy.sh
```

Або для конкретної гілки:
```bash
sudo ./deploy.sh dev
```

## 📊 Моніторинг та логи

### Перевірка статусу сервісів:
```bash
sudo systemctl status upgrade-bot upgrade-api upgrade-admin
```

### Перегляд логів:
```bash
# Логи бота
sudo journalctl -u upgrade-bot -f

# Логи API
sudo journalctl -u upgrade-api -f

# Логи адмін панелі
sudo journalctl -u upgrade-admin -f

# Всі логи разом
sudo journalctl -u upgrade-bot -u upgrade-api -u upgrade-admin -f
```

### Nginx логи:
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 🔒 Безпека

### Firewall (UFW):
```bash
sudo ufw status
```

### SSL сертифікат:
```bash
sudo certbot certificates
```

### Автоматичне оновлення SSL:
```bash
sudo systemctl status certbot.timer
```

## 🛠️ Налаштування бота

1. Відкрийте адмін панель: `https://admin.upgrade21.com`
2. Увійдіть з паролем з `.env` файлу
3. Перейдіть в **Settings**
4. Налаштуйте всі необхідні параметри:
   - Bot Token
   - Stripe Keys  
   - Webhook URL: `https://admin.upgrade21.com/webhook`
   - Subscription Price

## 🚨 Troubleshooting

### Сервіси не запускаються:
```bash
# Перевірити помилки
sudo journalctl -u upgrade-bot --no-pager -n 50

# Перезапустити сервіс
sudo systemctl restart upgrade-bot
```

### Nginx помилки:
```bash
# Перевірити конфігурацію
sudo nginx -t

# Перезапустити nginx
sudo systemctl restart nginx
```

### База даних:
```bash
# Підключитися до PostgreSQL
sudo -u postgres psql upgrade_studio_bot

# Перевірити міграції
cd /opt/upgrade-studio-bot
source venv/bin/activate
python migrate_database.py
```

### Домен не працює:
```bash
# Перевірити DNS
dig admin.upgrade21.com

# Перевірити SSL
curl -I https://admin.upgrade21.com
```

## 📞 Підтримка

Якщо виникають проблеми:
1. Перевірте логи сервісів
2. Перевірте статус всіх сервісів
3. Переконайтесь, що DNS налаштовано правильно
4. Перевірте, чи всі змінні в `.env` файлі заповнені

## 🔄 Backup та відновлення

### Створення backup:
```bash
sudo mkdir -p /opt/backups
sudo cp -r /opt/upgrade-studio-bot /opt/backups/upgrade-studio-bot-$(date +%Y%m%d)

# Backup бази даних
sudo -u postgres pg_dump upgrade_studio_bot > /opt/backups/db-$(date +%Y%m%d).sql
```

### Відновлення:
```bash
# Відновити файли
sudo cp -r /opt/backups/upgrade-studio-bot-YYYYMMDD/* /opt/upgrade-studio-bot/

# Відновити базу даних
sudo -u postgres psql upgrade_studio_bot < /opt/backups/db-YYYYMMDD.sql
```