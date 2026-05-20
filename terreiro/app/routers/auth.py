import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import criar_jwt, get_current_user
from app.database import get_pool
from app.queries import auth as auth_q
from app.schemas.auth import (
    AuthResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    UserResponse,
    VerifyRequest,
)
from app.services.email import enviar_magic_link

router = APIRouter(prefix="/v1/auth", tags=["auth"])

@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(request: MagicLinkRequest):
    pool = get_pool()
    token_id = await auth_q.criar_magic_link(pool, request.email)
    await enviar_magic_link(request.email, str(token_id))
    return MagicLinkResponse(message="Link enviado para seu email")

@router.post("/verify", response_model=AuthResponse)
async def verify_magic_link(request: VerifyRequest):
    pool = get_pool()
    email = await auth_q.validar_magic_link(pool, request.token)

    if not email:
        raise HTTPException(status_code=400, detail="Link inválido ou expirado")

    await auth_q.marcar_magic_link_usado(pool, request.token)
    user = await auth_q.buscar_ou_criar_user(pool, email)
    jwt_token = criar_jwt(uuid.UUID(str(user["id"])), user["email"])

    return AuthResponse(
        token=jwt_token,
        user=UserResponse(id=user["id"], email=user["email"]),
    )

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}
