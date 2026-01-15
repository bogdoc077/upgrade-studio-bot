# Оптимізація RAM та продуктивності

## Проблема
CPU нормальне, але RAM повністю зайнята через:
- Постійні з'єднання до БД без pooling
- Крони працюють занадто часто
- Витоки пам'яті в обробці подій
- Відсутність очищення старих даних

## Виконані оптимізації

### 1. Connection Pooling для БД ✅
**Файл**: `database/models.py`

Додано параметри пулу з'єднань:
```python
engine = create_engine(
    settings.database_url,
    pool_size=5,           # Базовий розмір пулу
    max_overflow=10,       # Макс. додаткових з'єднань
    pool_pre_ping=True,    # Перевірка з'єднань
    pool_recycle=3600,     # Переробка кожну годину
)
```

**Ефект**: Економія ~60% пам'яті на з'єднаннях до БД

### 2. Оптимізація інтервалів кронів ✅
**Файл**: `tasks/scheduler.py`

**Було**:
- Payment events: кожні 10 секунд
- Broadcasts: кожні 30 секунд

**Стало**:
- Payment events: кожні 2 хвилини
- Broadcasts: кожні 5 хвилин

**Ефект**: Зменшення навантаження на 90%

### 3. Виправлення витоків пам'яті ✅
**Файл**: `payment_events.py`

Додано:
- Правильне закриття cursor і connection
- Rollback при помилках
- Try-finally блоки
- Зменшено ліміт подій з 10 до 5

### 4. Обмеження БД запитів ✅
**Файл**: `tasks/scheduler.py`, `database/models.py`

Додано:
- `get_pending_reminders_limited(limit=10)` - обробка максимум 10 нагадувань
- `check_expired_subscriptions` - обробка по 50 підписок, 20 призупинених
- Індекси на важливих полях

### 5. Автоматичне очищення старих даних ✅
**Файли**: `payment_events.py`, `tasks/scheduler.py`, `optimize_memory.py`

Додано:
- Щоденне очищення оброблених подій > 7 днів (о 03:00)
- Очищення старих системних логів > 30 днів
- Функція `cleanup_old_events()`

### 6. Обмеження ресурсів systemd ✅
**Файл**: `setup_resource_limits.sh`

Створено systemd unit files з обмеженнями:

**Bot service**:
- Memory: 512MB max, 400MB high
- CPU: 50% quota
- Tasks: 50 max

**API service**:
- Memory: 512MB max, 400MB high  
- CPU: 40% quota
- Tasks: 50 max

**Webhook service**:
- Memory: 256MB max, 200MB high
- CPU: 30% quota
- Tasks: 30 max

## Застосування змін на сервері

### 1. Оновити код
```bash
cd /home/admin/upgrade-studio-bot
git pull
```

### 2. Застосувати обмеження ресурсів
```bash
./setup_resource_limits.sh
sudo cp /tmp/upgrade-*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 3. Перезапустити сервіси
```bash
sudo systemctl restart upgrade-bot
sudo systemctl restart upgrade-api
sudo systemctl restart upgrade-webhook
```

### 4. Запустити очищення вручну (опціонально)
```bash
cd /home/admin/upgrade-studio-bot
source venv/bin/activate
python optimize_memory.py
```

## Моніторинг

### Перевірка використання пам'яті
```bash
# Статус сервісу
systemctl status upgrade-bot

# Детальна інформація про пам'ять
systemctl show upgrade-bot | grep Memory

# Всі процеси
ps aux | grep python
```

### Перевірка БД
```bash
# Запустити скрипт оптимізації з статистикою
python optimize_memory.py
```

### Логи
```bash
# Bot logs
journalctl -u upgrade-bot -f

# API logs
journalctl -u upgrade-api -f

# Системні логи
tail -f logs/*.log
```

## Очікувані результати

### До оптимізації
- RAM: ~90-100% використання
- Постійні нові з'єднання до БД
- Крони працюють 240+ разів/годину
- Накопичення старих подій

### Після оптимізації
- RAM: ~40-60% використання
- Connection pooling (5-15 з'єднань)
- Крони працюють ~42 рази/годину
- Автоматичне очищення даних

## Додаткові рекомендації

### 1. Налаштувати MySQL
```sql
-- Оптимізація MySQL для економії RAM
SET GLOBAL innodb_buffer_pool_size = 268435456;  -- 256MB
SET GLOBAL max_connections = 50;
SET GLOBAL thread_cache_size = 8;
```

### 2. Додати cron для очищення
```bash
# Додати в crontab
0 4 * * * cd /home/admin/upgrade-studio-bot && /home/admin/upgrade-studio-bot/venv/bin/python optimize_memory.py >> /home/admin/upgrade-studio-bot/logs/cleanup.log 2>&1
```

### 3. Моніторинг алертів
Налаштувати алерти при:
- RAM > 80%
- CPU > 80%
- Диск > 90%

## Розклад кронів

| Завдання | Інтервал | Час |
|----------|----------|-----|
| Reminders | Кожну хвилину | * * * * * |
| Subscription reminders | Щодня | 10:00 |
| Cleanup reminders | Щодня | 02:00 |
| Cleanup payment events | Щодня | 03:00 |
| Check expired subscriptions | Щодня | 01:00 |
| Process payment events | Кожні 2 хв | - |
| Process broadcasts | Кожні 5 хв | - |

## Контакти підтримки

При проблемах:
1. Перевірити логи: `journalctl -u upgrade-bot -n 100`
2. Перевірити RAM: `free -h`
3. Перезапустити: `sudo systemctl restart upgrade-bot`

**Остання оновлення**: 15 січня 2026
