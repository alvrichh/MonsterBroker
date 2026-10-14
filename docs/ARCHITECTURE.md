# Arquitectura

```
┌──────────────────────────────┐         ┌─────────────────────────────────────┐
│ frontend (React + Vite)      │  /api   │ backend (FastAPI)                   │
│  pages: Home, Dashboard,     │ ──────► │  api/routes: market, bot, news,     │
│  Bot, News, Wallet, Auth     │         │              wallet, auth, health   │
│  lib/api.js (único fetch)    │ ◄────── │         │                           │
└──────────────────────────────┘         │         ▼                           │
                                         │  agent/ ── strategies/ ── tools/    │
                                         │    │  (loop)   (señales)  (indic.)  │
                                         │    ├── executor (paper)             │
                                         │    ├── memory  (data/paper/*.json)  │
                                         │    └── reviewer ── models/llm_client│
                                         │  news/collector ── sources, tags    │
                                         │  services/exchange (Binance público)│
                                         │  onchain/ (web3.py, opcional)       │
                                         └─────────────────────────────────────┘
                                                      ▲
                      GitHub Action daily-news.yml ───┘  (commitea data/news + docs/news)
```

## Flujo de un tick del bot

1. `POST /api/bot/tick` → `TradingAgent.tick()`.
2. Por cada símbolo configurado: velas de Binance → `strategy.evaluate(closes)`
   → `Signal(buy|sell|hold, confidence, reason)`.
3. Si no es `hold` y supera `min_confidence`: revisión opcional con Claude
   (`reviewer.review`) que puede vetar la orden.
4. `PaperExecutor` ejecuta contra el portfolio en papel. Todo queda en
   `Decision`/`Trade` dentro de `data/paper/state.json`.

## Flujo del radar de noticias

1. `NewsCollector.run()` lee las fuentes RSS de `news/sources.py` con httpx +
   feedparser, limpia HTML, saca imagen y fecha, y etiqueta con `news/tags.py`.
2. Fusiona con `data/news/archive.json` (dedupe por URL) y recorta
   `data/news/latest.json` (máx. 4 por fuente).
3. Si hay clave de Claude, pide titular + insight en español.
4. Escribe `docs/news/latest.md` y `docs/news/history/YYYY-MM-DD.md`.

La Action diaria hace exactamente eso y commitea solo esos ficheros, igual
que el "AI Radar" de MyPersonalWeb.
