"""What the news radar asks Claude once the feeds are in."""

from __future__ import annotations

import json

from app.news.collector import NewsItem

MAX_ITEMS = 30
MAX_CHARS = 18_000

DIGEST_SYSTEM = """Eres el editor del radar de noticias cripto de MonsterBroker. Recibes titulares y resúmenes \
de medios especializados publicados en las últimas horas.

Devuelve únicamente un objeto JSON, sin texto alrededor:
{"headline": "titular del día, máximo 90 caracteres, en español",
 "insight": "qué está pasando y por qué importa, máximo 320 caracteres, en español, sin consejos de inversión"}

No inventes hechos que no estén en los titulares. Si las noticias son dispares, resume los dos o tres temas \
que más se repiten."""


def digest_prompt(items: list[NewsItem]) -> str:
    rows = [
        {"title": i.title, "source": i.source, "date": i.date, "tags": i.tags, "summary": i.summary}
        for i in items[:MAX_ITEMS]
    ]
    return json.dumps(rows, ensure_ascii=False)[:MAX_CHARS]
