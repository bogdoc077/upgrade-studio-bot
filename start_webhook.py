#!/usr/bin/env python3
"""
Скрипт для запуску webhook сервера з автоматичним налаштуванням ngrok
"""
import asyncio
import subprocess
import time
import requests
import json
import os
import signal
import sys
from pathlib import Path

# Налаштування
WEBHOOK_PORT = 8000
WEBHOOK_HOST = "0.0.0.0"
NGROK_API_URL = "http://localhost:4040/api/tunnels"

def check_existing_ngrok():
    """Перевірити чи вже запущено ngrok"""
    try:
        response = requests.get(NGROK_API_URL, timeout=5)
        if response.status_code == 200:
            tunnels = response.json()["tunnels"]
            for tunnel in tunnels:
                if tunnel["config"]["addr"] == f"localhost:{WEBHOOK_PORT}":
                    public_url = tunnel["public_url"]
                    if public_url.startswith("https://"):
                        return public_url
        return None
    except:
        return None

def start_ngrok():
    """Запустити ngrok для webhook сервера (якщо ще не запущено)"""
    # Спочатку перевіряємо чи вже працює ngrok
    existing_url = check_existing_ngrok()
    if existing_url:
        print(f" ngrok вже запущено: {existing_url}")
        return None, existing_url  # Не повертаємо процес, оскільки він вже працює
    
    print(" Запуск нового ngrok...")
    
    # Перевіряємо чи налаштований auth token
    try:
        result = subprocess.run(["ngrok", "config", "check"], capture_output=True, text=True)
        if "valid" not in result.stdout.lower():
            print(" Auth token не налаштований")
            print("1. Зареєструйтеся на https://ngrok.com/")
            print("2. Отримайте auth token з https://dashboard.ngrok.com/get-started/your-authtoken")
            print("3. Запустіть: ngrok config add-authtoken YOUR_TOKEN")
            return None, None
    except:
        pass
    
    # Запускаємо ngrok
    ngrok_process = subprocess.Popen([
        "ngrok", "http", str(WEBHOOK_PORT),
        "--log=stdout"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Чекаємо декілька секунд на запуск
    print("⏳ Чекаємо запуск ngrok...")
    time.sleep(5)
    
    try:
        # Отримуємо URL ngrok
        response = requests.get(NGROK_API_URL, timeout=10)
        if response.status_code == 200:
            tunnels = response.json()["tunnels"]
            for tunnel in tunnels:
                if tunnel["config"]["addr"] == f"localhost:{WEBHOOK_PORT}":
                    public_url = tunnel["public_url"]
                    if public_url.startswith("https://"):
                        print(f" ngrok запущено: {public_url}")
                        return ngrok_process, public_url
        
        # Перевіряємо чи є помилки в процесі
        if ngrok_process.poll() is not None:
            stderr_output = ngrok_process.stderr.read()
            print(f" ngrok завершився з помилкою: {stderr_output}")
        else:
            print(" Не вдалося отримати URL ngrok")
        
        ngrok_process.terminate()
        return None, None
        
    except Exception as e:
        print(f" Помилка отримання URL ngrok: {e}")
        if ngrok_process:
            ngrok_process.terminate()
        return None, None

def update_stripe_webhook_endpoint(webhook_url):
    """Оновити endpoint webhook'а в Stripe (інструкції)"""
    print(f"\n ВАЖЛИВО! Налаштування Stripe webhook:")
    print("=" * 50)
    print(f"1. Відкрийте Stripe Dashboard: https://dashboard.stripe.com/webhooks")
    print(f"2. Натисніть 'Add endpoint' або оновіть існуючий")
    print(f"3. Вставте цей URL: {webhook_url}/webhook")
    print(f"4. Виберіть ці події для відстеження:")
    print(f"    checkout.session.completed")
    print(f"    customer.subscription.created")
    print(f"    customer.subscription.updated")
    print(f"    customer.subscription.deleted")
    print(f"    invoice.payment_failed")
    print(f"    invoice.payment_succeeded")
    print(f"5. Збережіть webhook")
    print(f"6. СКОПІЮЙТЕ 'Signing secret' (whsec_...)")
    print(f"7. Оновіть .env файл:")
    print(f"   STRIPE_WEBHOOK_SECRET=whsec_ваш_секрет")
    print(f"   WEBHOOK_URL={webhook_url}/webhook")
    print()
    print("  БЕЗ ПРАВИЛЬНОГО WEBHOOK SECRET ОПЛАТИ НЕ БУДУТЬ ОБРОБЛЯТИСЯ!")
    print("=" * 50)

def start_webhook_server():
    """Запустити webhook сервер"""
    print(" Запуск webhook сервера...")
    
    webhook_process = subprocess.Popen([
        "python", "webhook_server.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    return webhook_process

def check_dependencies():
    """Перевірити залежності"""
    print(" Перевірка залежностей...")
    
    # Перевіряємо ngrok
    try:
        result = subprocess.run(["ngrok", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            print(" ngrok не встановлено або не доступно")
            print("   Інсталяція: brew install ngrok/ngrok/ngrok")
            return False
        print(f" ngrok встановлено: {result.stdout.strip()}")
    except FileNotFoundError:
        print(" ngrok не знайдено")
        print("   Завантажте з: https://ngrok.com/download")
        print("   Або встановіть: brew install ngrok/ngrok/ngrok")
        return False
    
    # Перевіряємо .env файл
    if not Path(".env").exists():
        print(" Файл .env не знайдено")
        print("   Створіть .env файл з необхідними змінними")
        return False
    print(" Файл .env знайдено")
    
    # Перевіряємо основні налаштування
    try:
        from config import settings
        
        if not settings.stripe_secret_key or settings.stripe_secret_key == "your_stripe_secret_key":
            print(" STRIPE_SECRET_KEY не налаштований в .env")
            return False
        print(" STRIPE_SECRET_KEY налаштований")
        
        if not settings.telegram_bot_token or settings.telegram_bot_token == "your_telegram_bot_token":
            print(" TELEGRAM_BOT_TOKEN не налаштований в .env")
            return False
        print(" TELEGRAM_BOT_TOKEN налаштований")
        
        if settings.stripe_webhook_secret == "whsec_mock_secret_for_testing":
            print("  STRIPE_WEBHOOK_SECRET використовує тестове значення")
            print("   Оновіть його після налаштування ngrok webhook")
        else:
            print(" STRIPE_WEBHOOK_SECRET налаштований")
            
    except Exception as e:
        print(f" Помилка перевірки налаштувань: {e}")
        return False
    
    return True

def cleanup_processes(*processes):
    """Зупинити всі процеси"""
    print("\n Зупинка процесів...")
    for process in processes:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

def is_production_mode():
    """Перевірити чи це продакшен режим"""
    # Перевіряємо змінні оточення
    env_mode = os.getenv('ENVIRONMENT', '').lower()
    if env_mode in ['production', 'prod']:
        return True
    
    # Перевіряємо чи налаштований реальний WEBHOOK_URL
    try:
        from config import settings
        webhook_url = settings.webhook_url
        if webhook_url and not 'ngrok' in webhook_url.lower() and webhook_url != 'https://yourdomain.com/webhook':
            return True
    except:
        pass
    
    return False

def main():
    """Головна функція"""
    production_mode = is_production_mode()
    
    if production_mode:
        print("Upgrade Studio Bot - Webhook Server (Production)")
        print("=" * 50)
        print(" Режим продакшену - ngrok не використовується")
    else:
        print("Upgrade Studio Bot - Webhook Server з ngrok")
        print("=" * 50)
    
    # Перевіряємо залежності
    if not check_dependencies():
        return 1
    
    ngrok_process = None
    webhook_process = None
    
    def signal_handler(signum, frame):
        print(f"\n Отримано сигнал {signum}")
        cleanup_processes(ngrok_process, webhook_process)
        sys.exit(0)
    
    # Обробляємо сигнали
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if production_mode:
            # Продакшен режим - тільки webhook сервер
            print(" Запуск webhook сервера...")
            webhook_process = start_webhook_server()
            
            try:
                from config import settings
                webhook_url = settings.webhook_url
                print(" Webhook сервер запущено!")
                print(f" Local server: http://localhost:{WEBHOOK_PORT}")
                print(f" Configured webhook: {webhook_url}")
                print(f" Health check: http://localhost:{WEBHOOK_PORT}/health")
                print()
                print("Для зупинки натисніть Ctrl+C")
            except Exception as e:
                print(f" Не вдалося отримати налаштування: {e}")
            
            # Моніторимо тільки webhook процес
            while True:
                time.sleep(1)
                if webhook_process.poll() is not None:
                    print(" Webhook сервер зупинився")
                    break
        else:
            # Режим розробки з ngrok
            ngrok_process, public_url = start_ngrok()
            if not public_url:
                print(" Не вдалося запустити ngrok")
                return 1
            
            # Показуємо інструкції для Stripe тільки якщо це новий ngrok
            if ngrok_process:  # Новий процес ngrok
                update_stripe_webhook_endpoint(public_url)
            else:  # Використовуємо існуючий ngrok
                print(f" Використовуємо існуючий ngrok: {public_url}")
                print(f" Webhook endpoint: {public_url}/webhook")
            
            # Запускаємо webhook сервер
            webhook_process = start_webhook_server()
            
            print(" Все готово!")
            print(f" Webhook server: http://localhost:{WEBHOOK_PORT}")
            print(f" Public URL: {public_url}")
            print(f" Webhook endpoint: {public_url}/webhook")
            print(f" Health check: {public_url}/health")
            print()
            print("Для зупинки натисніть Ctrl+C")
            print()
            
            # Моніторимо процеси
            while True:
                time.sleep(1)
                
                # Перевіряємо чи працюють процеси
                if ngrok_process and ngrok_process.poll() is not None:
                    print(" ngrok зупинився")
                    break
                    
                if webhook_process.poll() is not None:
                    print(" Webhook сервер зупинився")
                    break
    
    except KeyboardInterrupt:
        print("\n Зупинка за запитом користувача")
    except Exception as e:
        print(f" Помилка: {e}")
    finally:
        cleanup_processes(ngrok_process, webhook_process)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())