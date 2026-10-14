# MonsterBroker

![MonsterBroker · Free learn about crypto](frontend/public/images/brand/banner-wide.png)

Crypto trading bot, web3 panel and news radar. It grows out of the static
2021 prototype (`alvrichh/Front-end/PROYECTO/MonsterBroker.html`) and reuses
the technical base of the portfolio
([alvrich.vercel.app](https://alvrich.vercel.app)): React + SCSS + Vite,
light/dark theme tokens and the daily news bot on GitHub Actions.

- **backend/** · Python 3.12 + FastAPI. Trading agent (strategies + optional
  review by Claude), public Binance market data, paper trading, RSS news
  collector, on-chain balance lookups and JWT auth.
- **frontend/** · React 19 + Vite + SCSS (JavaScript, no TypeScript).

## Run it locally

```bash
cp .env.example .env            # optional: everything works empty

# backend  → http://localhost:8000  (docs at /docs)
cd backend
python -m venv .venv && .venv/Scripts/activate   # Linux/mac: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --reload

# frontend → http://localhost:5173  (proxy /api → backend)
cd frontend
npm install
npm run dev
```

Or everything at once with Docker: `docker compose up --build`.

## What's in it

| Area | Endpoint / screen | Status |
| --- | --- | --- |
| Prices and candles (public Binance) | `GET /api/market/tickers`, `/ohlcv`, `/indicators` | done |
| Paper trading bot | `GET /api/bot/status`, `POST /api/bot/tick`, `/trades` | done, strategies `sma_cross` and `rsi_reversion` |
| Paper perpetuals (longs and shorts) | `PUT /api/bot/config {"market":"perp","leverage":3}` | done: isolated margin, funding, liquidation |
| Futures (mark price, funding, OI, live liquidations) | `GET /api/futures/*` + `/futures` page | done (public Binance USDT-M) |
| Candle charts, global market, top 20, DeFi | `GET /api/market/*`, `/api/defi/*` | done (CoinGecko, alternative.me, DefiLlama) |
| Signal review by Claude | automatic when `ANTHROPIC_API_KEY` is set | done |
| Crypto news radar | `GET /api/news/latest`, `/archive?tag=&q=` + daily Action | done |
| On-chain balances | `GET /api/wallet/balance?address=&chain=` | needs `WEB3_RPC_URL` |
| Accounts: sign-up with email confirmation, JWT login, password reset | `POST /api/auth/register`, `/verify`, `/login`, `/forgot-password`, `/reset-password` | done (SQLite/Postgres) |
| One-click sign-in: Google, GitHub, Microsoft, wallet (SIWE) | `GET /api/auth/oauth/providers`, `/oauth/{provider}/start`, `POST /api/auth/wallet/nonce`, `/verify`, `/link` | done (providers need credentials) |
| Admin panel (users, roles, activate/verify/delete) | `GET /api/admin/users`, `/stats` + `/admin` page | done (`admin` role) |
| Learn-to-earn: quests, claims, badge metadata | `GET /api/token/info`, `/me`, `POST /api/token/claim`, `/events` + `/token` page | done (minting waits for the deploy) |
| Course certificates: progress, issue, public verification, SVG render | `GET /api/certificates/courses`, `POST /api/certificates/{course}/issue`, `GET /api/certificates/{code}` and `.svg` + `/certificates` pages | done |
| Membership (free / Pro): admin grants, a month of Pro for finishing every quest | `PATCH /api/admin/users/{id} {plan, plan_days}` + `/pro` page | done (card payments later) |
| Member reviews (moderated) with real usage numbers; legal & privacy page | `GET/POST /api/reviews`, `GET/PATCH /api/admin/reviews` + home section, `/legal` | done (sample cards are labelled as samples) |
| Member levels Bronze → Silver → Gold → Platinum from real activity; certificates carry the level and upgrade | `GET /api/levels`, `/api/levels/me` + medals on `/pro`, `/certificates`, the header | done |
| Smart contracts: MonsterCoin (MBK), soulbound Monster Badges, paid Monster Certificates | `contracts/` (Foundry, Base Sepolia) | compiled and tested; deploy pending |
| Real trading | — | **not connected on purpose** (`PAPER_TRADING=true`) |

## Layout

```text
backend/
  main.py                 entry point (uvicorn main:app)
  app/
    config.py             settings (.env)
    api/                  FastAPI routers + schemas
    agent/                agent: loop, state, memory, executor
    strategies/           signals out of candles
    tools/                technical indicators
    models/               Claude client
    prompts/              agent and radar prompts
    news/                 RSS sources, tags, collector
    onchain/              web3: chains and balances
    services/             market (Binance), auth, oauth, siwe, email
    utils/                logger, helpers
  tests/
  data/                   news/ (committed by the bot), paper/ (local state)
  logs/
frontend/
  src/pages, components, hooks, lib, i18n, styles
  public/images/{brand,coins,partners}   assets inherited from the prototype
contracts/                Foundry: MonsterToken, MonsterBadge, tests, deploy script
docs/news/                daily radar reports · docs/WEB3.md strategy
.github/workflows/        ci.yml · daily-news.yml
```

## Accounts, database and email

- **Database**: async SQLAlchemy. With nothing configured it uses SQLite at
  `backend/data/monsterbroker.db`. For production point `DATABASE_URL` at a
  free Postgres (Neon doesn't pause the project; Supabase pauses it after 7
  idle days). The URL works as the provider gives it
  (`postgresql://…?sslmode=require`): it is normalised for asyncpg. Tables
  are created on startup, over the non-pooled URL (`DATABASE_URL_UNPOOLED`)
  when there is one; columns that newer models declare are added to
  existing tables the same way.
- **Neon from the terminal**: the repo ships Neon's *agent skills* in
  `.claude/skills/` (`npx neon skills -y`, needs Node ≥ 22). `npx neon claim
  create --env-pull` creates a Postgres without an account and writes
  `DATABASE_URL` into `.env.local` (the backend reads it); `npx neon claim
  accept` moves it to your account. An unclaimed project expires after 72 h.
- **Sign-up**: the user gets an email with a confirmation link (expires in
  24 h) and cannot sign in until it is confirmed. With
  `REQUIRE_EMAIL_VERIFICATION=false` they get straight in.
- **Email**: `EMAIL_BACKEND=console` (default) prints the link in the backend
  log and, in `DEBUG`, returns it in the register response so the screen can
  show it. `resend` uses the Resend API (free 100/day; until your domain is
  verified it only delivers to your own address from `onboarding@resend.dev`).
  `smtp` works with Brevo (300/day) or any relay. A `noreply@yourdomain`
  sender requires verifying the domain (SPF/DKIM) at the provider.
- **Admin**: whoever signs up with an email listed in `ADMIN_EMAILS` is an
  admin. Also: `cd backend && python -m app.cli promote you@example.com`
  (`list`, `demote`, `verify`).
- **One-click sign-in**: the "Sign in" button opens a small speech bubble
  with Google, GitHub, Microsoft, wallet and email. A provider shows up only
  when its `*_CLIENT_ID` and `*_CLIENT_SECRET` are set in `.env` (redirect
  URI to register at the provider:
  `PUBLIC_API_URL/api/auth/oauth/<provider>/callback`). With a wallet
  (MetaMask, Rabby…) you sign a SIWE message (EIP-4361): no gas, no
  password, and the account creates itself. An email account can link its
  wallet later (`POST /api/auth/wallet/link`).
- **Access**: every section is public so visitors can see what the app
  does; driving the bot needs an account and `/admin` needs the admin role.

## Web3

- `contracts/`: a Foundry project with **MonsterCoin (MBK)**, a capped
  ERC-20 the backend mints as a reward for learning, **Monster Badges**,
  *soulbound* ERC-721 achievements (they cannot be transferred), and
  **Monster Certificates**, paid course certificates with EIP-2981 royalties.
  Built for Base Sepolia (testnet, no real value). Build, tests and
  deployment in [contracts/README.md](contracts/README.md).
- Quests: link a wallet, run a bot tick, read the futures glossary. Each
  claim is recorded in `quest_claims`; with `MINTER_PRIVATE_KEY` and the
  contract addresses set the backend mints MBK and the badge, otherwise the
  claim waits and `python -m app.cli settle` mints it later.
- Certificates: a course is a set of recorded user events; finishing it
  issues a certificate with a public code (`MB-XXXXXXXX`), a verification
  page and an SVG in the brand's colours. Free accounts get a discreet
  watermark; Pro members get it clean.
- Membership: `users.plan` is `free` or `pro` (`plan_until`, `plan_source`).
  Admins are Pro by definition, can grant it from `/admin`, and completing
  every quest earns 30 days. Card payments are the next step.
- The strategy (learn-to-earn, monetisation paths, what MiCA requires) lives
  in [docs/WEB3.md](docs/WEB3.md).

## Tests

```bash
cd backend && pytest -q && ruff check .
cd frontend && npm run build
cd contracts && forge test
```

## Disclaimer

This is a learning project. The bot trades on paper; nothing here is
financial advice.
