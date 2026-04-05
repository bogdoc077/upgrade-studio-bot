#!/bin/bash
# Скрипт для перегляду логів бота на сервері

echo "Переглядаємо логи upgrade-webhook на сервері..."
ssh root@173.242.49.209 "journalctl -u upgrade-webhook -f"
