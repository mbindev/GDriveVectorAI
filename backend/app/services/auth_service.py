from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.main import get_db_connection
import psycopg2.extras
import secrets
import os

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: int, ip_address: Optional[str] = None,
                        user_agent: Optional[str] = None) -> str:
    """Create a refresh token and store it in database."""
    refresh_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_sessions (user_id, refresh_token, expires_at, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, refresh_token, expires_at, ip_address, user_agent))
            conn.commit()

    return refresh_token

def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate a user with username and password."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, username, email, password_hash, full_name, is_active, is_admin
                FROM users
                WHERE username = %s OR email = %s
            """, (username, username))
            user = cursor.fetchone()

            if not user:
                return None

            if not verify_password(password, user['password_hash']):
                return None

            if not user['is_active']:
                return None

            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = NOW() WHERE id = %s
            """, (user['id'],))
            conn.commit()

            return dict(user)

def verify_refresh_token(refresh_token: str) -> Optional[int]:
    """Verify refresh token and return user_id."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT user_id FROM user_sessions
                WHERE refresh_token = %s AND expires_at > NOW()
            """, (refresh_token,))
            result = cursor.fetchone()
            return result[0] if result else None

def revoke_refresh_token(refresh_token: str):
    """Revoke a refresh token."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM user_sessions WHERE refresh_token = %s
            """, (refresh_token,))
            conn.commit()

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, username, email, full_name, is_active, is_admin, api_key,
                       created_at, last_login
                FROM users
                WHERE id = %s
            """, (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None

def get_user_by_api_key(api_key: str) -> Optional[Dict]:
    """Get user by API key."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, username, email, full_name, is_active, is_admin
                FROM users
                WHERE api_key = %s AND is_active = true
            """, (api_key,))
            user = cursor.fetchone()
            return dict(user) if user else None

def create_user(username: str, email: str, password: str, full_name: Optional[str] = None,
                is_admin: bool = False) -> Dict:
    """Create a new user."""
    password_hash = get_password_hash(password)

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, is_admin)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, username, email, full_name, is_active, is_admin, created_at
            """, (username, email, password_hash, full_name, is_admin))
            user = cursor.fetchone()
            conn.commit()
            return dict(user)

def generate_api_key(user_id: int) -> str:
    """Generate a new API key for a user."""
    api_key = f"dvai_{secrets.token_urlsafe(32)}"

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET api_key = %s WHERE id = %s
            """, (api_key, user_id))
            conn.commit()

    return api_key

def revoke_api_key(user_id: int):
    """Revoke a user's API key."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET api_key = NULL WHERE id = %s
            """, (user_id,))
            conn.commit()
