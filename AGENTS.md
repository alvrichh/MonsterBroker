# AGENTS.md — MonsterBroker

Entry point for any AI agent (Claude Code, Codex, Cursor, Gemini CLI…) starting from scratch. Read this, then the detailed guide in [CLAUDE.md](CLAUDE.md) and the design docs in [docs/](docs/).

## What it is
Monorepo for a crypto trading **simulator** and web3 panel:
- `backend/` — Python 3.12 + FastAPI: trading agent (strategies + optional review by Claude), public Binance market data, paper trading (including perpetuals), RSS news radar, on-chain balance lookups, JWT auth.
- `frontend/` — React 19 + Vite + SCSS, JavaScript (no TypeScript). Light/dark tokens in `src/styles/partials/_tokens.scss`.
- `contracts/` — Foundry: MonsterCoin (MBK), soulbound badges and certificates for Base Sepolia. Compiled and tested; deploy pending.

## Hard rules (do not change without an explicit request from the owner)
1. **No real trading.** `PAPER_TRADING=true` is the only supported mode. `LiveExecutor` raises `NotImplementedError` on purpose. Perpetuals are paper too.
2. **Secrets stay out of git.** `.env` is never committed; keys are read only in `backend/app/config.py`. Do not print keys in logs or answers.
3. **Everything works without optional keys.** Claude (`ANTHROPIC_API_KEY`), the on-chain RPC and the OAuth providers are optional; empty means the feature is off, not broken.
4. **Commits:** small, one change each, English messages, **no co-author or AI attribution trailers**.
5. **Language:** UI text and `docs/` are in Spanish (`frontend/src/i18n/locales/*.json`); code, identifiers, commits and READMEs are in English.

## Commands
```bash
cd backend && uvicorn main:app --reload     # API on :8000, docs at /docs
cd backend && pytest -q && ruff check .      # run before committing backend changes
cd frontend && npm run dev                   # :5173, proxies /api to :8000
cd frontend && npm run build                 # run before committing frontend changes
```

## Where to look
- Architecture and the agent loop: `docs/ARCHITECTURE.md`.
- Web3, tokens and certificates: `docs/WEB3.md`, `contracts/README.md`.
- Daily news bot: `.github/workflows/daily-news.yml` writes only to `backend/data/news/` and `docs/news/`.
- CI: `.github/workflows/ci.yml`.

## Before you finish a change
- Backend: `pytest -q` and `ruff check .` pass.
- Frontend: `npm run build` passes; check the page in both light and dark theme.
- The change is described in the commit message, and no file outside the task was touched.
