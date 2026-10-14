# MonsterBroker

![MonsterBroker · Free learn about crypto](frontend/public/images/brand/banner-wide.png)

Bot de trading cripto, panel web3 y radar de noticias. Nace del prototipo
estático de 2021 (`alvrichh/Front-end/PROYECTO/MonsterBroker.html`) y
reutiliza la base técnica del portfolio
([alvrich.vercel.app](https://alvrich.vercel.app)): React + SCSS + Vite,
tokens de tema claro/oscuro y el bot diario de noticias con GitHub Actions.

- **backend/** · Python 3.12 + FastAPI. Agente de trading (estrategias +
  revisión opcional con Claude), datos de mercado públicos de Binance, paper
  trading, colector de noticias RSS, consulta de saldos on-chain y auth JWT.
- **frontend/** · React 19 + Vite + SCSS (JavaScript, sin TypeScript).

## Arrancar en local

```bash
cp .env.example .env            # opcional: todo funciona vacío

# backend  → http://localhost:8000  (docs en /docs)
cd backend
python -m venv .venv && .venv/Scripts/activate   # Linux/mac: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload

# frontend → http://localhost:5173  (proxy /api → backend)
cd frontend
npm install
npm run dev
```

O todo junto con Docker: `docker compose up --build`.

## Qué hay

| Área | Endpoint / pantalla | Estado |
| --- | --- | --- |
| Precios y velas (Binance público) | `GET /api/market/tickers`, `/ohlcv`, `/indicators` | listo |
| Bot de trading en papel | `GET /api/bot/status`, `POST /api/bot/tick`, `/trades` | listo, estrategias `sma_cross` y `rsi_reversion` |
| Revisión de señales con Claude | automática si hay `ANTHROPIC_API_KEY` | listo |
| Radar de noticias cripto | `GET /api/news/latest`, `/archive?tag=&q=` + Action diaria | listo |
| Saldos on-chain | `GET /api/wallet/balance?address=&chain=` | requiere `WEB3_RPC_URL` |
| Auth (registro / login / me) | `POST /api/auth/register`, `/login`, `GET /me` | listo (JSON + JWT) |
| Trading real | — | **no conectado a propósito** (`PAPER_TRADING=true`) |

## Estructura

```text
backend/
  main.py                 entrada (uvicorn main:app)
  app/
    config.py             settings (.env)
    api/                  routers FastAPI + schemas
    agent/                agente: loop, estado, memoria, ejecutor
    strategies/           señales a partir de velas
    tools/                indicadores técnicos
    models/               cliente Claude
    prompts/              prompts del agente y del radar
    news/                 fuentes RSS, tags, colector
    onchain/              web3: cadenas y saldos
    services/             mercado (Binance), auth
    utils/                logger, helpers
  tests/
  data/                   news/ (commiteado por el bot), paper/ (estado local)
  logs/
frontend/
  src/pages, components, hooks, lib, i18n, styles
  public/images/{brand,coins,partners}   assets heredados del prototipo
docs/news/                informes diarios del radar
.github/workflows/        ci.yml · daily-news.yml
```

## Tests

```bash
cd backend && pytest -q && ruff check .
cd frontend && npm run build
```

## Aviso

Esto es un proyecto de aprendizaje. El bot opera en papel; nada aquí es
asesoramiento financiero.
