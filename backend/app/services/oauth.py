"""Social login: Google and GitHub through Authlib, Microsoft through its
OAuth2 endpoints + Graph (its id_token issuer varies by tenant, so we don't
parse it). A provider is live only when its client id and secret are set."""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from pydantic import BaseModel

from app.config import Settings


class SocialProfile(BaseModel):
    provider: str
    subject: str  # the provider's user id
    email: str
    name: str
    email_verified: bool = True


LABELS = {"google": "Google", "github": "GitHub", "microsoft": "Microsoft"}


def build_oauth(settings: Settings) -> tuple[OAuth, list[str]]:
    """Register every configured provider. Returns the client and the names."""
    oauth = OAuth()
    configured: list[str] = []

    if settings.google_client_id and settings.google_client_secret:
        oauth.register(
            "google", client_id=settings.google_client_id, client_secret=settings.google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
        configured.append("google")

    if settings.github_client_id and settings.github_client_secret:
        oauth.register(
            "github", client_id=settings.github_client_id, client_secret=settings.github_client_secret,
            authorize_url="https://github.com/login/oauth/authorize",
            access_token_url="https://github.com/login/oauth/access_token",
            api_base_url="https://api.github.com/",
            client_kwargs={"scope": "read:user user:email"},
        )
        configured.append("github")

    if settings.microsoft_client_id and settings.microsoft_client_secret:
        tenant = settings.microsoft_tenant or "common"
        oauth.register(
            "microsoft", client_id=settings.microsoft_client_id, client_secret=settings.microsoft_client_secret,
            authorize_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            access_token_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            api_base_url="https://graph.microsoft.com/v1.0/",
            client_kwargs={"scope": "User.Read"},
        )
        configured.append("microsoft")

    return oauth, configured


async def fetch_profile(client, provider: str, token: dict) -> SocialProfile:
    """Normalise what each provider knows about the user."""
    if provider == "google":
        info = token.get("userinfo") or (await client.userinfo(token=token))
        return SocialProfile(provider="google", subject=str(info["sub"]), email=info["email"].lower(),
                             name=info.get("name") or info["email"].split("@")[0],
                             email_verified=bool(info.get("email_verified", True)))

    if provider == "github":
        user = (await client.get("user", token=token)).json()
        emails = (await client.get("user/emails", token=token)).json()
        primary = next((e for e in emails if e.get("primary") and e.get("verified")), None) \
            or next((e for e in emails if e.get("verified")), None)
        if not primary:
            raise ValueError("GitHub account has no verified email")
        return SocialProfile(provider="github", subject=str(user["id"]), email=primary["email"].lower(),
                             name=user.get("name") or user.get("login") or "GitHub")

    if provider == "microsoft":
        me = (await client.get("me", token=token)).json()
        email = (me.get("mail") or me.get("userPrincipalName") or "").lower()
        if "@" not in email:
            raise ValueError("Microsoft account has no email")
        return SocialProfile(provider="microsoft", subject=str(me["id"]), email=email,
                             name=me.get("displayName") or email.split("@")[0])

    raise ValueError(f"unknown provider {provider}")
