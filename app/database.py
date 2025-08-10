from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from .config import get_settings


settings = get_settings()

is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

if is_sqlite:
    # Avoid connection pool contention/timeouts with SQLite by disabling pooling
    engine = create_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
        poolclass=NullPool,
    )
else:
    # Bigger pool for Postgres
    engine = create_engine(
        settings.database_url,
        echo=False,
        future=True,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


