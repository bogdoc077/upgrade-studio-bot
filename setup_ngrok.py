#!/usr/bin/env python3
"""
Скрипт для налаштування ngrok auth token
"""
import subprocess
import sys

def setup_ngrok_auth():
    """Налаштувати ngrok auth token"""
    print(" Налаштування ngrok auth token")
    print("=" * 40)
    print()
    print("1. Відкрийте https://dashboard.ngrok.com/get-started/your-authtoken")
    print("2. Зареєструйтеся або увійдіть в акаунт")
    print("3. Скопіюйте ваш auth token")
    print()
    
    # Отримуємо токен від користувача
    while True:
        token = input("Вставте ваш ngrok auth token: ").strip()
        
        if not token:
            print(" Токен не може бути пустим")
            continue
            
        if len(token) < 20:
            print(" Токен занадто короткий")
            continue
            
        break
    
    # Налаштовуємо токен
    try:
        result = subprocess.run([
            "ngrok", "config", "add-authtoken", token
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(" Auth token налаштовано успішно!")
            print()
            print("Тепер можете запустити:")
            print("python start_webhook.py")
            return True
        else:
            print(f" Помилка налаштування токену: {result.stderr}")
            return False
            
    except Exception as e:
        print(f" Помилка: {e}")
        return False

if __name__ == "__main__":
    print("Upgrade Studio Bot - Налаштування ngrok")
    print("=" * 50)
    
    # Перевіряємо чи встановлений ngrok
    try:
        result = subprocess.run(["ngrok", "version"], capture_output=True)
        if result.returncode != 0:
            print(" ngrok не встановлений")
            print("Встановіть: brew install ngrok/ngrok/ngrok")
            sys.exit(1)
    except FileNotFoundError:
        print(" ngrok не знайдено")
        print("Встановіть: brew install ngrok/ngrok/ngrok") 
        sys.exit(1)
    
    success = setup_ngrok_auth()
    sys.exit(0 if success else 1)