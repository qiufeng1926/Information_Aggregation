from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserLogin(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str | None
    role: str
    view_library: bool = False


class TagBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None


class InfluencerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contact_info: dict | None = None
    shooting_style: list | None = None
    persona_traits: list | None = None
    cooperation_policy: str | None = None
    internal_notes: str | None = None
    last_contact_date: datetime | None = None


class InfluencerBase(BaseModel):
    platform: str = Field(..., description="douyin/xiaohongshu/kuaishou/wechat")
    platform_uid: str
    nickname: str | None = None
    avatar_url: str | None = None
    profile_url: str | None = None
    agency_id: int | None = None
    follower_count: int = 0
    engagement_rate: float | None = None
    source: str | None = None
    extra_data: dict | None = None


class InfluencerCreate(InfluencerBase):
    pass


class InfluencerUpdate(BaseModel):
    nickname: str | None = None
    avatar_url: str | None = None
    profile_url: str | None = None
    agency_id: int | None = None
    follower_count: int | None = None
    engagement_rate: float | None = None
    source: str | None = None
    status: int | None = None
    extra_data: dict | None = None
    profile: InfluencerProfileOut | None = None


class InfluencerOut(InfluencerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: int
    created_at: datetime
    updated_at: datetime
    tags: list[TagBrief] = []
    profile: InfluencerProfileOut | None = None
    agency_name: str | None = None


class InfluencerFilter(BaseModel):
    platform: str | None = None
    source: str | None = None
    keyword: str | None = None
    follower_min: int | None = None
    follower_max: int | None = None
    tag_ids: list[int] | None = None
    agency_id: int | None = None
    status: int | None = 1


class ImportResult(BaseModel):
    total: int
    success: int
    failed: int
    errors: list[str] = []
