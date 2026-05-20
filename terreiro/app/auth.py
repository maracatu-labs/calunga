"""JWT authentication dependency for FastAPI."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request

from app.config import settings

def criar_jwt(user_id: uuid.UUID, email: str) -> str:
    """Cria um JWT assinado com HS256, válido por 7 dias."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def decodificar_jwt(token: str) -> dict:
    """Decodifica e valida um JWT. Levanta exceção se inválido."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

async def get_current_user(request: Request) -> dict:
    """FastAPI dependency — extrai user do JWT. Retorna 401 se ausente/inválido."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")

    token = auth[7:]
    try:
        payload = decodificar_jwt(token)
        return {"id": payload["sub"], "email": payload["email"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
