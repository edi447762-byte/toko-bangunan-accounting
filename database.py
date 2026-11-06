"""
Layer database — mendukung SQLite & PostgreSQL via SQLAlchemy.
Switch cukup ganti DATABASE_URL di .env / Streamlit secrets.
"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

# ==================== KONFIG ====================
def get_database_url():
    """Ambil URL dari env, atau Streamlit secrets, fallback ke SQLite."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Coba Streamlit secrets (untuk deploy di Streamlit Cloud)
    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    # Default SQLite
    os.makedirs("data", exist_ok=True)
    return "sqlite:///data/toko_bangunan.db"

DATABASE_URL = get_database_url()

# ==================== ENGINE ====================
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    # Aktifkan foreign keys untuk SQLite
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )

SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))

@contextmanager
def get_conn():
    """Context manager untuk transaksi."""
    conn = engine.connect()
    trans = conn.begin()
    try:
        yield conn
        trans.commit()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()
