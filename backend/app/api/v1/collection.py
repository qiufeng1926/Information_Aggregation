from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import PageResult, ResponseBase
from app.schemas.collection import (
    CollectionTaskCreate,
    CollectionTaskOut,
    CollectedInfluencerOut,
    ReviewAction,
    ReviewResult,
)
from app.services.collection_service import CollectionService

router = APIRouter(prefix="/collection", tags=["自动采集"])


@router.get("/config", response_model=ResponseBase[dict])
def get_collection_config(_: CurrentUser):
    return ResponseBase(data=CollectionService.check_environment())


@router.post("/tasks", response_model=ResponseBase[CollectionTaskOut], status_code=status.HTTP_201_CREATED)
def create_collection_task(db: DbSession, user: CurrentUser, data: CollectionTaskCreate):
    try:
        task = CollectionService.create_task(db, user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    CollectionService.run_task_async(task.id)
    return ResponseBase(data=CollectionTaskOut.model_validate(task), message="采集任务已创建，正在后台执行")


@router.get("/tasks", response_model=ResponseBase[PageResult[CollectionTaskOut]])
def list_collection_tasks(
    db: DbSession,
    _: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = CollectionService.list_tasks(db, page, page_size)
    return ResponseBase(
        data=PageResult(
            items=[CollectionTaskOut.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/tasks/{task_id}", response_model=ResponseBase[CollectionTaskOut])
def get_collection_task(db: DbSession, _: CurrentUser, task_id: int):
    task = CollectionService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return ResponseBase(data=CollectionTaskOut.model_validate(task))


@router.post("/tasks/{task_id}/retry", response_model=ResponseBase[CollectionTaskOut])
def retry_collection_task(db: DbSession, _: CurrentUser, task_id: int):
    task = CollectionService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status == "running":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务正在执行中")

    task.status = "pending"
    task.error_message = None
    db.commit()
    CollectionService.run_task_async(task.id)
    return ResponseBase(data=CollectionTaskOut.model_validate(task), message="任务已重新启动")


@router.get("/pending", response_model=ResponseBase[PageResult[CollectedInfluencerOut]])
def list_pending_review(
    db: DbSession,
    _: CurrentUser,
    task_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items, total = CollectionService.list_pending(db, task_id, page, page_size)
    return ResponseBase(
        data=PageResult(
            items=[CollectedInfluencerOut.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/approve", response_model=ResponseBase[ReviewResult])
def approve_collected(db: DbSession, user: CurrentUser, data: ReviewAction):
    result = CollectionService.approve_items(db, data.ids, user.id)
    return ResponseBase(data=result, message=f"已通过 {result.approved} 条")


@router.post("/reject", response_model=ResponseBase[ReviewResult])
def reject_collected(db: DbSession, user: CurrentUser, data: ReviewAction):
    result = CollectionService.reject_items(db, data.ids, user.id)
    return ResponseBase(data=result, message=f"已拒绝 {result.rejected} 条")
