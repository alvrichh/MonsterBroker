"""One-click sign-in: OAuth providers (Google, GitHub, Microsoft) and
Sign-In with Ethereum. Both end in the same JWT the password flow issues."""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.api.deps import AuthDep, CurrentUser, DbSession, OAuthDep, SettingsDep, SiweDep
from app.api.schemas.auth import TokenOut
from app.services.auth import AuthError, UserOut
from app.services.oauth import LABELS, fetch_profile
from app.services.siwe import SiweError
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter()


class ProviderOut(BaseModel):
    id: str
    label: str
    start_url: str


class ProvidersOut(BaseModel):
    providers: list[ProviderOut]
    wallet: bool = True
    chain_id: int


class NonceIn(BaseModel):
    address: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")


class NonceOut(BaseModel):
    message: str


class VerifyIn(BaseModel):
    message: str = Field(min_length=40, max_length=2000)
    signature: str = Field(pattern=r"^0x[0-9a-fA-F]{130}$")


def _http(error: AuthError) -> HTTPException:
    return HTTPException(error.status, {"code": error.code, "message": error.message})


# ------------------------------------------------------------------ OAuth


@router.get("/oauth/providers", response_model=ProvidersOut)
def providers(oauth: OAuthDep, settings: SettingsDep):
    _, configured = oauth
    base = settings.public_api_url.rstrip("/")
    listed = [ProviderOut(id=p, label=LABELS[p], start_url=f"{base}/api/auth/oauth/{p}/start") for p in configured]
    return ProvidersOut(providers=listed, chain_id=settings.chain_id)


@router.get("/oauth/{provider}/start")
async def oauth_start(provider: str, request: Request, oauth: OAuthDep, settings: SettingsDep):
    client, configured = oauth
    if provider not in configured:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no configurado.")
    redirect_uri = f"{settings.public_api_url.rstrip('/')}/api/auth/oauth/{provider}/callback"
    return await client.create_client(provider).authorize_redirect(request, redirect_uri)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, oauth: OAuthDep, settings: SettingsDep,
                         session: DbSession, auth: AuthDep):
    client, configured = oauth
    front = settings.frontend_url.rstrip("/")
    if provider not in configured:
        return RedirectResponse(f"{front}/login?error=oauth_provider")
    try:
        token = await client.create_client(provider).authorize_access_token(request)
        profile = await fetch_profile(client.create_client(provider), provider, token)
        user = await auth.upsert_social(session, profile.provider, profile.email, profile.name, profile.email_verified)
    except AuthError as error:
        return RedirectResponse(f"{front}/login?error={error.code}")
    except Exception as error:  # provider hiccups, denied consent, bad state
        log.warning("oauth %s failed: %s", provider, error)
        return RedirectResponse(f"{front}/login?error=oauth")
    # The token travels in the fragment: it never reaches server logs or referrers.
    return RedirectResponse(f"{front}/auth/callback#token={auth.access_token(user)}")


# ------------------------------------------------------------------- SIWE


@router.post("/wallet/nonce", response_model=NonceOut)
def wallet_nonce(body: NonceIn, siwe: SiweDep):
    try:
        return NonceOut(message=siwe.issue(body.address))
    except SiweError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "siwe", "message": str(error)}) from error


@router.post("/wallet/verify", response_model=TokenOut)
async def wallet_verify(body: VerifyIn, siwe: SiweDep, session: DbSession, auth: AuthDep):
    try:
        address = siwe.verify(body.message, body.signature)
        user = await auth.upsert_wallet(session, address)
    except SiweError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "siwe", "message": str(error)}) from error
    except AuthError as error:
        raise _http(error) from error
    return TokenOut(access_token=auth.access_token(user), user=UserOut.from_user(user))


@router.post("/wallet/link", response_model=UserOut)
async def wallet_link(body: VerifyIn, siwe: SiweDep, session: DbSession, auth: AuthDep, user: CurrentUser):
    """Prove a wallet and attach it to the signed-in account."""
    try:
        address = siwe.verify(body.message, body.signature)
        linked = await auth.link_wallet(session, user, address)
    except SiweError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "siwe", "message": str(error)}) from error
    except AuthError as error:
        raise _http(error) from error
    return UserOut.from_user(linked)
