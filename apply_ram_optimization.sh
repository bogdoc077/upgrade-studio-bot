#!/bin/bash

# Скрипт для швидкого застосування всіх оптимізацій RAM

set -e

echo "🚀 Застосування оптимізацій RAM..."
echo ""

# Кольори
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функція для виведення кроків
step() {
    echo -e "${BLUE}►${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

error() {
    echo -e "${RED}❌${NC} $1"
}

# Перевіряємо чи ми на сервері
if [ ! -d "/home/admin" ]; then
    error "Цей скрипт призначений для запуску на сервері"
    exit 1
fi

cd /home/admin/upgrade-studio-bot

# 1. Оновлюємо код
step "Оновлення коду з репозиторію..."
if git pull; then
    success "Код оновлено"
else
    error "Помилка оновлення коду"
    exit 1
fi

# 2. Створюємо systemd unit files
step "Створення systemd unit files з обмеженнями..."
if ./setup_resource_limits.sh; then
    success "Конфігурацію створено"
else
    error "Помилка створення конфігурації"
fi

# 3. Копіюємо конфігурацію
step "Копіювання конфігурації..."
if sudo cp /tmp/upgrade-*.service /etc/systemd/system/; then
    success "Конфігурацію скопійовано"
else
    error "Помилка копіювання"
fi

# 4. Перезавантажуємо systemd
step "Перезавантаження systemd daemon..."
if sudo systemctl daemon-reload; then
    success "Daemon перезавантажено"
else
    error "Помилка перезавантаження daemon"
fi

# 5. Показуємо поточний стан
echo ""
step "Поточний стан сервісів:"
echo ""

for service in upgrade-bot upgrade-api upgrade-webhook; do
    if systemctl is-active --quiet $service; then
        echo "  $service: 🟢 активний"
    else
        echo "  $service: 🔴 неактивний"
    fi
done

echo ""
read -p "Перезапустити сервіси? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 6. Перезапускаємо сервіси
    step "Перезапуск сервісів..."
    
    for service in upgrade-bot upgrade-api upgrade-webhook; do
        echo "  Перезапуск $service..."
        if sudo systemctl restart $service; then
            success "$service перезапущено"
        else
            error "Помилка перезапуску $service"
        fi
        sleep 2
    done
    
    # 7. Перевіряємо статус
    echo ""
    step "Перевірка статусу після перезапуску:"
    echo ""
    
    for service in upgrade-bot upgrade-api upgrade-webhook; do
        if systemctl is-active --quiet $service; then
            echo "  $service: 🟢 працює"
        else
            echo "  $service: 🔴 не працює"
            error "Сервіс $service не запустився. Перевірте логи: journalctl -u $service -n 50"
        fi
    done
fi

# 8. Запускаємо очищення пам'яті
echo ""
read -p "Запустити очищення пам'яті? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    step "Очищення старих даних..."
    source venv/bin/activate
    python optimize_memory.py
    deactivate
fi

# 9. Показуємо статистику
echo ""
step "Статистика використання пам'яті:"
echo ""

for service in upgrade-bot upgrade-api upgrade-webhook; do
    echo "  $service:"
    systemctl show $service --property=MemoryCurrent,MemoryHigh,MemoryMax 2>/dev/null || echo "    Інформація недоступна"
    echo ""
done

echo ""
success "Оптимізацію завершено!"
echo ""
echo "📊 Для моніторингу використовуйте:"
echo "  - Логи: journalctl -u upgrade-bot -f"
echo "  - Пам'ять: systemctl show upgrade-bot | grep Memory"
echo "  - Процеси: ps aux | grep python"
echo ""
echo "📖 Детальна документація: RAM_OPTIMIZATION.md"
