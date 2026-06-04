from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import decode_token
from apps.auth.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    Checks for token in Authorization header or cookies.
    """
    token = None

    # 1. Check Authorization Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    # 2. Check Cookies
    if not token:
        token = request.cookies.get("accessToken")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("userId")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Fetch user from DB
    from common.orm import Model # Avoid circular import
    user = await User.objects(db).filter(id=user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user

async def require_auth(user: User = Depends(get_current_user)):
    """Ensures the user is authenticated."""
    return user

async def require_staff(user: User = Depends(get_current_user)):
    """Ensures the user is staff or superuser."""
    if not (user.is_staff or user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return user

async def require_superuser(user: User = Depends(get_current_user)):
    """Ensures the user is a superuser."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return user

def require_permission(codename: str):
    """
    Higher-order dependency to check for a specific permission.
    """
    async def permission_checker(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        if user.is_superuser:
            return user

        # Check direct permissions
        for perm in user.permissions:
            if perm.codename == codename:
                return user

        # Check group permissions
        for group in user.groups:
            for perm in group.permissions:
                if perm.codename == codename:
                    return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{codename}' required"
        )

    return permission_checker
