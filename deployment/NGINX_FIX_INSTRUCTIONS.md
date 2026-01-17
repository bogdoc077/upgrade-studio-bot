# Інструкція для виправлення Nginx через VNC/Serial Console

## Підключіться до сервера через VNC консоль хостинг-провайдера

## Виконайте наступні команди:

```bash
# 1. Створіть нову конфігурацію nginx
cat > /etc/nginx/sites-available/admin.upgrade21.com << 'EOF'
server {
    listen 80;
    server_name admin.upgrade21.com;
    client_max_body_size 50m;
    
    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Stripe Webhook
    location /webhook {
        proxy_pass http://localhost:8000/webhook;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 10m;
    }
    
    # Telegram Webhook  
    location /telegram-webhook {
        proxy_pass http://localhost:8000/telegram-webhook;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 10m;
    }
    
    # Admin Panel (Next.js)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 2. Перевірте конфігурацію
nginx -t

# 3. Якщо все ок, перезапустіть nginx
systemctl restart nginx

# 4. Перевстановіть SSL сертифікат (він додасть HTTPS)
certbot --nginx -d admin.upgrade21.com --non-interactive --agree-tos --email admin@upgrade21.com --redirect --force-renewal

# 5. Перевірте, що все працює
curl http://localhost:8001/api/dashboard/stats
systemctl status upgrade-api upgrade-webhook upgrade-admin
```

## Або швидкий однорядковий скрипт:

```bash
cat > /etc/nginx/sites-available/admin.upgrade21.com << 'EOF'
server {
    listen 80;
    server_name admin.upgrade21.com;
    client_max_body_size 50m;
    location /api/ { proxy_pass http://localhost:8001/api/; proxy_http_version 1.1; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme; }
    location /webhook { proxy_pass http://localhost:8000/webhook; proxy_http_version 1.1; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; client_max_body_size 10m; }
    location /telegram-webhook { proxy_pass http://localhost:8000/telegram-webhook; proxy_http_version 1.1; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; client_max_body_size 10m; }
    location / { proxy_pass http://localhost:3000; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }
}
EOF
nginx -t && systemctl restart nginx && certbot --nginx -d admin.upgrade21.com --non-interactive --agree-tos --email admin@upgrade21.com --redirect --force-renewal
```

## Що змінилося:

1. **Виправлено proxy_pass для API**: Тепер `/api/` проксується на `http://localhost:8001/api/` (додали `/api/` в кінці)
2. **Додано необхідні заголовки** для правильної роботи Next.js з API
3. **Збільшено client_max_body_size** до 50MB для завантаження файлів

## Після виправлення перевірте:

1. Відкрийте https://admin.upgrade21.com
2. Увійдіть (admin / Rr92vZE43Zdv)  
3. Перевірте сторінки: Dashboard, Broadcasts, Logs, Admins, Settings
4. Всі дані повинні завантажуватися

## Якщо SSH досі недоступний:

Проблема з SSH може бути через:
- Fail2Ban заблокував ваш IP
- MaxStartups в /etc/ssh/sshd_config обмежує підключення

Виконайте через VNC:
```bash
# Перевірити fail2ban
fail2ban-client status sshd

# Якщо ваш IP заблокований, розблокуйте:
fail2ban-client set sshd unbanip ВАШ_IP

# Або вимкніть fail2ban на час налаштування
systemctl stop fail2ban
```
