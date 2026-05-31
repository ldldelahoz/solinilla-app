#!/usr/bin/env python3
"""
Módulo de autenticación y seguridad para Solinilla API.
Manejo de contraseñas con pbkdf2_sha256 y tokens JWT.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

# === CONFIGURACIÓN DE SEGURIDAD ===
# Clave secreta para firmar tokens JWT (en producción, usar variable de entorno)
SECRET_KEY = "solinilla_secret_2026_cloud_compatible"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 horas

# === CONFIGURACIÓN DE HASHING DE CONTRASEÑAS ===
# Usamos pbkdf2_sha256 que es compatible con Python 3.12+ y Render
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash almacenado.
    
    Args:
        plain_password: Contraseña ingresada por el usuario.
        hashed_password: Hash almacenado en la base de datos.
    
    Returns:
        bool: True si coinciden, False en caso contrario.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Si el hash es de un algoritmo desconocido, retornar False
        # en lugar de lanzar excepción para evitar errores 500
        return False


def hash_password(password: str) -> str:
    """
    Genera un hash seguro para almacenar una contraseña.
    
    Args:
        password: Contraseña en texto plano.
    
    Returns:
        str: Hash de la contraseña listo para almacenar.
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT con los datos del usuario y fecha de expiración.
    
    Args:
        data: Diccionario con datos a incluir en el token (ej: {"sub": "admin", "rol": "admin"}).
        expires_delta: Tiempo de expiración opcional (por defecto: ACCESS_TOKEN_EXPIRE_MINUTES).
    
    Returns:
        str: Token JWT firmado y codificado.
    """
    to_encode = data.copy()
    
    # Calcular fecha de expiración
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Agregar claims estándar
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    # Firmar y retornar token
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodifica y verifica un token JWT.
    
    Args:
        token: Token JWT a decodificar.
    
    Returns:
        dict: Payload del token si es válido, None en caso contrario.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Token inválido, expirado o mal formado
        return None
    except Exception:
        # Cualquier otro error de decodificación
        return None


def get_password_hash(password: str) -> str:
    """Alias para hash_password (compatibilidad con código antiguo)."""
    return hash_password(password)