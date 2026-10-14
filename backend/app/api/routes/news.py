from fastapi import APIRouter, Query

from app.api.deps import NewsDep
from app.api.schemas.news import ArchiveOut, TagsOut
from app.news.collector import Digest

router = APIRouter()


@router.get("/latest", response_model=Digest)
def latest(news: NewsDep):
    return news.latest()


@router.get("/archive", response_model=ArchiveOut)
def archive(news: NewsDep, tag: str | None = None, q: str | None = Query(None, max_length=80),
            limit: int = Query(40, ge=1, le=200), offset: int = Query(0, ge=0)):
    items, total = news.search(tag=tag, query=q, limit=limit, offset=offset)
    return ArchiveOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/tags", response_model=TagsOut)
def tags(news: NewsDep):
    return TagsOut(tags=news.tag_counts())


@router.post("/refresh", response_model=Digest)
async def refresh(news: NewsDep):
    """Read every feed now. The daily Action does this on its own."""
    return await news.run()
