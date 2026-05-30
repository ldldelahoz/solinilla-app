#!/usr/bin/env python3
"""Módulo de autenticación y seguridad (JWT + Hashing)."""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# === CONFIGURACIÓN DE SEGURIDAD ===
# Clave secreta para firmar los tokens JWT
SECRET_KEY = "solinilla_secret_2026_cloud_compatible" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 horas

# === CONFIGURACIÓN DE HASHING ===
# IMPORTANTE: 'pbkdf2_sha256' es compatible con Python 3.12+ y Render.
# Evita el error 'passlib.exc.UnknownHashError'.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash guardado."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Si el hash es de un algoritmo desconocido (ej. bcrypt viejo), 
        # retornamos False para evitar Error 500 en el servidor.
        return False

def hash_password(password: str) -> str:
    """Genera un hash seguro para guardar en la base de datos."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT con fecha de expiración."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """Decodifica un token JWT y retorna los datos del usuario."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None