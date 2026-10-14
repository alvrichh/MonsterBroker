from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.deps import AuthDep, CurrentUser, DbSession, EmailDep, SettingsDep
from app.api.schemas.auth import EmailIn, LoginIn, MessageOut, RegisterIn, ResetIn, TokenIn, TokenOut
from app.config import Settings
from app.services.auth import PURPOSE_RESET, PURPOSE_VERIFY, AuthError, AuthService, UserOut
from app.services.email import EmailError, EmailService
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter()

GENERIC_SENT = "Si la cuenta existe, te hemos enviado un correo. Revisa también la carpeta de spam."


def _http(error: AuthError) -> HTTPException:
    return HTTPException(error.status, {"code": error.code, "message": error.message})


def _link(settings: Settings, path: str, token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/{path}?token={token}"


async def _safe_send(email: EmailService, to: str, subject: str, html: str, text: str) -> None:
    try:
        await email.send(to, subject, html, text)
    except EmailError as error:  # a failed email must not fail the request that queued it
        log.error("email to %s failed: %s", to, error)


def _queue_verification(user, auth: AuthService, email: EmailService, settings: Settings,
                        background: BackgroundTasks) -> str:
    url = _link(settings, "verify", auth.verification_token(user))
    subject, html, text = email.verification_email(user.name, url)
    background.add_task(_safe_send, email, user.email, subject, html, text)
    return url


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, session: DbSession, auth: AuthDep, email: EmailDep, settings: SettingsDep,
                   background: BackgroundTasks):
    try:
        user = await auth.register(session, body.email, body.password, body.name)
    except AuthError as error:
        raise _http(error) from error
    if not settings.require_email_verification:
        await auth.mark_verified(session, user)
        return TokenOut(access_token=auth.access_token(user), user=UserOut.from_user(user))
    url = _queue_verification(user, auth, email, settings, background)
    dev_link = url if settings.email_backend == "console" and settings.debug else None
    return TokenOut(user=UserOut.from_user(user), verification_required=True, verify_url=dev_link)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, session: DbSession, auth: AuthDep, settings: SettingsDep):
    try:
        user = await auth.authenticate(session, body.email, body.password)
    except AuthError as error:
        raise _http(error) from error
    if settings.require_email_verification and not user.is_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            {"code": "unverified", "message": "Confirma tu correo antes de entrar."})
    return TokenOut(access_token=auth.access_token(user), user=UserOut.from_user(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return UserOut.from_user(user)


@router.post("/verify", response_model=TokenOut)
async def verify(body: TokenIn, session: DbSession, auth: AuthDep):
    user = await auth.user_from_token(session, body.token, PURPOSE_VERIFY)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            {"code": "bad_token", "message": "El enlace no es válido o ha caducado."})
    await auth.mark_verified(session, user)
    return TokenOut(access_token=auth.access_token(user), user=UserOut.from_user(user))


@router.post("/resend-verification", response_model=MessageOut)
async def resend_verification(body: EmailIn, session: DbSession, auth: AuthDep, email: EmailDep,
                              settings: SettingsDep, background: BackgroundTasks):
    user = await auth.by_email(session, body.email)
    if user and user.is_active and not user.is_verified and settings.require_email_verification:
        _queue_verification(user, auth, email, settings, background)
    return MessageOut(message=GENERIC_SENT)


@router.post("/forgot-password", response_model=MessageOut)
async def forgot_password(body: EmailIn, session: DbSession, auth: AuthDep, email: EmailDep, settings: SettingsDep,
                          background: BackgroundTasks):
    user = await auth.by_email(session, body.email)
    if user and user.is_active:
        url = _link(settings, "reset", auth.reset_token(user))
        subject, html, text = email.reset_email(user.name, url)
        background.add_task(_safe_send, email, user.email, subject, html, text)
    return MessageOut(message=GENERIC_SENT)


@router.post("/reset-password", response_model=TokenOut)
async def reset_password(body: ResetIn, session: DbSession, auth: AuthDep):
    user = await auth.user_from_token(session, body.token, PURPOSE_RESET)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            {"code": "bad_token", "message": "El enlace no es válido o ha caducado."})
    try:
        await auth.set_password(session, user, body.password)
    except AuthError as error:
        raise _http(error) from error
    await auth.mark_verified(session, user)  # reaching the inbox proves the address too
    return TokenOut(access_token=auth.access_token(user), user=UserOut.from_user(user))
