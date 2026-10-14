from fastapi import APIRouter, HTTPException, status

from app.api.deps import AuthDep, CurrentUser
from app.api.schemas.auth import LoginIn, RegisterIn, TokenOut
from app.services.auth import AuthError, User

router = APIRouter()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, auth: AuthDep):
    try:
        user = auth.register(body.email, body.password, body.name)
    except AuthError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    return TokenOut(access_token=auth.create_token(user), user=user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, auth: AuthDep):
    user = auth.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos.")
    return TokenOut(access_token=auth.create_token(user), user=user)


@router.get("/me", response_model=User)
def me(user: CurrentUser):
    return user
