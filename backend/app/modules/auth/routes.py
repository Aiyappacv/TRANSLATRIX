"""
Auth API Routes
Authentication and registration endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.auth.schemas import (
    CompanyRegistrationRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse
)
from app.modules.auth.service import AuthService
from app.core.response import success_response, error_response
from app.exceptions import TranslatrixException

router = APIRouter()


@router.post("/register-company", status_code=status.HTTP_201_CREATED)
async def register_company(
    request: CompanyRegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new company
    Creates tenant, company, admin user, and onboarding record
    """
    try:
        service = AuthService(db)
        result = service.register_company(request)
        return success_response(
            data=result,
            message="Company registered successfully"
        )
    except TranslatrixException as e:
        return error_response(message=e.message, errors=[e.details])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    User login
    Returns access and refresh tokens
    """
    try:
        service = AuthService(db)
        result = service.login(request)
        return result
    except TranslatrixException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)


@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        service = AuthService(db)
        result = service.refresh_access_token(request.refresh_token)
        return success_response(data=result)
    except TranslatrixException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information
    """
    try:
        service = AuthService(db)
        result = service.get_current_user_info(str(current_user.id))
        return result
    except TranslatrixException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
