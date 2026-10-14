from app.db.database import normalize_database_url


def test_sqlite_is_left_alone():
    assert normalize_database_url("sqlite+aiosqlite:///x.db") == ("sqlite+aiosqlite:///x.db", {})


def test_neon_pooled_url_becomes_asyncpg_with_ssl_and_no_statement_cache():
    raw = "postgresql://u:p@ep-x-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    url, args = normalize_database_url(raw)
    assert url == "postgresql+asyncpg://u:p@ep-x-pooler.eu-central-1.aws.neon.tech/neondb"
    assert args == {"ssl": "require", "statement_cache_size": 0}


def test_direct_url_keeps_prepared_statements():
    url, args = normalize_database_url("postgres://u:p@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require")
    assert url.startswith("postgresql+asyncpg://") and args == {"ssl": "require"}


def test_explicit_asyncpg_url_is_respected():
    url, args = normalize_database_url("postgresql+asyncpg://u:p@localhost/db?application_name=mb")
    assert url == "postgresql+asyncpg://u:p@localhost/db?application_name=mb" and args == {}
