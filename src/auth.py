from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Header, HTTPException, status

# 🔐 Configuración JWT
SECRET_KEY = "solinilla_secret_key_2026_change_this_in_production"  # ← Cambia esto
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 horas

# 🔐 Configuración de hashing (PBKDF2 - compatible con Python 3.13)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verifica si una contraseña coincide con su hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def hash_password(password):
    """Genera un hash seguro para una contraseña."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    """Decodifica un token JWT."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None



def get_current_user(authorization: str = Header(None)):
    """Extrae y valida el usuario desde el header Authorization."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extraer el token (quitar "Bearer ")
    token = authorization.replace("Bearer ", "").strip()
    
    # Decodificar el token
    payload = decode_token(token)  # ← Tu función que usa jwt.decode
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload
def require_admin(user: dict):
    """Verifica que el usuario sea admin."""
    if not user or user.get("rol") != "admin":
        raise Exception("No autorizado")
    return user