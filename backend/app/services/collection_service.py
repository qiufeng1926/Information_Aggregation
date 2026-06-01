import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.collectors.registry import get_collector
from app.models import CollectedInfluencer, CollectionTask
from app.schemas.collection import CollectionTaskCreate, ReviewResult
from app.schemas import InfluencerCreate, InfluencerUpdate
from app.services.influencer_service import InfluencerService

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
WORKER_SCRIPT = BACKEND_DIR / "scripts" / "run_collect_worker.py"


def _detect_chromium() -> tuple[bool, str, str]:
    """检测 Chromium 是否已下载，不启动浏览器（避免误判和卡顿）"""
    import os

    search_roots: list[Path] = []
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_path:
        search_roots.append(Path(browsers_path))
    search_roots.append(Path.home() / "AppData" / "Local" / "ms-playwright")

    for root in search_roots:
        if not root.exists():
            continue
        for folder in sorted(root.glob("chromium-*"), reverse=True):
            for rel in ("chrome-win64/chrome.exe", "chrome-linux/chrome", "chrome-mac/Chromium.app"):
                exe = folder / rel.replace("/", os.sep)
                if exe.exists():
                    return True, str(exe), ""

    return False, "", "Chromium 未下载，请运行: playwright install chromium"


class CollectionService:
    @staticmethod
    def create_task(db: Session, user_id: int, data: CollectionTaskCreate) -> CollectionTask:
        get_collector(data.platform)
        filters = data.filters.model_dump(exclude_none=True) if data.filters else {}
        task = CollectionTask(
            user_id=user_id,
            title=data.title or f"{data.platform}-{data.keyword}",
            platform=data.platform,
            keyword=data.keyword,
            filters=filters,
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def run_task_async(task_id: int) -> None:
        """在独立子进程中运行 Playwright，避免 Windows 线程/环境问题"""
        import threading

        thread = threading.Thread(
            target=CollectionService._run_worker_subprocess,
            args=(task_id,),
            daemon=True,
        )
        thread.start()

    @staticmethod
    def _run_worker_subprocess(task_id: int) -> None:
        if not WORKER_SCRIPT.exists():
            message = f"采集 worker 脚本不存在: {WORKER_SCRIPT}"
            logger.error(message)
            CollectionService._mark_failed(task_id, message)
            return

        python = sys.executable
        cmd = [python, str(WORKER_SCRIPT), str(task_id)]
        logger.info("Starting collect worker: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                cwd=str(BACKEND_DIR),
            )
            if result.returncode != 0:
                stderr = result.stderr.strip() or result.stdout.strip()
                logger.error("Collect worker failed (code=%s): %s", result.returncode, stderr)
                CollectionService._mark_failed(
                    task_id,
                    CollectionService._parse_worker_error(stderr) or f"采集 worker 异常退出 (code={result.returncode})",
                )
        except subprocess.TimeoutExpired:
            logger.error("Collect worker timeout for task %s", task_id)
            CollectionService._mark_failed(task_id, "采集超时（超过10分钟）")
        except Exception as exc:
            logger.exception("Collect worker subprocess error")
            CollectionService._mark_failed(task_id, str(exc))

    @staticmethod
    def _parse_worker_error(output: str) -> str:
        import json

        for line in reversed(output.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("error"):
                return str(payload["error"])
        return output[:500] if output else ""

    @staticmethod
    def _mark_failed(task_id: int, message: str) -> None:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            task = db.query(CollectionTask).filter(CollectionTask.id == task_id).first()
            if task and task.status in ("pending", "running"):
                task.status = "failed"
                task.error_message = message
                task.completed_at = datetime.now()
                db.commit()
        finally:
            db.close()

    @staticmethod
    def list_tasks(db: Session, page: int, page_size: int) -> tuple[list[CollectionTask], int]:
        query = db.query(CollectionTask).order_by(CollectionTask.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def get_task(db: Session, task_id: int) -> CollectionTask | None:
        return db.query(CollectionTask).filter(CollectionTask.id == task_id).first()

    @staticmethod
    def list_pending(
        db: Session,
        task_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CollectedInfluencer], int]:
        query = db.query(CollectedInfluencer).filter(CollectedInfluencer.review_status == "pending")
        if task_id:
            query = query.filter(CollectedInfluencer.task_id == task_id)
        query = query.order_by(CollectedInfluencer.match_score.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def approve_items(db: Session, ids: list[int], user_id: int) -> ReviewResult:
        result = ReviewResult()
        items = (
            db.query(CollectedInfluencer)
            .filter(CollectedInfluencer.id.in_(ids), CollectedInfluencer.review_status == "pending")
            .all()
        )

        task_ids: set[int] = set()
        for item in items:
            existing = InfluencerService.get_by_platform_uid(db, item.platform, item.platform_uid)
            if existing:
                InfluencerService.update(
                    db,
                    existing,
                    InfluencerUpdate(
                        nickname=item.nickname,
                        avatar_url=item.avatar_url,
                        profile_url=item.profile_url,
                        follower_count=item.follower_count,
                        engagement_rate=float(item.engagement_rate) if item.engagement_rate else None,
                        source=item.source,
                        extra_data=item.extra_data,
                    ),
                )
                item.influencer_id = existing.id
            else:
                influencer = InfluencerService.create(
                    db,
                    InfluencerCreate(
                        platform=item.platform,
                        platform_uid=item.platform_uid,
                        nickname=item.nickname,
                        avatar_url=item.avatar_url,
                        profile_url=item.profile_url,
                        follower_count=item.follower_count,
                        engagement_rate=float(item.engagement_rate) if item.engagement_rate else None,
                        source=item.source,
                        extra_data=item.extra_data,
                    ),
                )
                item.influencer_id = influencer.id

            item.review_status = "approved"
            item.reviewed_by = user_id
            item.reviewed_at = datetime.now()
            task_ids.add(item.task_id)
            result.approved += 1

        result.skipped = len(ids) - len(items)

        for tid in task_ids:
            task = db.query(CollectionTask).filter(CollectionTask.id == tid).first()
            if task:
                task.approved_count = (
                    db.query(CollectedInfluencer)
                    .filter(
                        CollectedInfluencer.task_id == tid,
                        CollectedInfluencer.review_status == "approved",
                    )
                    .count()
                )

        db.commit()
        return result

    @staticmethod
    def reject_items(db: Session, ids: list[int], user_id: int) -> ReviewResult:
        result = ReviewResult()
        items = (
            db.query(CollectedInfluencer)
            .filter(CollectedInfluencer.id.in_(ids), CollectedInfluencer.review_status == "pending")
            .all()
        )
        for item in items:
            item.review_status = "rejected"
            item.reviewed_by = user_id
            item.reviewed_at = datetime.now()
            result.rejected += 1

        result.skipped = len(ids) - len(items)
        db.commit()
        return result

    @staticmethod
    def check_environment() -> dict:
        import importlib.util

        playwright_ok = importlib.util.find_spec("playwright") is not None
        chromium_ok, chromium_path, chromium_error = _detect_chromium()

        if not playwright_ok:
            chromium_error = (
                "当前后端 Python 环境中未安装 playwright。"
                "请在运行 uvicorn 的同一环境中执行: pip install playwright"
            )

        from app.config import settings

        storage_ok = bool(
            settings.XINGTU_STORAGE_STATE and Path(settings.XINGTU_STORAGE_STATE).exists()
        )

        ready = playwright_ok and chromium_ok and storage_ok

        return {
            "python": sys.executable,
            "playwright_installed": playwright_ok,
            "chromium_ready": chromium_ok,
            "chromium_path": chromium_path,
            "chromium_error": chromium_error,
            "storage_configured": storage_ok,
            "mode": settings.COLLECTOR_MODE,
            "ready": ready,
            "hint": CollectionService._build_env_hint(
                playwright_ok, chromium_ok, storage_ok, chromium_error
            ),
        }

    @staticmethod
    def _build_env_hint(
        playwright_ok: bool, chromium_ok: bool, storage_ok: bool, chromium_error: str
    ) -> str:
        if playwright_ok and chromium_ok and storage_ok:
            return ""
        parts: list[str] = []
        if not playwright_ok:
            parts.append("Playwright 未安装（需重启后端）")
        elif not chromium_ok:
            parts.append(chromium_error or "Chromium 未就绪")
        if not storage_ok:
            parts.append("星图登录态未配置，请运行 python scripts/save_xingtu_session.py")
        if not playwright_ok:
            parts.append(f"当前后端 Python: {sys.executable}")
        return "；".join(parts)
