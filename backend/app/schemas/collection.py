from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CollectionFilters(BaseModel):
    follower_min: int | None = None
    follower_max: int | None = None
    avg_views_min: int | None = None
    limit: int = Field(default=50, ge=1, le=200)


class CollectionTaskCreate(BaseModel):
    platform: str = Field(..., description="douyin/xiaohongshu/kuaishou")
    keyword: str = Field(..., min_length=1, max_length=200)
    title: str | None = None
    filters: CollectionFilters | None = None


class CollectionTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str | None
    platform: str
    keyword: str
    filters: dict | None
    status: str
    result_count: int
    approved_count: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CollectedInfluencerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    platform: str
    platform_uid: str
    nickname: str | None
    avatar_url: str | None
    profile_url: str | None
    follower_count: int
    engagement_rate: float | None
    avg_views: int | None
    source: str | None
    matched_tags: list | None
    match_score: float | None
    extra_data: dict | None
    review_status: str
    influencer_id: int | None
    created_at: datetime


class ReviewAction(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class ReviewResult(BaseModel):
    approved: int = 0
    rejected: int = 0
    skipped: int = 0
