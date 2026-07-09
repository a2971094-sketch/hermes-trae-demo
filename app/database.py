"""数据库配置 — 内存 SQLite（使用 StaticPool 确保多线程共享同一数据库）"""

from sqlalchemy import create_engine, pool
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=pool.StaticPool,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
