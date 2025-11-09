from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer
from typing import List, Dict, Any, Optional
import secrets
from datetime import datetime, timedelta
import bcrypt
import jwt
from jwt import InvalidTokenError
import sys
from pathlib import Path
from pydantic import BaseModel

# Додаємо шлях до проєкту
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.models import get_database
from database.encryption import settings_manager
from config import settings

# Pydantic моделі
class LoginRequest(BaseModel):
    username: str
    password: str

class AdminCreate(BaseModel):
    username: str
    email: str
    password: str
    first_name: str
    last_name: Optional[str] = None
    role: str = "admin"
    can_manage_users: bool = True
    can_manage_payments: bool = True
    can_manage_settings: bool = False
    can_manage_admins: bool = False

class AdminUpdate(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    can_manage_payments: Optional[bool] = None
    can_manage_settings: Optional[bool] = None
    can_manage_admins: Optional[bool] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class SettingUpdate(BaseModel):
    key: str
    value: str
    value_type: str = "string"
    category: str = "general"
    is_sensitive: bool = False
    description: Optional[str] = None


app = FastAPI(title="Upgrade Studio Bot API", version="1.0.0")

# CORS для Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://admin.upgrade21.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic Authentication
# JWT налаштування
JWT_SECRET = settings_manager.get("jwt_secret", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = timedelta(hours=24)

security = HTTPBasic(auto_error=False)
bearer_security = HTTPBearer(auto_error=False)

def create_access_token(data: dict) -> str:
    """Створити JWT токен"""
    to_encode = data.copy()
    expire = datetime.utcnow() + JWT_EXPIRATION
    to_encode.update({"exp": expire})
    # Переконуємось що sub є рядком
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Перевірити пароль"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def hash_password(password: str) -> str:
    """Захешувати пароль"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def get_admin_by_username(username: str) -> Optional[Dict]:
    """Отримати адміна за ім'ям користувача"""
    db = get_database()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM admins WHERE username = %s AND is_active = TRUE", (username,))
        admin = cursor.fetchone()
        return admin
    finally:
        cursor.close()
        db.close()

def get_admin_by_id(admin_id: int) -> Optional[Dict]:
    """Отримати адміна за ID"""
    db = get_database()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM admins WHERE id = %s AND is_active = TRUE", (admin_id,))
        admin = cursor.fetchone()
        return admin
    finally:
        cursor.close()
        db.close()

def get_current_admin_from_token(token: str = Depends(bearer_security)) -> Dict:
    """Отримати поточного адміна з JWT токена"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required",
        )
    
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        admin_id_str: str = payload.get("sub")
        if admin_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        admin_id = int(admin_id_str)  # Конвертуємо назад в int
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    admin = get_admin_by_id(admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
        )
    
    return admin

def get_current_admin(credentials: Optional[HTTPBasicCredentials] = Depends(security)):
    """Перевірка базової авторизації адміна (для зворотної сумісності)"""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Basic Auth credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Спочатку перевіряємо в базі даних
    admin = get_admin_by_username(credentials.username)
    if admin and verify_password(credentials.password, admin["password_hash"]):
        return admin
    
    # Якщо не знайдено в БД, перевіряємо старі дефолтні креди
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "Qwerty21")
    
    if correct_username and correct_password:
        return {"username": "admin", "id": 0, "is_superadmin": True, "can_manage_users": True, "can_manage_payments": True, "can_manage_settings": True, "can_manage_admins": True}
    
    raise HTTPException(
        status_code=401,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )

def get_current_admin_flexible(
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
    token: Optional[HTTPBearer] = Depends(bearer_security)
) -> Dict:
    """Гнучка авторизація - підтримує як Basic Auth так і JWT"""
    # Спочатку пробуємо JWT токен
    if token and hasattr(token, 'credentials') and token.credentials:
        try:
            payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            admin_id_str: str = payload.get("sub")
            if admin_id_str:
                admin_id = int(admin_id_str)  # Конвертуємо назад в int
                admin = get_admin_by_id(admin_id)
                if admin:
                    return admin
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
            pass
    
    # Якщо JWT не працює, пробуємо Basic Auth
    if credentials:
        try:
            return get_current_admin(credentials)
        except HTTPException:
            pass
    
    raise HTTPException(
        status_code=401,
        detail="Not authenticated",
    )

def check_admin_permission(admin: Dict, permission: str) -> bool:
    """Перевірити дозвіл адміна"""
    if admin.get("is_superadmin"):
        return True
    
    return admin.get(f"can_{permission}", False)

@app.get("/api/dashboard")
async def get_dashboard(admin: Dict = Depends(get_current_admin_flexible)) -> Dict[str, Any]:
    """Отримати статистику для дашборду"""
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        # Total users
        cursor.execute("SELECT COUNT(*) as total FROM users")
        result = cursor.fetchone()
        total_users = result["total"] if result else 0
        
        # Active users (subscription_active = 1)
        cursor.execute("SELECT COUNT(*) as active FROM users WHERE subscription_active = 1")
        result = cursor.fetchone()
        active_users = result["active"] if result else 0
        
        # Inactive users (subscription_active = 0)
        cursor.execute("SELECT COUNT(*) as inactive FROM users WHERE subscription_active = 0")
        result = cursor.fetchone()
        inactive_users = result["inactive"] if result else 0
        
        # Total revenue from successful payments (в центах)
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE status = 'succeeded'")
        result = cursor.fetchone()
        if result and result["total"]:
            from decimal import Decimal
            total_amount = result["total"]
            if isinstance(total_amount, Decimal):
                total_revenue = int(total_amount)
            else:
                total_revenue = int(total_amount)
        else:
            total_revenue = 0
        
        # Today's payments count
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM payments 
            WHERE status = 'succeeded' 
            AND DATE(created_at) = CURDATE()
        """)
        result = cursor.fetchone()
        payments_today = result["count"] if result else 0
        
        cursor.close()
        db.close()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "total_revenue": total_revenue,
            "payments_today": payments_today
        }
    except Exception as e:
        if 'db' in locals():
            try:
                db.close()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/users")
