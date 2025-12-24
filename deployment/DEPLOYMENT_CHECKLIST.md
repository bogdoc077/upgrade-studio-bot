# 🚀 Чеклист розгортання на чистій ОС

## ✅ Підготовка (5 хв)

1. **Перевірте що OS чиста**
   ```bash
   ssh root@173.242.49.209
   df -h  # Повинно бути багато вільного місця
   free -h  # RAM не перевантажений
   ps aux | grep -E "kinsing|c3pool|rsyslo"  # Немає malware
   ```

2. **Налаштуйте DNS**
   - Додайте A-запис: `admin.upgrade21.com` → `173.242.49.209`
   - Дочекайтесь поширення (5-30 хв): `nslookup admin.upgrade21.com`

## 🔧 Автоматичне встановлення (10-15 хв)

```bash
# 1. Завантажте скрипт
cd /root
wget https://raw.githubusercontent.com/bogdoc077/upgrade-studio-bot/main/deployment/fresh_install.sh

# 2. Зробіть виконуваним
chmod +x fresh_install.sh

# 3. Запустіть (це займе 10-15 хвилин)
./fresh_install.sh
```

Скрипт автоматично:
- ✅ Встановить всі пакети (Python, Node.js, Nginx, Redis)
- ✅ Налаштує firewall
- ✅ Склонує репозиторій
- ✅ Створить .env з правильними налаштуваннями
- ✅ Ініціалізує базу даних
- ✅ Зробить build admin panel
- ✅ Налаштує nginx
- ✅ Створить systemd сервіси

## 📝 Додайте секретні ключі (2 хв)

```bash
nano /opt/upgrade-studio-bot/.env
```

**Додайте:**
```env
TELEGRAM_BOT_TOKEN=ваш_токен_від_BotFather
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
ADMIN_PASSWORD=ваш_надійний_пароль
```

Збережіть: `Ctrl+O`, `Enter`, `Ctrl+X`

## 🔐 SSL Сертифікат (2 хв)

```bash
certbot --nginx -d admin.upgrade21.com
```

Введіть:
- Email для сповіщень
- `Y` - погодитись з умовами
- `N` - не діліться email

## 🚀 Запуск (1 хв)

```bash
cd /opt/upgrade-studio-bot
./start_all.sh
```

Очікуваний вивід:
```
✓ api запущено (PID: XXXX)
✓ webhook запущено (PID: XXXX)
✓ bot запущено (PID: XXXX)
✓ Admin Panel запущено (PID: XXXX)
```

## ✓ Перевірка (2 хв)

### 1. Перевірте сервіси
```bash
# Статус nginx
systemctl status nginx

# Процеси бота
ps aux | grep -E "python|node" | grep -v grep

# RAM (повинно бути < 1GB)
free -h

# Диск (повинно бути 20-30GB вільно)
df -h
```

### 2. Перевірте веб-доступ
```bash
# Перевірка HTTPS
curl -I https://admin.upgrade21.com

# Перевірка admin панелі
curl https://admin.upgrade21.com/api/health
```

### 3. Перевірте логи
```bash
# Останні 20 рядків кожного лога
tail -20 /opt/upgrade-studio-bot/logs/bot.log
tail -20 /opt/upgrade-studio-bot/logs/api.log
tail -20 /opt/upgrade-studio-bot/logs/webhook.log
tail -20 /opt/upgrade-studio-bot/logs/admin_panel.log
```

**Не повинно бути помилок!**

### 4. Перевірте бота в Telegram
- Відкрийте бота в Telegram
- Надішліть `/start`
- Повинен прийти привітальне відео та питання про цілі

### 5. Перевірте admin панель
- Відкрийте https://admin.upgrade21.com
- Логін: `admin`
- Пароль: той що встановили в .env
- Повинна відкритись панель з користувачами

## 🎯 Фінальні налаштування (опціонально)

### Налаштування Telegram Webhook
```bash
cd /opt/upgrade-studio-bot
source venv/bin/activate
python3 setup_ngrok.py  # Якщо використовуєте ngrok
# АБО webhook вже налаштований на https://admin.upgrade21.com/webhook
```

### Додати admin користувача в бот
1. Відкрийте бота
2. Надішліть `/start`
3. В admin панелі знайдіть свого користувача
4. Змініть role на `admin`

### Моніторинг
```bash
# Реалтайм моніторинг ресурсів
watch -n 2 'free -h && echo "---" && df -h && echo "---" && ps aux --sort=-%mem | head -10'

# Реалтайм логи
tail -f /opt/upgrade-studio-bot/logs/*.log
```

## 🔄 Оновлення коду в майбутньому

```bash
cd /opt/upgrade-studio-bot
git pull
./stop_all.sh
./start_all.sh
```

## ❗ Troubleshooting

### Nginx не запускається
```bash
nginx -t  # Перевірка конфігурації
systemctl status nginx
tail -50 /var/log/nginx/error.log
```

### Бот не відповідає
```bash
tail -100 /opt/upgrade-studio-bot/logs/bot.log
systemctl status upgrade-bot
```

### Admin панель не відкривається
```bash
tail -100 /opt/upgrade-studio-bot/logs/admin_panel.log
cd /opt/upgrade-studio-bot/admin-panel
npm run build  # Перебілдити
```

### База даних не підключається
```bash
# Перевірка з'єднання
mysql -h upgrade.mysql.network -P 10868 -u upgrade_studio -p upgrade_studio
# Пароль: 92vZE43Zdv
```

## 📊 Очікувані показники

- **RAM використання**: 600-800 MB (з 4GB)
- **Диск**: 10-15 GB зайнято, 20-30 GB вільно
- **CPU**: 5-15% в спокої
- **Запущені процеси**: 4 (api, webhook, bot, admin)

## ✅ Готово!

Ваш бот працює на:
- 🌐 https://admin.upgrade21.com - Admin Panel
- 💬 https://t.me/ваш_бот - Telegram Bot
- 🔗 https://admin.upgrade21.com/webhook - Webhook endpoint

**Час розгортання: ~20-25 хвилин**
