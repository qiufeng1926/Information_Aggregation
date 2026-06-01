from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1 import auth, collection, influencers
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.middleware.request_log import RequestLogMiddleware
from app.models import User
from app.utils.security import get_password_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def log_collect_env():
    from app.services.collection_service import CollectionService

    env = CollectionService.check_environment()
    print("\n" + "=" * 60)
    print("采集环境检测")
    print(f"  Python     : {env['python']}")
    print(f"  Playwright : {'已安装' if env['playwright_installed'] else '未安装'}")
    print(f"  Chromium   : {'已就绪' if env['chromium_ready'] else '未就绪'}")
    print(f"  星图登录态 : {'已配置' if env['storage_configured'] else '未配置'}")
    if env.get("hint"):
        print(f"  提示       : {env['hint']}")
    print("=" * 60 + "\n")


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print("\n" + "=" * 60)
        print("数据库连接失败，请先初始化 MySQL：")
        print("  powershell -ExecutionPolicy Bypass -File scripts\\setup_local.ps1")
        print("或在 backend\\.env 中修改 DATABASE_URL 为你的 MySQL 账号")
        print("=" * 60 + "\n")
        raise exc
    db: Session = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                nickname="管理员",
                role="admin",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log_collect_env()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(influencers.router, prefix="/api/v1")
app.include_router(collection.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
