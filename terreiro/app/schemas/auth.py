from uuid import UUID

from pydantic import BaseModel, EmailStr

class MagicLinkRequest(BaseModel):
    email: EmailStr

class MagicLinkResponse(BaseModel):
    message: str

class VerifyRequest(BaseModel):
    token: UUID

class UserResponse(BaseModel):
    id: UUID
    email: str

class AuthResponse(BaseModel):
    token: str
    user: UserResponse
