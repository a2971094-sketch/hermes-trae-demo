"""Hermes × Trae 示范项目 — FastAPI 应用入口"""

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import router as auth_router, users_router

# 创建所有表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hermes × Trae Demo",
    description="Hermes 主控规划任务 → Trae 云端编码实现 → Hermes 审查合并",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(users_router)


@app.get("/")
def root():
    return {"message": "Hermes 主控 × Trae 云端被控", "status": "running"}
