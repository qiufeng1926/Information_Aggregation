from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.schemas import (
    ImportResult,
    InfluencerCreate,
    InfluencerFilter,
    InfluencerOut,
    InfluencerUpdate,
    PageResult,
    ResponseBase,
    TagBrief,
)
from app.services.influencer_service import InfluencerService

router = APIRouter(prefix="/influencers", tags=["达人管理"])


def _to_out(influencer) -> InfluencerOut:
    data = InfluencerOut.model_validate(influencer)
    data.tags = [
        TagBrief.model_validate(it.tag) for it in influencer.tags if it.tag is not None
    ]
    return data


@router.get("", response_model=ResponseBase[PageResult[InfluencerOut]])
def list_influencers(
    db: DbSession,
    _: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: str | None = None,
    source: str | None = None,
    keyword: str | None = None,
    follower_min: int | None = None,
    follower_max: int | None = None,
    status: int | None = 1,
):
    filters = InfluencerFilter(
        platform=platform,
        source=source,
        keyword=keyword,
        follower_min=follower_min,
        follower_max=follower_max,
        status=status,
    )
    items, total = InfluencerService.list_influencers(db, filters, page, page_size)
    return ResponseBase(
        data=PageResult(
            items=[_to_out(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{influencer_id}", response_model=ResponseBase[InfluencerOut])
def get_influencer(db: DbSession, _: CurrentUser, influencer_id: int):
    influencer = InfluencerService.get_by_id(db, influencer_id)
    if not influencer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="达人不存在")
    return ResponseBase(data=_to_out(influencer))


@router.post("", response_model=ResponseBase[InfluencerOut], status_code=status.HTTP_201_CREATED)
def create_influencer(db: DbSession, _: CurrentUser, data: InfluencerCreate):
    try:
        influencer = InfluencerService.create(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ResponseBase(data=_to_out(influencer))


@router.put("/{influencer_id}", response_model=ResponseBase[InfluencerOut])
def update_influencer(
    db: DbSession, _: CurrentUser, influencer_id: int, data: InfluencerUpdate
):
    influencer = InfluencerService.get_by_id(db, influencer_id)
    if not influencer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="达人不存在")
    influencer = InfluencerService.update(db, influencer, data)
    return ResponseBase(data=_to_out(influencer))


@router.delete("/{influencer_id}", response_model=ResponseBase[None])
def delete_influencer(db: DbSession, _: CurrentUser, influencer_id: int):
    influencer = InfluencerService.get_by_id(db, influencer_id)
    if not influencer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="达人不存在")
    InfluencerService.delete(db, influencer)
    return ResponseBase(message="删除成功")


@router.post("/import", response_model=ResponseBase[ImportResult])
async def import_influencers(
    db: DbSession,
    _: CurrentUser,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传 Excel 文件")

    content = await file.read()
    result = InfluencerService.import_from_excel(db, content)
    return ResponseBase(data=result)