async def get_users(
    page: int = 1, 
    limit: int = 50, 
    search: str = "", 
    admin: Dict = Depends(get_current_admin_flexible)
) -> Dict[str, Any]:
    """Отримати список користувачів"""
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        offset = (page - 1) * limit
        
        if search:
            search_query = f"%{search}%"
            count_sql = """
                SELECT COUNT(*) as total 
                FROM users 
                WHERE CAST(telegram_id AS CHAR) LIKE %s OR first_name LIKE %s OR last_name LIKE %s
            """
            cursor.execute(count_sql, (search_query, search_query, search_query))
            result = cursor.fetchone()
            total_users = result["total"] if result else 0
            
            users_sql = """
                SELECT * FROM users 
                WHERE CAST(telegram_id AS CHAR) LIKE %s OR first_name LIKE %s OR last_name LIKE %s
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            cursor.execute(users_sql, (search_query, search_query, search_query, limit, offset))
        else:
            cursor.execute("SELECT COUNT(*) as total FROM users")
            result = cursor.fetchone()
            total_users = result["total"] if result else 0
            
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s", (limit, offset))
        
        users = cursor.fetchall() or []
        
        # Convert datetime objects to ISO strings
        for user in users:
            if user.get('created_at'):
                user['created_at'] = user['created_at'].isoformat()
            if user.get('updated_at'):
                user['updated_at'] = user['updated_at'].isoformat()
            if user.get('subscription_end_date'):
                user['subscription_end_date'] = user['subscription_end_date'].isoformat()
            if user.get('next_billing_date'):
                user['next_billing_date'] = user['next_billing_date'].isoformat()
            if user.get('member_since'):
                user['member_since'] = user['member_since'].isoformat()
        
        total_pages = (total_users + limit - 1) // limit if total_users > 0 else 1
        
        cursor.close()
        db.close()
        
        return {
            "users": users,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_users": total_users,
                "per_page": limit
            }
        }
    except Exception as e:
        if 'db' in locals():
            try:
                db.close()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/payments")
async def get_payments(
    page: int = 1, 
    limit: int = 50, 
    admin: Dict = Depends(get_current_admin_flexible)
) -> Dict[str, Any]:
    """Отримати список платежів"""
    try:
        db = get_database()
        cursor = db.cursor(dictionary=True)
        
        offset = (page - 1) * limit
        
        # Count total payments
        cursor.execute("SELECT COUNT(*) as total FROM payments")
        result = cursor.fetchone()
        total_payments = result["total"] if result else 0
        
        # Get payments with user info
        cursor.execute("""
            SELECT p.*, u.telegram_id, u.first_name, u.last_name
            FROM payments p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        payments = cursor.fetchall() or []
        
        # Convert datetime objects to ISO strings
        for payment in payments:
            if payment.get('created_at'):
                payment['created_at'] = payment['created_at'].isoformat()
            if payment.get('updated_at'):
                payment['updated_at'] = payment['updated_at'].isoformat()
            if payment.get('paid_at'):
                payment['paid_at'] = payment['paid_at'].isoformat()
        
        total_pages = (total_payments + limit - 1) // limit if total_payments > 0 else 1
        
        cursor.close()
        db.close()
        
        return {
            "payments": payments,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_payments": total_payments,
                "per_page": limit
            }
        }
    except Exception as e:
        if 'db' in locals():
            try:
                db.close()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/users/{user_id}/subscription")
