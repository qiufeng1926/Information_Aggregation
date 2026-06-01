from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CollectionFilters(BaseModel):
    """星图采集筛选条件，各字段默认空/None 表示「不限」"""

    # 合作诉求
    cooperation_purpose: str | None = None
    incentive_method: str | None = None
    cooperation_form: str | None = None
    creator_level: str | None = None

    # 达人配置
    creator_type: str | None = None
    follower_tier: str | None = None
    content_theme: str | None = None
    creator_gender: str | None = None
    follower_gender: str | None = None
    follower_age: str | None = None
    verified: str | None = None

    # 数据指标
    follower_min: int | None = None
    follower_max: int | None = None
    avg_views_min: int | None = None
    interaction_rate_min: float | None = None

    # 性价比
    quote_duration: str | None = None
    quote_min: int | None = None
    quote_max: int | None = None
    expected_play_min: int | None = None
    expected_cpm_max: float | None = None
    expected_cpe_max: float | None = None
    completion_rate_min: float | None = None

    # 主题推荐（多选）
    theme_tags: list[str] | None = None

    # 采集数量
    limit: int = Field(default=30, ge=1, le=200)


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
