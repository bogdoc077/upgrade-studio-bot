# Оптимізація сервера - інструкції

## Проблема
- RAM перевантажений
- Трафік 5.30 TB/місяць (дуже багато!)
- Сервер не відповідає по SSH

## Негайні дії

### 1. Перезавантаження сервера
Через панель керування VPS-провайдера перезавантажте сервер.

### 2. Після відновлення доступу

```bash
# Підключіться до сервера
ssh root@173.242.49.209

# Перейдіть до проекту
cd /opt/upgrade-studio-bot

# Оновіть код
git pull

# Запустіть діагностику
chmod +x optimize_server.sh
./optimize_server.sh > optimization_report.txt

# Перегляньте звіт
cat optimization_report.txt
```

### 3. Застосування оптимізацій

```bash
# Застосуйте всі оптимізації
chmod +x apply_optimization.sh
./apply_optimization.sh
```

## Що робить оптимізація

### 1. **Логи (зменшення на ~80%)**
- Ротація логів: максимум 50MB на файл, 3 backups
- Автоочищення логів старше 7 днів
- Journalctl: залишаємо лише 3 дні

### 2. **Next.js (зменшення RAM на ~200MB)**
- Production build замість dev mode
- Оптимізація bundle size
- Static optimization

### 3. **Nginx (зменшення трафіку на ~60%)**
- Gzip compression (6 рівень)
- Кешування статичних файлів (30 днів)
- Rate limiting (захист від DDoS)
- Буферизація

### 4. **MySQL (зменшення RAM на ~100MB)**
- Buffer pool: 256MB замість 512MB+
- Max connections: 50 замість 151
- Query cache: 16MB
- Вимкнення slow query log

### 5. **Uploads (автоочищення)**
- Видалення broadcast файлів старше 30 днів
- Cron job щоденно о 3:00

### 6. **Systemd limits**
- Memory limit: 512MB на процес
- CPU quota: 50%

## Моніторинг після оптимізації

```bash
# Використання ресурсів
watch -n 2 'free -h && echo "---" && df -h'

# Топ процесів
watch -n 2 'ps aux --sort=-%mem | head -10'

# Трафік (якщо встановлено vnstat)
vnstat -l

# Логи nginx
tail -f /var/log/nginx/admin.upgrade21.com.access.log
```

## Очікувані результати

### RAM
- **До**: ~1.5-2GB використання
- **Після**: ~600-800MB використання
- **Економія**: ~50-60%

### Трафік
- **До**: 5.30 TB/місяць
- **Після**: ~2-3 TB/місяць (з compression + cache)
- **Економія**: ~40-50%

### Диск
- **До**: Повний (0 bytes)
- **Після**: 20-30% вільного місця
- **Економія**: через видалення старих логів та файлів

## Додаткові рекомендації

### 1. Upgrade VPS план
Якщо трафік все ще високий:
- Розглянути CDN (Cloudflare) для статичних файлів
- Збільшити RAM до 2-4GB
- Збільшити трафік ліміт

### 2. Моніторинг
Встановити моніторинг:
```bash
# Встановити netdata для моніторингу
bash <(curl -Ss https://my-netdata.io/kickstart.sh)
```

### 3. Backup
Налаштувати автоматичний backup:
```bash
# Щоденний backup бази даних
0 4 * * * mysqldump -u root upgrade_studio_bot | gzip > /backup/db_$(date +\%Y\%m\%d).sql.gz
# Видалення backup старше 7 днів
0 5 * * * find /backup -name "db_*.sql.gz" -mtime +7 -delete
```

### 4. Аналіз трафіку
Перевірити, що генерує трафік:
```bash
# Top IP адреси за запитами
awk '{print $1}' /var/log/nginx/admin.upgrade21.com.access.log | sort | uniq -c | sort -rn | head -20

# Top URL за запитами
awk '{print $7}' /var/log/nginx/admin.upgrade21.com.access.log | sort | uniq -c | sort -rn | head -20
```

## Якщо проблема повторюється

1. **DDoS атака?**
   - Перевірити логи на підозрілі IP
   - Додати Cloudflare перед сервером
   - Налаштувати fail2ban

2. **Bot активність?**
   - Перевірити User-Agent в логах
   - Заблокувати ботів в robots.txt
   - Rate limiting більш агресивний

3. **Broadcast відео?**
   - Стискати відео перед відправкою
   - Використовувати Telegram Bot API file_id замість завантаження
   - Обмежити розмір файлів

## Контакти підтримки
Якщо потрібна додаткова допомога, зв'яжіться з DevOps спеціалістом.
