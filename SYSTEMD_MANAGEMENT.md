# Управління сервісами через systemd

## Переваги systemd

- **Автоматичне обмеження ресурсів**: Кожен сервіс має ліміти пам'яті та CPU
- **Автоматичний перезапуск**: При падінні сервіс перезапускається автоматично
- **Централізоване логування**: Всі логи в journalctl + файлах
- **Автозапуск**: Сервіси запускаються при перезавантаженні сервера
- **Немає дублікатів процесів**: systemd коректно завершує всі процеси

## Ліміти ресурсів

- **API Server**: 512MB RAM, 50% CPU
- **Webhook Server**: 512MB RAM, 50% CPU
- **Telegram Bot**: 512MB RAM, 50% CPU
- **Admin Panel**: 768MB RAM, 75% CPU

## Команди управління

### Запуск всіх сервісів
```bash
./start_systemd.sh
# або
sudo systemctl start upgrade-bot-{api,webhook,main,admin}
```

### Зупинка всіх сервісів
```bash
./stop_systemd.sh
# або
sudo systemctl stop upgrade-bot-{api,webhook,main,admin}
```

### Перезапуск всіх сервісів
```bash
./restart_systemd.sh
# або
sudo systemctl restart upgrade-bot-{api,webhook,main,admin}
```

### Перезапуск окремого сервісу
```bash
sudo systemctl restart upgrade-bot-api
sudo systemctl restart upgrade-bot-webhook
sudo systemctl restart upgrade-bot-main
sudo systemctl restart upgrade-bot-admin
```

## Моніторинг

### Перегляд статусу всіх сервісів
```bash
sudo systemctl status upgrade-bot-*
```

### Перегляд статусу окремого сервісу
```bash
sudo systemctl status upgrade-bot-api
```

### Перегляд використання ресурсів
```bash
sudo systemctl status upgrade-bot-* | grep -E "upgrade-bot-|Memory:|CPU:"
```

### Перегляд логів (live)
```bash
# Всі сервіси
sudo journalctl -u upgrade-bot-* -f

# Окремий сервіс
sudo journalctl -u upgrade-bot-api -f
sudo journalctl -u upgrade-bot-webhook -f
sudo journalctl -u upgrade-bot-main -f
sudo journalctl -u upgrade-bot-admin -f
```

### Перегляд останніх 100 рядків логів
```bash
sudo journalctl -u upgrade-bot-api -n 100
```

## Оновлення коду

```bash
cd /opt/upgrade-studio-bot
git pull
./restart_systemd.sh
```

## Відключення автозапуску
Якщо потрібно відключити автоматичний запуск при перезавантаженні сервера:
```bash
sudo systemctl disable upgrade-bot-{api,webhook,main,admin}
```

## Увімкнення автозапуску
```bash
sudo systemctl enable upgrade-bot-{api,webhook,main,admin}
```

## Ручний запуск (старі скрипти)
Старі скрипти `start_all.sh` та `stop_all.sh` все ще працюють, але рекомендується використовувати systemd для кращого управління ресурсами.

## Troubleshooting

### Сервіс не запускається
```bash
# Перегляд помилок
sudo journalctl -u upgrade-bot-<service> -n 50

# Перезапуск з очищенням стану
sudo systemctl reset-failed upgrade-bot-<service>
sudo systemctl restart upgrade-bot-<service>
```

### Високе споживання ресурсів
```bash
# Перегляд використання
sudo systemctl status upgrade-bot-* | grep Memory

# Якщо сервіс досяг ліміту - збільшити в конфігурації
sudo nano /etc/systemd/system/upgrade-bot-<service>.service
# Змінити MemoryLimit або CPUQuota
sudo systemctl daemon-reload
sudo systemctl restart upgrade-bot-<service>
```

### Перевірка що процеси не дублюються
```bash
ps aux | grep -E 'python.*upgrade|next-server' | grep -v grep
# Має бути тільки 4-5 процесів (по одному на сервіс + можливо worker процеси)
```
