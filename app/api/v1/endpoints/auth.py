import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.token import RevokedToken
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserInToken,
    RefreshRequest,
    AccessTokenResponse,
    LogoutRequest,
)

router = APIRouter()
security = HTTPBearer()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    jti_access = str(uuid.uuid4())
    jti_refresh = str(uuid.uuid4())

    access_token = create_access_token({"sub": user.id, "jti": jti_access})
    refresh_token = create_refresh_token({"sub": user.id, "jti": jti_refresh})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserInToken(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            store_id=user.store_id,
        ),
    )


@router.post("/logout")
async def logout(request: LogoutRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(request.refresh_token)
        jti = payload.get("jti", str(uuid.uuid4()))
        exp = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else (
            datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    revoked = RevokedToken(id=str(uuid.uuid4()), jti=jti, expires_at=expires_at)
    db.add(revoked)
    await db.commit()
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )
    try:
        payload = decode_token(request.refresh_token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        jti: str = payload.get("jti", "")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Check revoked
    result = await db.execute(select(RevokedToken).where(RevokedToken.jti == jti))
    if result.scalar_one_or_none():
        raise credentials_exception

    jti_new = str(uuid.uuid4())
    access_token = create_access_token({"sub": user_id, "jti": jti_new})
    return AccessTokenResponse(access_token=access_token)
