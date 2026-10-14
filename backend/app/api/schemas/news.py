from pydantic import BaseModel

from app.news.collector import NewsItem


class ArchiveOut(BaseModel):
    items: list[NewsItem]
    total: int
    limit: int
    offset: int


class TagsOut(BaseModel):
    tags: dict[str, int]
