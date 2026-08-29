from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
from backend.config import DATABASE_URL

# Configure engine with robust connection pooling
engine_kwargs = {
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("postgresql"):
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600,
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """
    FastAPI dependency that yields a database session and ensures it is closed after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
