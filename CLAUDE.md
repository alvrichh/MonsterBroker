# MonsterBroker — guía para agentes

Monorepo: `backend/` (Python 3.12, FastAPI) y `frontend/` (React 19, Vite,
JSX, SCSS). Español en UI y en `docs/`; los README, los commits, el código y
los identificadores en inglés.
Commits pequeños (uno por cambio), sin trailers de co-autoría.

## Comandos

```bash
cd backend && uvicorn main:app --reload        # API en :8000, docs en /docs
cd backend && pytest -q && ruff check .
cd backend && python -m app.news.collector     # un pase del radar de noticias
cd frontend && npm run dev                     # :5173, proxy /api → :8000
cd frontend && npm run build
```

## Reglas

- **Nunca trading real.** `PAPER_TRADING=true` es el único modo soportado;
  `LiveExecutor` lanza `NotImplementedError` a propósito. No lo "arregles"
  sin que el usuario lo pida de forma explícita. Los perpetuos
  (`config.market = perp`, largos y cortos con apalancamiento) son siempre
  papel: `PerpExecutor` simula margen aislado, comisión taker, funding y
  liquidación con datos públicos de Binance Futures.
- `.env` no se commitea. Las claves se leen solo en `app/config.py`.
- El bot de noticias (Action `daily-news.yml`) solo escribe en
  `backend/data/news/` y `docs/news/`. Nada más se commitea automáticamente.
- Los datos de mercado vienen del REST público de Binance; sin claves.
- Claude es opcional: con `ANTHROPIC_API_KEY` vacía el agente opera solo con
  las estrategias y el radar no genera resumen. Todo debe seguir funcionando.
- Cliente LLM: SDK oficial `anthropic`, modelo por defecto `claude-opus-5-5`,
  thinking adaptativo. No usar `budget_tokens` ni prefill.

## Convenciones

- Usuarios en base de datos (SQLAlchemy async, `app/db/`): SQLite por defecto,
  Postgres vía `DATABASE_URL`. Sesiones JWT HS256 (`JWT_SECRET` ≥ 32 bytes);
  los enlaces de verificación y de reset son JWT con `purpose` y caducidad.
  El correo sale por `app/services/email.py` (`console` | `resend` | `smtp`);
  nunca bloquea una petición (va en `BackgroundTasks`). Las respuestas de
  error de auth llevan `detail = {"code", "message"}` y el frontend lee el
  `code`.
- Backend: pydantic v2 para todo lo que cruza la API; funciones puras en
  `tools/` y `strategies/` (listas de floats, sin pandas) para que se testeen
  sin red. Estado del agente en JSON (`data/paper/state.json`).
- Frontend: tokens en `src/styles/partials/_tokens.scss` (tema claro/oscuro
  vía `data-theme` en `<html>`, aplicado antes del primer paint desde
  `index.html`). `localStorage` solo a través de `src/lib/storage.js`.
  Un partial SCSS por área. Texto visible en `src/i18n/locales/*.json`.
- Assets heredados del prototipo 2021 en `frontend/public/images/`:
  `brand/` (logo, wordmark, header), `coins/`, `partners/`.

## Referencias

- Prototipo original: <https://github.com/alvrichh/Front-end/blob/main/PROYECTO/MonsterBroker.html>
- Base técnica (tokens, i18n, radar diario): `../MyPersonalWeb`
