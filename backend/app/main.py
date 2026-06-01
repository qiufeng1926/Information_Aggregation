from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1 import auth, agencies, collection, influencers, match, tags
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.middleware.request_log import RequestLogMiddleware
from app.models import User
from app.utils.security import get_password_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def log_collect_env():
    from app.services.collection_service import CollectionService

    print("\n" + "=" * 60)
    print("采集环境检测")
    for platform, label in (("douyin", "抖音/星图"), ("xiaohongshu", "小红书/蒲公英")):
        env = CollectionService.check_environment(platform)
        print(f"  [{label}]")
        print(f"    Python     : {env['python']}")
        print(f"    Playwright : {'已安装' if env['playwright_installed'] else '未安装'}")
        print(f"    Chromium   : {'已就绪' if env['chromium_ready'] else '未就绪'}")
        print(f"    登录态     : {'已配置' if env['storage_configured'] else '未配置'}")
        if env.get("hint"):
            print(f"    提示       : {env['hint']}")
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
        has_users = db.query(User).count() > 0
        if not has_users:
            username = settings.ADMIN_USERNAME.strip()
            password = settings.ADMIN_PASSWORD
            if username and password:
                if len(password) < 8:
                    raise RuntimeError("ADMIN_PASSWORD 长度至少 8 位")
                admin = User(
                    username=username,
                    password_hash=get_password_hash(password),
                    nickname="管理员",
                    role="admin",
                )
                db.add(admin)
                db.commit()
                print(f"已创建管理员账号: {username}")
            else:
                print("\n" + "!" * 60)
                print("警告: 系统中尚无用户，且未配置 ADMIN_USERNAME / ADMIN_PASSWORD")
                print("请在 backend/.env 中设置后重启，或通过数据库手动创建用户")
                print("!" * 60 + "\n")
    finally:
        db.close()

    db = SessionLocal()
    try:
        from app.services.tag_service import TagService

        seeded = TagService.seed_defaults(db)
        if seeded:
            print(f"已初始化 {seeded} 个预置标签")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log_collect_env()
    if settings.DEBUG:
        print(f"CORS origins : {settings.CORS_ORIGINS}")
        if settings.CORS_ORIGIN_REGEX:
            print(f"CORS regex   : {settings.CORS_ORIGIN_REGEX}")
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(RequestLogMiddleware)

_cors_kwargs: dict = {
    "allow_origins": settings.CORS_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "expose_headers": ["Content-Disposition"],
}
if settings.CORS_ORIGIN_REGEX:
    _cors_kwargs["allow_origin_regex"] = settings.CORS_ORIGIN_REGEX

app.add_middleware(CORSMiddleware, **_cors_kwargs)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(influencers.router, prefix="/api/v1")
app.include_router(collection.router, prefix="/api/v1")
app.include_router(tags.router, prefix="/api/v1")
app.include_router(agencies.router, prefix="/api/v1")
app.include_router(match.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
