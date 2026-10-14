"""The news radar: read the feeds, tag the stories, keep an archive, write a
digest. A port of MyPersonalWeb's AI radar to Python.

Run once from the command line (what the daily GitHub Action does):

    python -m app.news.collector
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from pathlib import Path

import feedparser
import httpx
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.utils.helpers import is_safe_url, read_json, strip_html, today, write_json
from app.utils.logger import get_logger, setup_logging

from .sources import SOURCES, Source
from .tags import get_tags

log = get_logger(__name__)

USER_AGENT = "monsterbroker-news-bot/1.0 (+https://github.com/alvrichh/MonsterBroker)"
LATEST_SIZE = 30
LATEST_PER_SOURCE = 4
ARCHIVE_SIZE = 3000
SUMMARY_CHARS = 280
MAX_AGE_DAYS = 45  # some feeds ship their whole history; the radar is about now

_IMG = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
_WP_TAIL = re.compile(r"\s+The post\s[\s\S]*$")  # "The post X appeared first on Y"


class NewsItem(BaseModel):
    title: str
    source: str
    date: str  # YYYY-MM-DD
    url: str
    summary: str = ""
    image: str = ""
    tags: list[str] = Field(default_factory=list)


class Digest(BaseModel):
    date: str
    headline: str = "Radar cripto"
    insight: str = ""
    items: list[NewsItem] = Field(default_factory=list)


DEFAULT_INSIGHT = "Titulares recientes de medios cripto, agrupados por tema. Resumen con IA no disponible."


# ------------------------------------------------------------------ parsing


def _entry_date(entry: feedparser.FeedParserDict) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return today()
    try:
        return datetime(*parsed[:6], tzinfo=UTC).date().isoformat()
    except (TypeError, ValueError):
        return today()


def is_recent(date: str, today_str: str, max_age_days: int = MAX_AGE_DAYS) -> bool:
    """True unless the story is clearly older than the window. Unparseable
    or future dates pass through rather than silently vanish."""
    try:
        age = (datetime.fromisoformat(today_str) - datetime.fromisoformat(date)).days
    except ValueError:
        return True
    return age <= max_age_days


def _entry_image(entry: feedparser.FeedParserDict, html: str) -> str:
    candidates: list[str] = []
    for key in ("media_thumbnail", "media_content"):
        candidates += [m.get("url", "") for m in entry.get(key, []) or []]
    candidates += [e.get("href", "") for e in entry.get("enclosures", []) or []
                   if str(e.get("type", "")).startswith("image/")]
    match = _IMG.search(html or "")
    if match:
        candidates.append(match.group(1))
    return next((c for c in candidates if is_safe_url(c)), "")


def _entry_summary(entry: feedparser.FeedParserDict) -> tuple[str, str]:
    """(clean text, raw html) of the best description field."""
    content = entry.get("content") or []
    raw = entry.get("summary") or entry.get("description") or (content[0].get("value", "") if content else "")
    clean = _WP_TAIL.sub("", strip_html(raw))
    if len(clean) > SUMMARY_CHARS:
        clean = clean[: SUMMARY_CHARS - 1].rstrip() + "…"
    return clean, raw


def parse_feed(payload: bytes, source: Source) -> list[NewsItem]:
    feed = feedparser.parse(payload)
    items: list[NewsItem] = []
    for entry in feed.entries:
        title = strip_html(entry.get("title", ""))
        url = entry.get("link") or source.homepage
        if not title or not is_safe_url(url):
            continue
        summary, raw = _entry_summary(entry)
        items.append(NewsItem(
            title=title,
            source=source.name,
            date=_entry_date(entry),
            url=url,
            summary=summary,
            image=_entry_image(entry, raw),
            tags=get_tags(title, summary),
        ))
    return items


# ---------------------------------------------------------------- collector


class NewsCollector:
    def __init__(self, settings: Settings | None = None, sources: tuple[Source, ...] = SOURCES) -> None:
        self.settings = settings or get_settings()
        self.sources = sources
        self.data_dir: Path = self.settings.data_dir / "news"
        self.docs_dir: Path = self.settings.docs_dir / "news"
        self.latest_path = self.data_dir / "latest.json"
        self.archive_path = self.data_dir / "archive.json"

    # ------------------------------------------------------------ reading

    async def fetch_source(self, client: httpx.AsyncClient, source: Source) -> list[NewsItem]:
        try:
            response = await client.get(source.url)
            response.raise_for_status()
        except httpx.HTTPError as error:
            log.warning("%s: %s", source.name, error)
            return []
        items = parse_feed(response.content, source)
        log.info("%s: %d stories", source.name, len(items))
        return items

    async def collect(self) -> list[NewsItem]:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True,
                                     headers={"User-Agent": USER_AGENT}) as client:
            batches = await asyncio.gather(*(self.fetch_source(client, s) for s in self.sources))
        seen: set[str] = set()
        fresh: list[NewsItem] = []
        today_str = today()
        for item in (item for batch in batches for item in batch):
            if item.url not in seen and is_recent(item.date, today_str):
                seen.add(item.url)
                fresh.append(item)
        fresh.sort(key=lambda item: item.date, reverse=True)
        return fresh

    # ------------------------------------------------------------ storage

    def latest(self) -> Digest:
        raw = read_json(self.latest_path, None)
        return Digest.model_validate(raw) if raw else Digest(date=today(), insight=DEFAULT_INSIGHT)

    def archive(self) -> list[NewsItem]:
        raw = read_json(self.archive_path, {})
        return [NewsItem.model_validate(i) for i in raw.get("items", [])]

    def search(self, tag: str | None = None, query: str | None = None, limit: int = 40,
               offset: int = 0) -> tuple[list[NewsItem], int]:
        items = self.archive()
        if tag:
            items = [i for i in items if tag.lower() in (t.lower() for t in i.tags)]
        if query:
            needle = query.lower()
            items = [i for i in items if needle in f"{i.title} {i.summary} {i.source}".lower()]
        return items[offset : offset + limit], len(items)

    def tag_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.archive():
            for tag in item.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    def _merge_archive(self, fresh: list[NewsItem]) -> list[NewsItem]:
        by_url = {item.url: item for item in self.archive()}
        for item in fresh:
            by_url[item.url] = item
        merged = sorted(by_url.values(), key=lambda item: item.date, reverse=True)
        return merged[:ARCHIVE_SIZE]

    @staticmethod
    def _pick_latest(items: list[NewsItem]) -> list[NewsItem]:
        per_source: dict[str, int] = {}
        picked: list[NewsItem] = []
        for item in items:
            if per_source.get(item.source, 0) >= LATEST_PER_SOURCE:
                continue
            per_source[item.source] = per_source.get(item.source, 0) + 1
            picked.append(item)
            if len(picked) >= LATEST_SIZE:
                break
        return picked

    # ---------------------------------------------------------------- run

    async def run(self) -> Digest:
        fresh = await self.collect()
        archive = self._merge_archive(fresh)
        latest = self._pick_latest(archive)
        digest = Digest(date=today(), items=latest, insight=DEFAULT_INSIGHT)

        headline_insight = await self._enrich(latest)
        if headline_insight:
            digest.headline, digest.insight = headline_insight

        write_json(self.archive_path, {"updated": digest.date, "count": len(archive),
                                       "items": [i.model_dump() for i in archive]})
        write_json(self.latest_path, digest.model_dump())
        self._write_report(digest, len(archive))
        log.info("radar: %d fresh, %d in archive, %d in latest", len(fresh), len(archive), len(latest))
        return digest

    async def _enrich(self, items: list[NewsItem]) -> tuple[str, str] | None:
        if not self.settings.llm_enabled or not items:
            return None
        try:
            from app.models.llm_client import get_llm

            return await get_llm().news_digest(items)
        except Exception as error:  # the digest is optional; the data is not
            log.warning("news digest with Claude failed: %s", error)
            return None

    def _write_report(self, digest: Digest, archive_size: int) -> None:
        lines = [
            f"# MonsterBroker · Radar cripto · {digest.date}",
            "",
            f"**{digest.headline}**",
            "",
            f"> {digest.insight}",
            "",
            f"{len(digest.items)} titulares en portada · {archive_size} en el archivo.",
            "",
            "## Noticias",
            "",
        ]
        for item in digest.items:
            tags = " ".join(f"`{tag}`" for tag in item.tags)
            lines.append(f"- **[{item.title}]({item.url})** — {item.source} · {item.date} · {tags}")
            if item.summary:
                lines.append(f"  {item.summary}")
        text = "\n".join(lines) + "\n"
        (self.docs_dir / "history").mkdir(parents=True, exist_ok=True)
        (self.docs_dir / "latest.md").write_text(text, encoding="utf-8")
        (self.docs_dir / "history" / f"{digest.date}.md").write_text(text, encoding="utf-8")


_collector: NewsCollector | None = None


def get_news_collector() -> NewsCollector:
    global _collector
    if _collector is None:
        _collector = NewsCollector()
    return _collector


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.logs_dir)
    digest = await NewsCollector(settings).run()
    print(f"{digest.date}: {digest.headline} — {len(digest.items)} stories")


if __name__ == "__main__":
    asyncio.run(main())
