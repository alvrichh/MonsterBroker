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
| Perpetuos en papel (largos y cortos) | `PUT /api/bot/config {"market":"perp","leverage":3}` | listo: margen aislado, funding, liquidación |
| Futuros (mark, funding, OI, liquidaciones en vivo) | `GET /api/futures/*` + página `/futures` | listo (Binance USDT-M público) |
| Gráficas de velas, mercado global, top 20, DeFi | `GET /api/market/*`, `/api/defi/*` | listo (CoinGecko, alternative.me, DefiLlama) |
| Revisión de señales con Claude | automática si hay `ANTHROPIC_API_KEY` | listo |
| Radar de noticias cripto | `GET /api/news/latest`, `/archive?tag=&q=` + Action diaria | listo |
| Saldos on-chain | `GET /api/wallet/balance?address=&chain=` | requiere `WEB3_RPC_URL` |
| Cuentas: registro con verificación por correo, login JWT, reset de contraseña | `POST /api/auth/register`, `/verify`, `/login`, `/forgot-password`, `/reset-password` | listo (SQLite/Postgres) |
| Panel de administración (usuarios, roles, activar/verificar/borrar) | `GET /api/admin/users`, `/stats` + página `/admin` | listo (rol `admin`) |
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

## Cuentas, base de datos y correo

- **Base de datos**: SQLAlchemy async. Sin configurar nada usa SQLite en
  `backend/data/monsterbroker.db`. Para producción pon un Postgres gratuito
  en `DATABASE_URL` (Neon no pausa el proyecto; Supabase lo pausa tras 7 días
  sin uso). Vale la URL tal cual la da el proveedor (`postgresql://…?sslmode=require`):
  se normaliza para asyncpg. Las tablas se crean al arrancar, por la URL sin
  pooler (`DATABASE_URL_UNPOOLED`) si existe.
- **Neon desde la terminal**: el repo lleva los *agent skills* de Neon en
  `.claude/skills/` (`npx neon skills -y`, requiere Node ≥ 22). `npx neon claim
  create --env-pull` crea un Postgres sin cuenta y escribe `DATABASE_URL` en
  `.env.local` (el backend lo lee); `npx neon claim accept` lo pasa a tu
  cuenta. Un proyecto sin reclamar caduca a las 72 h.
- **Registro**: el usuario recibe un correo con un enlace de confirmación
  (caduca en 24 h) y no puede entrar hasta confirmarlo. Con
  `REQUIRE_EMAIL_VERIFICATION=false` entra directamente.
- **Correo**: `EMAIL_BACKEND=console` (por defecto) imprime el enlace en el
  log del backend y, en `DEBUG`, lo devuelve en la respuesta de registro para
  que la pantalla lo muestre. `resend` usa la API de Resend (gratis 100/día;
  hasta verificar tu dominio solo entrega a tu propio correo desde
  `onboarding@resend.dev`). `smtp` sirve para Brevo (300/día) o cualquier
  relay. Un remitente `noreply@tudominio` exige verificar el dominio
  (SPF/DKIM) en el proveedor.
- **Admin**: quien se registre con un email de `ADMIN_EMAILS` es admin.
  También: `cd backend && python -m app.cli promote tu@correo.com`
  (`list`, `demote`, `verify`).
- **Acceso**: la home es pública; Mercado, Futuros, Bot, Noticias, Wallet y
  DeFi piden cuenta confirmada; `/admin` pide rol admin. En la API, `/bot` y
  `/wallet` exigen token; los datos de mercado siguen siendo públicos.

## Tests

```bash
cd backend && pytest -q && ruff check .
cd frontend && npm run build
```

## Aviso

Esto es un proyecto de aprendizaje. El bot opera en papel; nada aquí es
asesoramiento financiero.