async def update_user_subscription(
    user_id: int,
    action: str,
    admin: Dict = Depends(get_current_admin_flexible)
):
    """Оновити статус підписки користувача"""
    try:
        if action not in ["activate", "deactivate", "extend"]:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        db = get_database()
        cursor = db.cursor()
        
        if action == "activate":
            cursor.execute("""
                UPDATE users 
                SET subscription_status = 'active',
                    subscription_active = true,
                    subscription_end_date = DATE_ADD(NOW(), INTERVAL 1 MONTH)
                WHERE id = %s
            """, (user_id,))
        elif action == "deactivate":
            cursor.execute("""
                UPDATE users 
                SET subscription_status = 'inactive',
                    subscription_active = false,
                    subscription_end_date = NOW()
                WHERE id = %s
            """, (user_id,))
        elif action == "extend":
            cursor.execute("""
                UPDATE users 
                SET subscription_end_date = DATE_ADD(COALESCE(subscription_end_date, NOW()), INTERVAL 1 MONTH)
                WHERE id = %s
            """, (user_id,))
        
        db.commit()
        cursor.close()
        db.close()
        
        return {"success": True, "message": f"Subscription {action} successful"}
    except Exception as e:
        if 'db' in locals():
            try:
                db.close()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: Dict = Depends(get_current_admin_flexible)
):
    """Видалити користувача та всі пов'язані дані"""
    try:
        db = get_database()
        cursor = db.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            cursor.close()
            db.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete related payments first
        cursor.execute("DELETE FROM payments WHERE user_id = %s", (user_id,))
        
        # Delete user reminders if they exist
        try:
            cursor.execute("DELETE FROM user_reminders WHERE user_id = %s", (user_id,))
        except:
            # Table might not exist
            pass
        
        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        db.commit()
        cursor.close()
        db.close()
        
        return {"success": True, "message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        if 'db' in locals():
            try:
                db.close()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    """Авторизація адміна"""
    admin = get_admin_by_username(login_data.username)
    
    if not admin or not verify_password(login_data.password, admin["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Оновлюємо час останнього входу
    db = get_database()
    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE admins SET last_login_at = NOW() WHERE id = %s",
            (admin["id"],)
        )
        db.commit()
    finally:
        cursor.close()
        db.close()
    
    # Створюємо JWT токен
    access_token = create_access_token(data={"sub": admin["id"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "admin": {
            "id": admin["id"],
            "username": admin["username"],
            "email": admin["email"],
            "first_name": admin["first_name"],
            "last_name": admin["last_name"],
            "role": admin["role"],
            "is_superadmin": admin["is_superadmin"],
            "permissions": {
                "manage_users": admin["can_manage_users"],
                "manage_payments": admin["can_manage_payments"],
                "manage_settings": admin["can_manage_settings"],
                "manage_admins": admin["can_manage_admins"],
            }
        }
    }

@app.get("/api/auth/me")
async def get_current_user(admin: Dict = Depends(get_current_admin_from_token)):
    """Отримати інформацію про поточного адміна"""
    return {
        "id": admin["id"],
        "username": admin["username"],
        "email": admin["email"],
        "first_name": admin["first_name"],
        "last_name": admin["last_name"],
        "role": admin["role"],
        "is_superadmin": admin["is_superadmin"],
        "permissions": {
            "manage_users": admin["can_manage_users"],
            "manage_payments": admin["can_manage_payments"],
            "manage_settings": admin["can_manage_settings"],
            "manage_admins": admin["can_manage_admins"],
        },
        "last_login_at": admin["last_login_at"]
    }

@app.get("/api/admins")
async def get_admins(admin: Dict = Depends(get_current_admin_from_token)):
    """Отримати список адмінів"""
    if not check_admin_permission(admin, "manage_admins"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db = get_database()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT id, username, email, first_name, last_name, role, 
                   is_active, is_superadmin, can_manage_users, can_manage_payments,
                   can_manage_settings, can_manage_admins, created_at, last_login_at
            FROM admins 
            ORDER BY created_at DESC
        """)
        
        admins = cursor.fetchall() or []
        
        # Форматуємо дати
        for admin_item in admins:
            if admin_item.get('created_at'):
                admin_item['created_at'] = admin_item['created_at'].isoformat()
            if admin_item.get('last_login_at'):
                admin_item['last_login_at'] = admin_item['last_login_at'].isoformat()
        
        return {"admins": admins}
        
    finally:
        cursor.close()
        db.close()

@app.post("/api/admins")
async def create_admin(admin_data: AdminCreate, admin: Dict = Depends(get_current_admin_from_token)):
    """Створити нового адміна"""
    if not check_admin_permission(admin, "manage_admins"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db = get_database()
    cursor = db.cursor()
    
    try:
        # Перевіряємо чи не існує вже адмін з таким username або email
        cursor.execute(
            "SELECT id FROM admins WHERE username = %s OR email = %s",
            (admin_data.username, admin_data.email)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already exists")
        
        # Хешуємо пароль
        password_hash = hash_password(admin_data.password)
        
        # Створюємо адміна
        cursor.execute("""
            INSERT INTO admins (
                username, email, password_hash, first_name, last_name, role,
                can_manage_users, can_manage_payments, can_manage_settings, can_manage_admins
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            admin_data.username,
            admin_data.email,
            password_hash,
            admin_data.first_name,
            admin_data.last_name,
            admin_data.role,
            admin_data.can_manage_users,
            admin_data.can_manage_payments,
            admin_data.can_manage_settings,
            admin_data.can_manage_admins
        ))
        
        db.commit()
        admin_id = cursor.lastrowid
        
        return {"success": True, "message": "Admin created successfully", "id": admin_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating admin: {str(e)}")
    finally:
        cursor.close()
        db.close()

@app.put("/api/admins/{admin_id}")
async def update_admin(admin_id: int, admin_data: AdminUpdate, admin: Dict = Depends(get_current_admin_from_token)):
    """Оновити адміна"""
    if not check_admin_permission(admin, "manage_admins"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db = get_database()
    cursor = db.cursor()
    
    try:
        # Перевіряємо чи існує адмін
        cursor.execute("SELECT id FROM admins WHERE id = %s", (admin_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Admin not found")
        
        # Формуємо запит на оновлення
        update_fields = []
        update_values = []
        
        for field, value in admin_data.dict(exclude_none=True).items():
            update_fields.append(f"{field} = %s")
            update_values.append(value)
        
        if update_fields:
            update_values.append(admin_id)
            cursor.execute(
                f"UPDATE admins SET {', '.join(update_fields)}, updated_at = NOW() WHERE id = %s",
                update_values
            )
            db.commit()
        
        return {"success": True, "message": "Admin updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating admin: {str(e)}")
    finally:
        cursor.close()
        db.close()

@app.delete("/api/admins/{admin_id}")
async def delete_admin(admin_id: int, admin: Dict = Depends(get_current_admin_from_token)):
    """Видалити адміна"""
    if not check_admin_permission(admin, "manage_admins"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Не можна видалити самого себе
    if admin["id"] == admin_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db = get_database()
    cursor = db.cursor()
    
    try:
        cursor.execute("DELETE FROM admins WHERE id = %s", (admin_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Admin not found")
        
        db.commit()
        return {"success": True, "message": "Admin deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting admin: {str(e)}")
    finally:
        cursor.close()
        db.close()

@app.post("/api/admins/{admin_id}/change-password")
async def change_admin_password(admin_id: int, password_data: PasswordChange, admin: Dict = Depends(get_current_admin_from_token)):
    """Змінити пароль адміна"""
    # Можна змінити свій пароль або якщо є права manage_admins
    if admin["id"] != admin_id and not check_admin_permission(admin, "manage_admins"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db = get_database()
    cursor = db.cursor(dictionary=True)
    
    try:
        # Отримуємо поточний пароль
        cursor.execute("SELECT password_hash FROM admins WHERE id = %s", (admin_id,))
        admin_data = cursor.fetchone()
        
        if not admin_data:
            raise HTTPException(status_code=404, detail="Admin not found")
        
        # Перевіряємо поточний пароль (тільки якщо змінюємо свій)
        if admin["id"] == admin_id:
            if not verify_password(password_data.current_password, admin_data["password_hash"]):
                raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Хешуємо новий пароль
        new_password_hash = hash_password(password_data.new_password)
        
        # Оновлюємо пароль
        cursor.execute(
            "UPDATE admins SET password_hash = %s, updated_at = NOW() WHERE id = %s",
            (new_password_hash, admin_id)
        )
        
        db.commit()
        return {"success": True, "message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error changing password: {str(e)}")
    finally:
        cursor.close()
        db.close()

@app.get("/api/settings")
async def get_settings(admin: Dict = Depends(get_current_admin_flexible)):
    """Отримати налаштування системи"""
    # Для адмін панелі повертаємо всі налаштування, включаючи sensitive
    all_settings = settings_manager.get_all_settings(include_sensitive=True)
    
    return {
        "bot_token": all_settings.get("bot_token", ""),
        "webhook_url": all_settings.get("webhook_url", ""),
        "stripe_publishable_key": all_settings.get("stripe_publishable_key", ""),
        "stripe_secret_key": all_settings.get("stripe_secret_key", ""),
        "stripe_webhook_secret": all_settings.get("stripe_webhook_secret", ""),
        "subscription_price": all_settings.get("subscription_price", 15.0),
        "subscription_currency": all_settings.get("subscription_currency", "eur"),
        "database_status": "Connected",
        "bot_status": "Running",
        "webhook_status": "Active",
        "app_name": all_settings.get("app_name", "Upgrade Studio Bot"),
        "support_email": all_settings.get("support_email", "support@upgradestudio.com"),
        "maintenance_mode": all_settings.get("maintenance_mode", False)
    }

@app.get("/api/settings/all")
async def get_all_settings(admin: Dict = Depends(get_current_admin_from_token)):
    """Отримати всі налаштування для редагування"""
    if not check_admin_permission(admin, "manage_settings"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db = get_database()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT s.*, a.username as updated_by_username
            FROM system_settings s
            LEFT JOIN admins a ON s.updated_by = a.id
            ORDER BY s.category, s.key
        """)
        
        settings_list = cursor.fetchall() or []
        
        # Дешифруємо значення і форматуємо дати
        from database.encryption import decrypt_setting
        
        for setting in settings_list:
            if not setting["is_sensitive"]:
                setting["decrypted_value"] = decrypt_setting(setting["encrypted_value"], setting["value_type"])
            else:
                setting["decrypted_value"] = "***HIDDEN***"
            
            if setting.get('created_at'):
                setting['created_at'] = setting['created_at'].isoformat()
            if setting.get('updated_at'):
                setting['updated_at'] = setting['updated_at'].isoformat()
        
        return {"settings": settings_list}
        
    finally:
        cursor.close()
        db.close()

@app.put("/api/settings/{setting_key}")
async def update_setting(setting_key: str, setting_data: SettingUpdate, admin: Dict = Depends(get_current_admin_flexible)):
    """Оновити налаштування"""
    if not check_admin_permission(admin, "manage_settings"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    try:
        success = settings_manager.set(
            key=setting_key,
            value=setting_data.value,
            value_type=setting_data.value_type,
            category=setting_data.category,
            is_sensitive=setting_data.is_sensitive,
            description=setting_data.description,
            updated_by=admin["id"]
        )
        
        if success:
            # Очищаємо кеш налаштувань для динамічного оновлення
            settings.invalidate_cache()
            return {"success": True, "message": "Setting updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update setting")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating setting: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)