#!/bin/bash
# Скрипт для виправлення Nginx конфігурації API

echo "🔧 Виправлення Nginx конфігурації для API..."

cat > /etc/nginx/sites-available/admin.upgrade21.com << 'EOF'
server {
    listen 80;
    server_name admin.upgrade21.com;
    
    client_max_body_size 50m;
    
    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
        
        # Handle OPTIONS requests
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS';
            add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization';
            add_header 'Access-Control-Max-Age' 1728000;
            add_header 'Content-Type' 'text/plain; charset=utf-8';
            add_header 'Content-Length' 0;
            return 204;
        }
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
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

echo "✅ Конфігурація створена"

# Перевіряємо конфігурацію
echo "🔍 Перевірка конфігурації..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Конфігурація валідна"
    echo "🔄 Перезапуск Nginx..."
    systemctl restart nginx
    
    # Перевстановлюємо SSL (він перезапише listen 80 на listen 443)
    echo "🔒 Перевстановлення SSL..."
    certbot --nginx -d admin.upgrade21.com --non-interactive --agree-tos --email admin@upgrade21.com --redirect --force-renewal
    
    echo ""
    echo "✅ Nginx конфігурацію виправлено!"
    echo ""
    echo "Перевірте API:"
    echo "  curl http://localhost:8001/api/dashboard/stats"
else
    echo "❌ Помилка в конфігурації!"
    exit 1
fi
