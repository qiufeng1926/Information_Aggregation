import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.collectors.registry import get_collector
from app.models import CollectedInfluencer, CollectionTask, Influencer
from app.schemas.collection import CollectionTaskCreate, ReviewResult
from app.schemas import InfluencerCreate, InfluencerUpdate
from app.services.agency_service import AgencyService
from app.services.influencer_service import InfluencerService
from app.services.tag_service import TagService
from app.utils.filter_summary import build_filter_summary

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
WORKER_SCRIPT = BACKEND_DIR / "scripts" / "run_collect_worker.py"

RETRIABLE_CATEGORIES = {"network", "timeout", "unknown"}
MAX_AUTO_RETRY = 1


def _detect_chromium() -> tuple[bool, str, str]:
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


def categorize_error(message: str) -> str:
    lower = message.lower()
    if any(k in message for k in ("未登录", "Cookie", "cookie", "登录态", "passport")):
        return "login_expired"
    if any(k in message for k in ("超时", "timeout")):
        return "timeout"
    if any(k in message for k in ("未采集到", "无结果", "无达人")):
        return "no_results"
    if any(k in lower for k in ("network", "connection", "连接", "refused")):
        return "network"
    return "unknown"


ERROR_CATEGORY_LABELS = {
    "login_expired": "登录失效",
    "timeout": "采集超时",
    "no_results": "无匹配结果",
    "network": "网络异常",
    "unknown": "未知错误",
}


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
        from app.services.collection_queue import enqueue_task

        enqueue_task(task_id)

    @staticmethod
    def _run_worker_subprocess(task_id: int) -> None:
        if not WORKER_SCRIPT.exists():
            message = f"采集 worker 脚本不存在: {WORKER_SCRIPT}"
            logger.error(message)
            CollectionService._mark_failed(task_id, message, categorize_error(message))
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
            if result.returncode == 0:
                return

            stderr = result.stderr.strip() or result.stdout.strip()
            error_msg = CollectionService._parse_worker_error(stderr) or f"采集 worker 异常退出 (code={result.returncode})"
            category = categorize_error(error_msg)
            logger.error("Collect worker failed (code=%s): %s", result.returncode, stderr)

            if CollectionService._should_auto_retry(task_id, category):
                CollectionService._schedule_retry(task_id, error_msg, category)
                return

            CollectionService._mark_failed(task_id, error_msg, category)
        except subprocess.TimeoutExpired:
            logger.error("Collect worker timeout for task %s", task_id)
            category = "timeout"
            if CollectionService._should_auto_retry(task_id, category):
                CollectionService._schedule_retry(task_id, "采集超时（超过10分钟）", category)
                return
            CollectionService._mark_failed(task_id, "采集超时（超过10分钟）", category)
        except Exception as exc:
            logger.exception("Collect worker subprocess error")
            msg = str(exc)
            CollectionService._mark_failed(task_id, msg, categorize_error(msg))

    @staticmethod
    def _should_auto_retry(task_id: int, category: str) -> bool:
        if category not in RETRIABLE_CATEGORIES:
            return False
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            task = db.query(CollectionTask).filter(CollectionTask.id == task_id).first()
            return bool(task and task.retry_count < MAX_AUTO_RETRY)
        finally:
            db.close()

    @staticmethod
    def _schedule_retry(task_id: int, last_error: str, category: str) -> None:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            task = db.query(CollectionTask).filter(CollectionTask.id == task_id).first()
            if not task:
                return
            task.retry_count += 1
            task.status = "pending"
            task.error_message = f"[自动重试 {task.retry_count}/{MAX_AUTO_RETRY}] {last_error}"
            task.error_category = category
            task.completed_at = None
            db.commit()
            logger.info("Auto retry task %s (attempt %s)", task_id, task.retry_count)
        finally:
            db.close()

        from app.services.collection_queue import enqueue_task

        enqueue_task(task_id)

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
    def _mark_failed(task_id: int, message: str, category: str | None = None) -> None:
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            task = db.query(CollectionTask).filter(CollectionTask.id == task_id).first()
            if task and task.status in ("pending", "running"):
                task.status = "failed"
                task.error_message = message
                task.error_category = category or categorize_error(message)
                task.completed_at = datetime.now()
                db.commit()
        finally:
            db.close()

    @staticmethod
    def list_tasks(
        db: Session,
        user_id: int,
        is_admin: bool,
        page: int,
        page_size: int,
    ) -> tuple[list[CollectionTask], int]:
        query = db.query(CollectionTask)
        if not is_admin:
            query = query.filter(CollectionTask.user_id == user_id)
        query = query.order_by(CollectionTask.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def get_task(
        db: Session,
        task_id: int,
        user_id: int | None = None,
        is_admin: bool = True,
    ) -> CollectionTask | None:
        query = db.query(CollectionTask).filter(CollectionTask.id == task_id)
        if not is_admin and user_id is not None:
            query = query.filter(CollectionTask.user_id == user_id)
        return query.first()

    @staticmethod
    def get_task_detail(
        db: Session,
        task_id: int,
        user_id: int,
        is_admin: bool,
    ) -> dict | None:
        task = CollectionService.get_task(db, task_id, user_id, is_admin)
        if not task:
            return None

        samples = (
            db.query(CollectedInfluencer)
            .filter(CollectedInfluencer.task_id == task_id)
            .order_by(CollectedInfluencer.match_score.desc())
            .limit(5)
            .all()
        )

        duration = None
        if task.started_at and task.completed_at:
            duration = int((task.completed_at - task.started_at).total_seconds())

        from app.services.collection_queue import queue_size, running_task_id

        queue_position = None
        if task.status == "pending":
            ahead = (
                db.query(CollectionTask)
                .filter(
                    CollectionTask.status == "pending",
                    CollectionTask.id < task.id,
                )
                .count()
            )
            queue_position = ahead + (1 if running_task_id() else 0) + 1

        library_uids = CollectionService._library_uid_map(db, samples)

        return {
            "task": task,
            "filter_summary": build_filter_summary(task.filters),
            "duration_seconds": duration,
            "sample_items": samples,
            "queue_size": queue_size(),
            "queue_position": queue_position,
            "running_task_id": running_task_id(),
            "library_uids": library_uids,
        }

    @staticmethod
    def _library_uid_map(db: Session, items: list[CollectedInfluencer]) -> dict[str, int]:
        if not items:
            return {}
        pairs = {(i.platform, i.platform_uid) for i in items}
        result: dict[str, int] = {}
        for platform, uid in pairs:
            row = (
                db.query(Influencer.id)
                .filter(Influencer.platform == platform, Influencer.platform_uid == uid)
                .first()
            )
            if row:
                result[f"{platform}:{uid}"] = row[0]
        return result

    @staticmethod
    def _collected_query_for_user(
        db: Session,
        user_id: int,
        is_admin: bool,
    ):
        query = db.query(CollectedInfluencer)
        if not is_admin:
            query = query.join(CollectionTask).filter(CollectionTask.user_id == user_id)
        return query

    @staticmethod
    def list_pending(
        db: Session,
        user_id: int,
        is_admin: bool,
        task_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CollectedInfluencer], int, dict[str, int]]:
        query = CollectionService._collected_query_for_user(db, user_id, is_admin).filter(
            CollectedInfluencer.review_status == "pending"
        )
        if task_id:
            if not is_admin:
                task = CollectionService.get_task(db, task_id, user_id, is_admin=False)
                if not task:
                    return [], 0, {}
            query = query.filter(CollectedInfluencer.task_id == task_id)
        query = query.order_by(CollectedInfluencer.match_score.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        library_map = CollectionService._library_uid_map(db, items)
        return items, total, library_map

    @staticmethod
    def list_reviewed(
        db: Session,
        user_id: int,
        is_admin: bool,
        review_status: str,
        task_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CollectedInfluencer], int]:
        query = CollectionService._collected_query_for_user(db, user_id, is_admin).filter(
            CollectedInfluencer.review_status == review_status
        )
        if task_id:
            if not is_admin:
                task = CollectionService.get_task(db, task_id, user_id, is_admin=False)
                if not task:
                    return [], 0
            query = query.filter(CollectedInfluencer.task_id == task_id)
        query = query.order_by(CollectedInfluencer.reviewed_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def approve_items(
        db: Session,
        ids: list[int],
        user_id: int,
        is_admin: bool,
    ) -> ReviewResult:
        result = ReviewResult()
        query = (
            db.query(CollectedInfluencer)
            .filter(
                CollectedInfluencer.id.in_(ids),
                CollectedInfluencer.review_status == "pending",
            )
        )
        if not is_admin:
            query = query.join(CollectionTask).filter(CollectionTask.user_id == user_id)
        items = query.all()

        task_ids: set[int] = set()
        for item in items:
            agency_id = AgencyService.resolve_agency_id(db, item.platform, item.extra_data)
            existing = InfluencerService.get_by_platform_uid(db, item.platform, item.platform_uid)
            if existing:
                update_data = InfluencerUpdate(
                    nickname=item.nickname,
                    avatar_url=item.avatar_url,
                    profile_url=item.profile_url,
                    follower_count=item.follower_count,
                    engagement_rate=float(item.engagement_rate) if item.engagement_rate else None,
                    source=item.source,
                    extra_data=item.extra_data,
                )
                if agency_id is not None:
                    update_data.agency_id = agency_id
                InfluencerService.update(db, existing, update_data)
                influencer_id = existing.id
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
                        agency_id=agency_id,
                    ),
                )
                influencer_id = influencer.id

            if item.matched_tags:
                TagService.attach_tags(db, influencer_id, item.matched_tags, source="collect")

            item.influencer_id = influencer_id
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
    def reject_items(
        db: Session,
        ids: list[int],
        user_id: int,
        is_admin: bool,
    ) -> ReviewResult:
        result = ReviewResult()
        query = (
            db.query(CollectedInfluencer)
            .filter(
                CollectedInfluencer.id.in_(ids),
                CollectedInfluencer.review_status == "pending",
            )
        )
        if not is_admin:
            query = query.join(CollectionTask).filter(CollectionTask.user_id == user_id)
        items = query.all()
        for item in items:
            item.review_status = "rejected"
            item.reviewed_by = user_id
            item.reviewed_at = datetime.now()
            result.rejected += 1

        result.skipped = len(ids) - len(items)
        db.commit()
        return result

    @staticmethod
    def get_stats(db: Session, user_id: int, is_admin: bool) -> dict:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        pending_query = CollectionService._collected_query_for_user(db, user_id, is_admin).filter(
            CollectedInfluencer.review_status == "pending"
        )
        pending_review = pending_query.count()

        def owned_tasks():
            q = db.query(CollectionTask)
            if not is_admin:
                q = q.filter(CollectionTask.user_id == user_id)
            return q

        today_tasks = owned_tasks().filter(CollectionTask.created_at >= today_start).count()
        today_collected = (
            owned_tasks()
            .filter(
                CollectionTask.created_at >= today_start,
                CollectionTask.status == "completed",
            )
            .with_entities(func.coalesce(func.sum(CollectionTask.result_count), 0))
            .scalar()
        )
        completed = owned_tasks().filter(CollectionTask.status == "completed").count()
        failed = owned_tasks().filter(CollectionTask.status == "failed").count()
        finished = completed + failed
        success_rate = round(completed / finished * 100, 1) if finished else 100.0

        running = owned_tasks().filter(CollectionTask.status == "running").first()
        queued = owned_tasks().filter(CollectionTask.status == "pending").count()

        from app.services.collection_queue import queue_size, running_task_id

        return {
            "pending_review": pending_review,
            "today_tasks": today_tasks,
            "today_collected": int(today_collected or 0),
            "success_rate": success_rate,
            "running_task_id": running.id if running else running_task_id(),
            "queued_tasks": queued,
            "queue_size": queue_size(),
        }

    @staticmethod
    def check_environment() -> dict:
        import importlib.util
        import json
        from datetime import datetime as dt

        playwright_ok = importlib.util.find_spec("playwright") is not None
        chromium_ok, chromium_path, chromium_error = _detect_chromium()

        if not playwright_ok:
            chromium_error = (
                "当前后端 Python 环境中未安装 playwright。"
                "请在运行 uvicorn 的同一环境中执行: pip install playwright"
            )

        from app.config import settings

        storage_path = Path(settings.XINGTU_STORAGE_STATE) if settings.XINGTU_STORAGE_STATE else None
        storage_ok = bool(storage_path and storage_path.exists())
        storage_updated_at = None
        storage_age_days = None

        if storage_ok and storage_path:
            mtime = storage_path.stat().st_mtime
            storage_updated_at = dt.fromtimestamp(mtime).isoformat(timespec="seconds")
            storage_age_days = (dt.now() - dt.fromtimestamp(mtime)).days

            try:
                with open(storage_path, encoding="utf-8") as f:
                    state = json.load(f)
                cookie_count = len(state.get("cookies", []))
            except Exception:
                cookie_count = 0
        else:
            cookie_count = 0

        ready = playwright_ok and chromium_ok and storage_ok
        login_warning = ""
        if storage_ok and storage_age_days is not None and storage_age_days >= 7:
            login_warning = f"登录态已 {storage_age_days} 天未更新，建议重新运行 save_xingtu_session.py"

        hint = CollectionService._build_env_hint(
            playwright_ok, chromium_ok, storage_ok, chromium_error
        )
        if login_warning:
            hint = f"{hint}；{login_warning}" if hint else login_warning

        return {
            "python": sys.executable,
            "playwright_installed": playwright_ok,
            "chromium_ready": chromium_ok,
            "chromium_path": chromium_path,
            "chromium_error": chromium_error,
            "storage_configured": storage_ok,
            "storage_updated_at": storage_updated_at,
            "storage_age_days": storage_age_days,
            "cookie_count": cookie_count,
            "login_warning": login_warning,
            "mode": settings.COLLECTOR_MODE,
            "ready": ready,
            "hint": hint,
            "save_session_command": "python scripts/save_xingtu_session.py",
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
