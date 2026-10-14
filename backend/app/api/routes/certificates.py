"""Courses, their progress, and the certificates they issue. Verification
and the rendered SVG are public: a certificate is meant to be shared."""

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.api.deps import CertsDep, CurrentUser, DbSession, OptionalUser, QuestsDep
from app.db.models import User
from app.services.certificates import COURSES, CertificateError, CertificateOut, CourseOut
from app.services.membership import is_pro

router = APIRouter()


class IssueIn(BaseModel):
    name: str | None = Field(None, max_length=80)  # printed on the certificate; default: the account name


class VerifyOut(BaseModel):
    valid: bool
    certificate: CertificateOut | None = None


@router.get("/courses", response_model=list[CourseOut])
async def courses(session: DbSession, certs: CertsDep, quests: QuestsDep, user: OptionalUser):
    """The catalogue; with a session, each course carries the user's progress."""
    events = await quests.events_for(session, user.id) if user else None
    mine = await certs.mine(session, user.id) if user else {}
    return [certs.course_out(c, events, mine.get(c.id)) for c in COURSES.values()]


@router.get("/mine", response_model=list[CertificateOut])
async def mine(session: DbSession, certs: CertsDep, user: CurrentUser):
    return [certs.to_out(c) for c in (await certs.mine(session, user.id)).values()]


@router.post("/{course_id}/issue", response_model=CertificateOut, status_code=status.HTTP_201_CREATED)
async def issue(course_id: str, body: IssueIn, session: DbSession, certs: CertsDep, quests: QuestsDep,
                user: CurrentUser):
    try:
        cert = await certs.issue(session, user, course_id, body.name, await quests.events_for(session, user.id))
    except CertificateError as error:
        raise HTTPException(error.status, {"code": error.code, "message": error.message}) from error
    return certs.to_out(cert)


@router.get("/{code}.svg")
async def render(code: str, session: DbSession, certs: CertsDep, lang: str = Query("es", pattern="^(es|en)$")):
    cert = await certs.by_code(session, code)
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown certificate")
    holder = await session.get(User, cert.user_id)  # the watermark follows the holder's current plan
    svg = certs.render_svg(cert, clean=bool(holder and is_pro(holder)), lang=lang)
    return Response(svg, media_type="image/svg+xml",
                    headers={"Content-Disposition": f'inline; filename="monsterbroker-{cert.id}.svg"'})


@router.get("/{code}", response_model=VerifyOut)
async def verify(code: str, session: DbSession, certs: CertsDep):
    cert = await certs.by_code(session, code)
    return VerifyOut(valid=cert is not None, certificate=certs.to_out(cert) if cert else None)
