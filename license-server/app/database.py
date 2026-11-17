import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def build_database_url():
    value = os.environ.get('DATABASE_URL', '').strip()
    if not value:
        raise RuntimeError('DATABASE_URL is not configured')
    if value.startswith('postgres://'):
        value = value.replace('postgres://', 'postgresql+psycopg://', 1)
    elif value.startswith('postgresql://'):
        value = value.replace('postgresql://', 'postgresql+psycopg://', 1)
    return value

engine = create_engine(build_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
