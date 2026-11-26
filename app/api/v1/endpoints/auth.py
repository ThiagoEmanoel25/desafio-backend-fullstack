"""Authentication endpoints: register, login (form data) and current user."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories import user_repository
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse

router = APIRouter()

# Verified when the e-mail is unknown so both login failures cost one bcrypt check.
_DUMMY_HASH = hash_password("timing-equalizer")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> User:
    """Create a user with a hashed password; 409 if the e-mail is taken."""
    conflict = HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
    )
    if await user_repository.get_by_email(db, payload.email):
        raise conflict
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    try:
        await user_repository.create(db, user)
        await db.commit()
    except IntegrityError:  # unique index backstop for a concurrent register
        await db.rollback()
        raise conflict from None
    return user


@router.post("/login", response_model=TokenResponse, summary="Log in and get a token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange credentials for a JWT.

    Expects `application/x-www-form-urlencoded` with the e-mail in the
    `username` field and the `password` field (not JSON). Unknown e-mail,
    wrong password and inactive user all return the same 401.
    """
    user = await user_repository.get_by_email(db, form_data.username)
    password_ok = verify_password(
        form_data.password, user.hashed_password if user else _DUMMY_HASH
    )
    if user is None or not password_ok or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserResponse, summary="Get the current user")
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the user identified by the bearer token."""
    return current_user
