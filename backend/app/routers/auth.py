from fastapi import APIRouter, HTTPException, Depends, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.services import auth_service
from datetime import timedelta

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_admin: bool
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency to get current authenticated user."""
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = auth_service.get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """Dependency to get current active user."""
    if not current_user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: dict = Depends(get_current_active_user)):
    """Dependency to check if user is admin."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return current_user

async def get_api_key_user(x_api_key: Optional[str] = Header(None)):
    """Dependency to authenticate via API key."""
    if not x_api_key:
        return None

    user = auth_service.get_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user."""
    try:
        user = auth_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        return user
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token."""
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token = auth_service.create_access_token(
        data={"sub": str(user['id']), "username": user['username']}
    )
    refresh_token = auth_service.create_refresh_token(user['id'])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    user_id = auth_service.verify_refresh_token(request.refresh_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Create new tokens
    access_token = auth_service.create_access_token(
        data={"sub": str(user['id']), "username": user['username']}
    )
    # Optionally rotate refresh token
    new_refresh_token = auth_service.create_refresh_token(user_id)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(
    request: RefreshTokenRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Logout and revoke refresh token."""
    auth_service.revoke_refresh_token(request.refresh_token)
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user

@router.post("/api-key/generate")
async def generate_api_key(current_user: dict = Depends(get_current_active_user)):
    """Generate a new API key for the current user."""
    api_key = auth_service.generate_api_key(current_user['id'])
    return {"api_key": api_key, "message": "API key generated. Store it securely."}

@router.delete("/api-key/revoke")
async def revoke_api_key(current_user: dict = Depends(get_current_active_user)):
    """Revoke the current user's API key."""
    auth_service.revoke_api_key(current_user['id'])
    return {"message": "API key revoked"}
