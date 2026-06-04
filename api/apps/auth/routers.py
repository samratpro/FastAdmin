from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from core.database import get_db
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from core.dependencies import get_current_user, require_auth
from core.config import settings
from apps.auth.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic Schemas
class UserRegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class UserMeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    userId: int = Field(validation_alias="id")
    username: str
    email: str
    isStaff: bool = Field(validation_alias="is_staff")
    isSuperuser: bool = Field(validation_alias="is_superuser")
    firstName: Optional[str] = Field(None, validation_alias="first_name")
    lastName: Optional[str] = Field(None, validation_alias="last_name")

@router.post("/register")
async def register(data: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    existing_user = await User.objects(db).filter(email=data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_username = await User.objects(db).filter(username=data.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = User(
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        is_active=False # Requires email verification
    )
    await new_user.save(db)

    return {"success": True, "message": "User registered successfully. Please verify your email."}

@router.post("/login")
async def login(data: UserLoginSchema, response: Response, db: AsyncSession = Depends(get_db)):
    user = await User.objects(db).filter(email=data.email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is not active. Please verify your email.")

    # Create tokens
    access_token = create_access_token({"userId": user.id, "email": user.email, "username": user.username, "isStaff": user.is_staff, "isSuperuser": user.is_superuser})
    refresh_token = create_refresh_token({"userId": user.id})

    # Set cookies
    response.set_cookie(
        key="accessToken",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=86400 # 1 day
    )
    response.set_cookie(
        key="refreshToken",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        path="/auth/refresh",
        max_age=604800 # 7 days
    )

    return {
        "success": True,
        "message": "Login successful",
        "user": UserMeSchema.model_validate(user)
    }

@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refreshToken")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    payload = decode_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = await User.objects(db).filter(id=payload.get("userId")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token({"userId": user.id, "email": user.email, "username": user.username, "isStaff": user.is_staff, "isSuperuser": user.is_superuser})

    response.set_cookie(
        key="accessToken",
        value=new_access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=86400
    )

    return {"success": True, "message": "Token refreshed", "user": UserMeSchema.model_validate(user)}

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "success": True,
        "user": UserMeSchema.model_validate(user)
    }

@router.post("/verify-email")
async def verify_email(payload: dict, db: AsyncSession = Depends(get_db)):
    token = payload.get("token", "")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    # Decode the token to get userId
    data = decode_token(token)
    if not data or "userId" not in data:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user = await User.objects(db).filter(id=data["userId"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await user.save(db)
    return {"success": True, "message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(payload: dict, db: AsyncSession = Depends(get_db)):
    email = payload.get("email", "")
    user = await User.objects(db).filter(email=email).first()
    # Always return success to avoid user enumeration
    if user:
        # In production, send email with reset token. For now, log it.
        reset_token = create_access_token({"userId": user.id, "purpose": "reset"})
        print(f"[DEV] Password reset token for {email}: {reset_token}")
    return {"success": True, "message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(payload: dict, db: AsyncSession = Depends(get_db)):
    token = payload.get("token", "")
    new_password = payload.get("newPassword", "")
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="token and newPassword are required")
    data = decode_token(token)
    if not data or data.get("purpose") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user = await User.objects(db).filter(id=data.get("userId")).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password = hash_password(new_password)
    user.is_active = True
    await user.save(db)
    return {"success": True, "message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(payload: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_password = payload.get("currentPassword", "")
    new_password = payload.get("newPassword", "")
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="currentPassword and newPassword are required")
    if not verify_password(current_password, user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password = hash_password(new_password)
    await user.save(db)
    return {"success": True, "message": "Password changed successfully"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("accessToken")
    response.delete_cookie("refreshToken")
    return {"success": True, "message": "Logged out successfully"}
