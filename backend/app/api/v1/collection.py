from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import PageResult, ResponseBase
from app.schemas.collection import (
    CollectionTaskCreate,
    CollectionTaskDetailOut,
    CollectionTaskOut,
    CollectedInfluencerOut,
    ReviewAction,
    ReviewResult,
)
from app.services.collection_service import CollectionService, ERROR_CATEGORY_LABELS
from app.utils.access_control import is_admin
from app.utils.filter_summary import build_filter_summary
from app.utils.mcn_utils import extract_mcn_name

router = APIRouter(prefix="/collection", tags=["自动采集"])


def _task_out(task) -> CollectionTaskOut:
    data = CollectionTaskOut.model_validate(task)
    data.filter_summary = build_filter_summary(task.filters)
    return data


def _collected_out(item, library_map: dict[str, int] | None = None) -> CollectedInfluencerOut:
    data = CollectedInfluencerOut.model_validate(item)
    key = f"{item.platform}:{item.platform_uid}"
    if library_map and key in library_map:
        data.in_library = True
        data.existing_influencer_id = library_map[key]
    elif item.extra_data:
        data.in_library = bool(item.extra_data.get("in_library"))
        data.existing_influencer_id = item.extra_data.get("existing_influencer_id")
    data.mcn_name = extract_mcn_name(item.extra_data)
    return data


@router.get("/config", response_model=ResponseBase[dict])
def get_collection_config(_: CurrentUser):
    return ResponseBase(data=CollectionService.check_environment())


@router.get("/stats", response_model=ResponseBase[dict])
def get_collection_stats(db: DbSession, user: CurrentUser):
    return ResponseBase(data=CollectionService.get_stats(db, user.id, is_admin(user)))


@router.get("/filter-options", response_model=ResponseBase[dict])
def get_filter_options(_: CurrentUser):
    from app.constants.xingtu_filters import get_filter_options

    return ResponseBase(data=get_filter_options())


@router.post("/tasks", response_model=ResponseBase[CollectionTaskOut], status_code=status.HTTP_201_CREATED)
def create_collection_task(db: DbSession, user: CurrentUser, data: CollectionTaskCreate):
    try:
        task = CollectionService.create_task(db, user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    CollectionService.run_task_async(task.id)
    return ResponseBase(data=_task_out(task), message="采集任务已创建，已加入队列")


@router.get("/tasks", response_model=ResponseBase[PageResult[CollectionTaskOut]])
def list_collection_tasks(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = CollectionService.list_tasks(db, user.id, is_admin(user), page, page_size)
    return ResponseBase(
        data=PageResult(
            items=[_task_out(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/tasks/{task_id}", response_model=ResponseBase[CollectionTaskOut])
def get_collection_task(db: DbSession, user: CurrentUser, task_id: int):
    task = CollectionService.get_task(db, task_id, user.id, is_admin(user))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return ResponseBase(data=_task_out(task))


@router.get("/tasks/{task_id}/detail", response_model=ResponseBase[CollectionTaskDetailOut])
def get_collection_task_detail(db: DbSession, user: CurrentUser, task_id: int):
    detail = CollectionService.get_task_detail(db, task_id, user.id, is_admin(user))
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    task = detail["task"]
    out = CollectionTaskDetailOut.model_validate(task)
    out.filter_summary = detail["filter_summary"]
    out.duration_seconds = detail["duration_seconds"]
    out.queue_size = detail["queue_size"]
    out.queue_position = detail["queue_position"]
    out.running_task_id = detail["running_task_id"]
    out.sample_items = [
        _collected_out(i, detail["library_uids"]) for i in detail["sample_items"]
    ]
    if out.error_category:
        label = ERROR_CATEGORY_LABELS.get(out.error_category, out.error_category)
        if out.error_message and label not in out.error_message:
            out.error_message = f"[{label}] {out.error_message}"
    return ResponseBase(data=out)


@router.post("/tasks/{task_id}/retry", response_model=ResponseBase[CollectionTaskOut])
def retry_collection_task(db: DbSession, user: CurrentUser, task_id: int):
    task = CollectionService.get_task(db, task_id, user.id, is_admin(user))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status == "running":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务正在执行中")

    task.status = "pending"
    task.error_message = None
    task.error_category = None
    db.commit()
    CollectionService.run_task_async(task.id)
    return ResponseBase(data=_task_out(task), message="任务已重新加入队列")


@router.get("/pending", response_model=ResponseBase[PageResult[CollectedInfluencerOut]])
def list_pending_review(
    db: DbSession,
    user: CurrentUser,
    task_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total, library_map = CollectionService.list_pending(
        db, user.id, is_admin(user), task_id, page, page_size
    )
    return ResponseBase(
        data=PageResult(
            items=[_collected_out(i, library_map) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/reviewed", response_model=ResponseBase[PageResult[CollectedInfluencerOut]])
def list_reviewed(
    db: DbSession,
    user: CurrentUser,
    review_status: str = Query("approved", pattern="^(approved|rejected)$"),
    task_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = CollectionService.list_reviewed(
        db, user.id, is_admin(user), review_status, task_id, page, page_size
    )
    return ResponseBase(
        data=PageResult(
            items=[_collected_out(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/approve", response_model=ResponseBase[ReviewResult])
def approve_collected(db: DbSession, user: CurrentUser, data: ReviewAction):
    result = CollectionService.approve_items(db, data.ids, user.id, is_admin(user))
    return ResponseBase(data=result, message=f"已通过 {result.approved} 条")


@router.post("/reject", response_model=ResponseBase[ReviewResult])
def reject_collected(db: DbSession, user: CurrentUser, data: ReviewAction):
    result = CollectionService.reject_items(db, data.ids, user.id, is_admin(user))
    return ResponseBase(data=result, message=f"已拒绝 {result.rejected} 条")
