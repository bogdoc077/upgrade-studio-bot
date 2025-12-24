# 🚀 Швидкий старт на чистій ОС

## Крок 1: Завантажте скрипт і запустіть

```bash
# Підключіться до сервера
ssh root@173.242.49.209

# Завантажте скрипт
wget https://raw.githubusercontent.com/bogdoc077/upgrade-studio-bot/main/deployment/fresh_install.sh

# Зробіть його виконуваним
chmod +x fresh_install.sh

# Запустіть
./fresh_install.sh
```

## Крок 2: Налаштуйте .env

```bash
nano /opt/upgrade-studio-bot/.env
```

Додайте:
- `TELEGRAM_BOT_TOKEN` - отримайте від @BotFather
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`
- `PRIVATE_CHANNEL_ID`, `PRIVATE_CHAT_ID`, `ADMIN_CHAT_ID`
- Змініть `ADMIN_PASSWORD`

## Крок 3: Налаштуйте DNS

В панелі вашого доменного провайдера додайте:

```
Тип: A
Ім'я: admin.upgrade21.com
Значення: 173.242.49.209
TTL: 300
```

Дочекайтесь поширення DNS (5-30 хвилин):
```bash
nslookup admin.upgrade21.com
```

## Крок 4: Отримайте SSL сертифікат

```bash
certbot --nginx -d admin.upgrade21.com
```

Введіть email та погодьтесь з умовами.

## Крок 5: Запустіть сервіси

```bash
cd /opt/upgrade-studio-bot
./start_all.sh
```

## Крок 6: Перевірка

```bash
# Перевірка статусу
systemctl status nginx
curl -I https://admin.upgrade21.com

# Перегляд логів
tail -f /opt/upgrade-studio-bot/logs/*.log

# Перевірка RAM
free -h

# Перевірка процесів
ps aux | grep -E "python|node"
```

## Альтернатива: Ручне встановлення

Якщо автоматичний скрипт не підходить, дивіться [MANUAL_SETUP.md](./MANUAL_SETUP.md)

## Troubleshooting

### Nginx не запускається
```bash
nginx -t
systemctl status nginx
```

### Бот не працює
```bash
tail -100 /opt/upgrade-studio-bot/logs/bot.log
```

### SSL помилка
```bash
certbot certificates
certbot renew --dry-run
```

### MySQL помилка
```bash
systemctl status mysql
mysql -u upgrade_user -p upgrade_studio_bot
```

## Моніторинг

```bash
# Використання ресурсів
htop

# Дисковий простір
df -h

# Логи nginx
tail -f /var/log/nginx/admin.upgrade21.com.access.log
```

## Оновлення коду

```bash
cd /opt/upgrade-studio-bot
git pull
./stop_all.sh
./start_all.sh
```
