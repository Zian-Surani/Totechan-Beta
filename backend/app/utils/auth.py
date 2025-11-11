from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.settings import settings
from app.config.database import get_db
from app.models.user import User
from app.models.user_schemas import TokenData
from app.utils.exceptions import AuthenticationError, AuthorizationError

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")

        if user_id is None:
            raise AuthenticationError("Invalid token: missing user ID")

        return TokenData(
            user_id=user_id,
            email=email,
            role=role
        )

    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    credentials_exception = AuthenticationError("Could not validate credentials")

    try:
        token = credentials.credentials
        token_data = verify_token(token)
    except Exception:
        raise credentials_exception

    # Get user from database
    stmt = select(User).where(User.id == token_data.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise AuthenticationError("User account is inactive")
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current verified user"""
    if not current_user.is_verified:
        raise AuthenticationError("User account is not verified")
    return current_user


def require_role(allowed_roles: list[str]):
    """Decorator to require specific user roles"""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


# Common role dependencies
require_admin = require_role(["admin"])
require_user = require_role(["user", "admin", "viewer"])
require_viewer = require_role(["viewer", "admin"])


def create_user_token(user: User) -> Dict[str, Any]:
    """Create token for user"""
    access_token_expires = timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified
        }
    }


def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """Get user from token without FastAPI dependencies"""
    try:
        token_data = verify_token(token)
        stmt = select(User).where(User.id == token_data.user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    except Exception:
        return None