from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        # Add more password validation as needed
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(UserBase):
    id: uuid.UUID
    role: str
    is_active: bool
    is_verified: bool
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: Optional[uuid.UUID] = None
    email: Optional[str] = None
    role: Optional[str] = None


class UserProfile(UserResponse):
    """Extended user profile with additional information"""
    total_documents: Optional[int] = 0
    total_sessions: Optional[int] = 0
    total_tokens_used: Optional[int] = 0


class UserPreferences(BaseModel):
    """User preferences schema"""
    theme: str = "light"  # light, dark
    language: str = "en"
    notifications_enabled: bool = True
    auto_save_sessions: bool = True
    default_retrieval_k: int = 8
    rerank_enabled: bool = True
    max_file_upload_size: int = 50  # MB

    class Config:
        from_attributes = True