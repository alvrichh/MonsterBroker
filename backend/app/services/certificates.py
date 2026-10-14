"""Course certificates: a course is a set of things the user has done
(events); finishing it issues a certificate with a public verification code
and a rendered SVG. Pro members get it without the free-version watermark;
on-chain minting (MonsterCertificate.grant) comes with the deploy."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from html import escape

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Certificate, User
from app.services.levels import outranks
from app.services.membership import as_utc
from app.utils.helpers import utc_now


@dataclass(frozen=True, slots=True)
class Course:
    id: str
    title: str
    subtitle: str
    requires: tuple[str, ...]  # user events that complete it


COURSES: dict[str, Course] = {
    c.id: c
    for c in (
        Course("monster-starter", "Trading en papel con el Monstruo",
               "Estrategias técnicas, órdenes simuladas y lectura de velas reales", ("bot_tick",)),
        Course("futures-101", "Futuros 101",
               "Precio mark, funding, open interest, basis y liquidaciones", ("glossary_read",)),
        Course("perps-101", "Perpetuos 101",
               "Largos y cortos con apalancamiento, margen aislado, funding y liquidación", ("perp_mode", "bot_tick")),
    )
}

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def new_code() -> str:
    return "MB-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


class CertificateError(Exception):
    def __init__(self, message: str, code: str, status: int = 400) -> None:
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


class CertificateOut(BaseModel):
    code: str
    course: str
    course_title: str
    holder: str
    tier: str
    issued_at: str
    nft_tx: str | None = None
    verify_url: str
    svg_url: str


class CourseOut(BaseModel):
    id: str
    title: str
    subtitle: str
    requires: list[str]
    done: list[str] = []
    completed: bool = False
    certificate: CertificateOut | None = None


LABELS = {
    "es": {
        "kicker": "CERTIFICADO DE APRENDIZAJE", "certifies": "Se certifica que", "completed": "ha completado",
        "date": "Fecha", "code": "Código de verificación", "verify": "Verifica en", "seal": "VERIFICADO",
        "free": "VERSIÓN GRATUITA · CON PRO EL CERTIFICADO VA LIMPIO", "nft": "También acuñado como NFT en Base",
        "level": "NIVEL {tier}", "bronze": "BRONCE", "silver": "PLATA", "gold": "ORO", "platinum": "PLATINO",
    },
    "en": {
        "kicker": "CERTIFICATE OF LEARNING", "certifies": "This certifies that", "completed": "has completed",
        "date": "Date", "code": "Verification code", "verify": "Verify at", "seal": "VERIFIED",
        "free": "FREE VERSION · PRO MEMBERS GET IT CLEAN", "nft": "Also minted as an NFT on Base",
        "level": "{tier} LEVEL", "bronze": "BRONZE", "silver": "SILVER", "gold": "GOLD", "platinum": "PLATINUM",
    },
}

# Frame, seal and label colours per level: (light, dark).
TIER_COLOURS = {
    "bronze": ("#e09a5a", "#9a5a2a"),
    "silver": ("#e6ebf0", "#8e9aa6"),
    "gold": ("#ffb347", "#ff7a1a"),
    "platinum": ("#d9f1ff", "#7fb6e8"),
}

DISPLAY = "'Space Grotesk', 'Instrument Sans', 'Segoe UI', system-ui, sans-serif"
MONO = "'JetBrains Mono', Consolas, ui-monospace, monospace"


def _fit(text: str, base: int, comfortable: int) -> int:
    """Shrink the font for long names so they stay inside the frame."""
    if len(text) <= comfortable:
        return base
    return max(int(base * comfortable / len(text)), base // 2)


class CertificateService:
    def __init__(self, site_base: str, api_base: str) -> None:
        self.site_base = site_base.rstrip("/")
        self.api_base = api_base.rstrip("/")

    # --------------------------------------------------------------- courses

    @staticmethod
    def progress(course: Course, events: set[str]) -> tuple[list[str], bool]:
        done = [e for e in course.requires if e in events]
        return done, len(done) == len(course.requires)

    def course_out(self, course: Course, events: set[str] | None, cert: Certificate | None) -> CourseOut:
        done, completed = self.progress(course, events or set())
        return CourseOut(id=course.id, title=course.title, subtitle=course.subtitle, requires=list(course.requires),
                         done=done, completed=completed, certificate=self.to_out(cert) if cert else None)

    # ---------------------------------------------------------- certificates

    def to_out(self, cert: Certificate) -> CertificateOut:
        return CertificateOut(
            code=cert.id, course=cert.course, course_title=COURSES[cert.course].title, holder=cert.holder,
            tier=cert.tier or "bronze", issued_at=as_utc(cert.issued_at).isoformat(), nft_tx=cert.nft_tx,
            verify_url=f"{self.site_base}/certificates/verify/{cert.id}",
            svg_url=f"{self.api_base}/api/certificates/{cert.id}.svg",
        )

    @staticmethod
    async def mine(session: AsyncSession, user_id: str) -> dict[str, Certificate]:
        rows = await session.scalars(select(Certificate).where(Certificate.user_id == user_id))
        return {cert.course: cert for cert in rows}

    @staticmethod
    async def by_code(session: AsyncSession, code: str) -> Certificate | None:
        return await session.get(Certificate, code.strip().upper())

    async def issue(self, session: AsyncSession, user: User, course_id: str, holder: str | None,
                    events: set[str], tier: str = "bronze") -> Certificate:
        """Issue (once) the certificate of a finished course at the holder's
        current level. Issuing again upgrades the tier when the holder has
        levelled up since; the code and the name stay."""
        course = COURSES.get(course_id)
        if course is None:
            raise CertificateError("Ese curso no existe.", "unknown_course", 404)
        _, completed = self.progress(course, events)
        if not completed:
            raise CertificateError("Todavía no has completado ese curso.", "not_completed")
        existing = (await self.mine(session, user.id)).get(course_id)
        if existing:
            if outranks(tier, existing.tier or "bronze"):
                existing.tier = tier
                await session.commit()
                await session.refresh(existing)
            return existing
        name = (holder or "").strip() or user.name
        cert = Certificate(id=new_code(), user_id=user.id, course=course_id, holder=name[:80], tier=tier,
                           issued_at=utc_now())
        session.add(cert)
        await session.commit()
        await session.refresh(cert)
        return cert

    # ---------------------------------------------------------------- render

    def render_svg(self, cert: Certificate, clean: bool, lang: str = "es") -> str:
        """The certificate as a 1200×850 SVG in the brand's colours. `clean`
        drops the free-version watermark (Pro members)."""
        course = COURSES[cert.course]
        label = LABELS.get(lang, LABELS["es"])
        holder = escape(cert.holder)
        verify_url = f"{self.site_base}/certificates/verify/{cert.id}"
        issued = as_utc(cert.issued_at)
        date = issued.strftime("%d/%m/%Y") if lang == "es" else issued.strftime("%Y-%m-%d")
        tier = cert.tier if cert.tier in TIER_COLOURS else "bronze"
        light, dark = TIER_COLOURS[tier]
        watermark = "" if clean else (
            f'<text transform="rotate(-18 600 470)" x="600" y="500" text-anchor="middle" font-family="{DISPLAY}" '
            f'font-size="150" font-weight="700" fill="#ff7a1a" opacity="0.07">FREE</text>'
            f'<text x="600" y="806" text-anchor="middle" font-size="11" letter-spacing="3" fill="#8ea2ad">{label["free"]}</text>'
        )
        nft = (
            f'<text x="80" y="640" font-size="14" fill="#3ddc97">{label["nft"]} · {escape(cert.nft_tx[:18])}…</text>'
            if cert.nft_tx else ""
        )
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 850" width="1200" height="850" font-family="'Instrument Sans', 'Segoe UI', system-ui, sans-serif">
  <title>{label["kicker"]} · {holder} · {escape(course.title)}</title>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff7a1a"/><stop offset="1" stop-color="#ffb347"/></linearGradient>
    <linearGradient id="tier" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{light}"/><stop offset="1" stop-color="{dark}"/></linearGradient>
  </defs>
  <rect width="1200" height="850" fill="#0a1c26"/>
  <path d="M0 0H1200V110C900 90 450 150 0 210Z" fill="#0e2d3a"/>
  <path d="M0 210C450 150 900 90 1200 110" fill="none" stroke="url(#g)" stroke-width="6"/>
  <rect x="40" y="40" width="1120" height="770" rx="24" fill="none" stroke="url(#tier)" stroke-opacity="0.9" stroke-width="3"/>
  <rect x="52" y="52" width="1096" height="746" rx="18" fill="none" stroke="{light}" stroke-opacity="0.25" stroke-width="1"/>
  <text x="80" y="92" font-family="{DISPLAY}" font-size="36" font-weight="700" fill="#f0ede6">Monster<tspan fill="#ff7a1a">B</tspan>roker</text>
  <text x="80" y="118" font-size="13" letter-spacing="3" fill="#8ea2ad">FREE LEARN ABOUT CRYPTO</text>
  {watermark}
  <text x="600" y="300" text-anchor="middle" font-size="16" letter-spacing="6" fill="#ff7a1a">{label["kicker"]}</text>
  <text x="600" y="350" text-anchor="middle" font-size="20" fill="#cbd6dd">{label["certifies"]}</text>
  <text x="600" y="430" text-anchor="middle" font-family="{DISPLAY}" font-size="{_fit(cert.holder, 64, 22)}" font-weight="700" fill="#f0ede6">{holder}</text>
  <line x1="300" y1="455" x2="900" y2="455" stroke="#ff7a1a" stroke-opacity="0.6" stroke-width="2"/>
  <text x="600" y="505" text-anchor="middle" font-size="20" fill="#cbd6dd">{label["completed"]}</text>
  <text x="600" y="560" text-anchor="middle" font-family="{DISPLAY}" font-size="{_fit(course.title, 40, 34)}" font-weight="700" fill="#ffb347">{escape(course.title)}</text>
  <text x="600" y="598" text-anchor="middle" font-size="18" fill="#8ea2ad">{escape(course.subtitle)}</text>
  {nft}
  <circle cx="1010" cy="680" r="62" fill="#0e2d3a" stroke="url(#tier)" stroke-width="7"/>
  <circle cx="1010" cy="680" r="50" fill="none" stroke="{light}" stroke-opacity="0.35" stroke-width="1"/>
  <text x="1010" y="674" text-anchor="middle" font-family="{DISPLAY}" font-size="34" font-weight="700" fill="#f0ede6">M<tspan fill="#ff7a1a">B</tspan></text>
  <text x="1010" y="702" text-anchor="middle" font-size="10" letter-spacing="2" fill="#8ea2ad">{label["seal"]}</text>
  <text x="1010" y="772" text-anchor="middle" font-family="{DISPLAY}" font-size="15" font-weight="700" letter-spacing="4" fill="{light}">{label["level"].format(tier=label[tier])}</text>
  <text x="80" y="690" font-size="14" fill="#8ea2ad">{label["date"]}</text>
  <text x="80" y="716" font-size="20" fill="#f0ede6">{date}</text>
  <text x="80" y="758" font-size="14" fill="#8ea2ad">{label["code"]}</text>
  <text x="80" y="784" font-family="{MONO}" font-size="20" fill="#f0ede6">{cert.id}</text>
  <text x="420" y="758" font-size="14" fill="#8ea2ad">{label["verify"]}</text>
  <text x="420" y="784" font-family="{MONO}" font-size="15" fill="#ff7a1a">{escape(verify_url)}</text>
</svg>
"""
