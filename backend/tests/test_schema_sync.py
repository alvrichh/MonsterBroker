"""init_db() has to bring a users table created by an older version up to
date: the social/wallet columns were added after the first deployments."""

import asyncio
import sqlite3
from pathlib import Path

LEGACY_USERS = """
CREATE TABLE users (
    id VARCHAR(16) NOT NULL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(80) NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    role VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL,
    is_verified BOOLEAN NOT NULL,
    created_at DATETIME NOT NULL,
    verified_at DATETIME,
    last_login_at DATETIME
)
"""
LEGACY_ROW = "INSERT INTO users VALUES ('u1', 'old@test.com', 'Old', 'x', 'user', 1, 1, '2026-01-01', NULL, NULL)"


def _sync() -> None:
    from app.db.database import dispose_db, init_db

    async def run():
        await init_db()
        await dispose_db()  # the engine must not outlive this event loop

    asyncio.run(run())


def test_missing_columns_are_added(settings_env, tmp_path: Path):
    db = tmp_path / "test.db"
    with sqlite3.connect(db) as conn:
        conn.execute(LEGACY_USERS)
        conn.execute(LEGACY_ROW)

    _sync()

    with sqlite3.connect(db) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        assert {"provider", "wallet_address"} <= columns
        assert conn.execute("SELECT provider, wallet_address FROM users").fetchone() == ("password", None)
        indexes = {row[1]: row[2] for row in conn.execute("PRAGMA index_list(users)")}
        assert indexes.get("ix_users_wallet_address") == 1  # unique

    _sync()  # idempotent
