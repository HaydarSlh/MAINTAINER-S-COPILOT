"""Auth routes: registration + login (JWT).

POST /auth/register  — create account, return token
POST /auth/login     — verify credentials, return token
GET  /auth/me        — return current user (requires auth)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from app.api.deps import get_current_user
from app.domain.models import User

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest) -> TokenResponse:
    from app.services.auth_service import register as svc_register
    user, token = await svc_register(body.email, body.password)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    from app.services.auth_service import authenticate
    user, token = await authenticate(body.email, body.password)
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=User)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
