from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import structlog
from datetime import datetime

from app.config.database import get_db
from app.models.user import User
from app.models.user_schemas import (
    UserCreate, UserLogin, UserResponse, Token, UserProfile
)
from app.utils.auth import (
    get_password_hash, verify_password, create_user_token,
    get_current_active_user, require_admin
)
from app.utils.exceptions import (
    AuthenticationError, ValidationError, ConflictError
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    try:
        # Check if user already exists
        stmt = select(User).where(User.email == user_data.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise ConflictError("User with this email already exists")

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_active=True,
            is_verified=False  # Require email verification
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info("user_registered", user_id=str(user.id), email=user.email)

        return user

    except IntegrityError:
        await db.rollback()
        raise ConflictError("User with this email already exists")
    except Exception as e:
        await db.rollback()
        logger.error("registration_error", error=str(e))
        raise


@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return access token"""
    try:
        # Get user by email
        stmt = select(User).where(User.email == user_credentials.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not verify_password(user_credentials.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()

        # Create token
        token_data = create_user_token(user)

        logger.info("user_logged_in", user_id=str(user.id), email=user.email)

        return token_data

    except AuthenticationError:
        logger.warning(
            "login_failed",
            email=user_credentials.email,
            reason="invalid_credentials"
        )
        raise
    except Exception as e:
        logger.error("login_error", error=str(e))
        raise


@router.post("/token", response_model=Token)
async def login_with_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """OAuth2 compatible token endpoint"""
    user_credentials = UserLogin(
        email=form_data.username,
        password=form_data.password
    )
    return await login(user_credentials, db)


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile with statistics"""
    try:
        # Get user statistics
        from sqlalchemy import func, Count

        # Document count
        doc_stmt = select(func.count(User.id)).where(User.id == current_user.id)
        doc_result = await db.execute(
            select(func.count(User.id))
            .select_from(User)
            .join(User.documents)
            .where(User.id == current_user.id)
        )
        total_documents = doc_result.scalar() or 0

        # Session count
        session_result = await db.execute(
            select(func.count(User.id))
            .select_from(User)
            .join(User.chat_sessions)
            .where(User.id == current_user.id)
        )
        total_sessions = session_result.scalar() or 0

        # Token usage
        from app.models.chat import ChatSession, Message

        token_result = await db.execute(
            select(func.coalesce(func.sum(Message.token_count), 0))
            .select_from(User)
            .join(User.chat_sessions)
            .join(ChatSession.messages)
            .where(User.id == current_user.id)
        )
        total_tokens_used = token_result.scalar() or 0

        # Build profile response
        user_profile = UserProfile(
            **current_user.__dict__,
            total_documents=total_documents,
            total_sessions=total_sessions,
            total_tokens_used=total_tokens_used
        )

        return user_profile

    except Exception as e:
        logger.error("profile_error", user_id=str(current_user.id), error=str(e))
        # Return basic profile if stats fail
        return UserProfile(**current_user.__dict__)


@router.get("/verify", response_model=dict)
async def verify_token(
    current_user: User = Depends(get_current_active_user)
):
    """Verify if token is valid"""
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """Logout user (client-side token removal)"""
    logger.info("user_logged_out", user_id=str(current_user.id))
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
    """Refresh access token"""
    try:
        token_data = create_user_token(current_user)
        logger.info("token_refreshed", user_id=str(current_user.id))
        return token_data
    except Exception as e:
        logger.error("token_refresh_error", user_id=str(current_user.id), error=str(e))
        raise


# Admin-only endpoints
@router.get("/admin/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)"""
    try:
        stmt = select(User).offset(skip).limit(limit)
        result = await db.execute(stmt)
        users = result.scalars().all()
        return users
    except Exception as e:
        logger.error("admin_list_users_error", error=str(e))
        raise


@router.post("/admin/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Activate user account (admin only)"""
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.is_active = True
        user.is_verified = True
        await db.commit()

        logger.info(
            "user_activated",
            target_user_id=user_id,
            admin_id=str(current_user.id)
        )

        return {"message": "User activated successfully"}

    except Exception as e:
        await db.rollback()
        logger.error("admin_activate_user_error", error=str(e))
        raise