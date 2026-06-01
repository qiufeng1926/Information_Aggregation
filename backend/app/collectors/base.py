from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchFilters:
    follower_min: int | None = None
    follower_max: int | None = None
    avg_views_min: int | None = None
    limit: int = 50


@dataclass
class RawInfluencer:
    platform: str
    platform_uid: str
    nickname: str
    avatar_url: str | None = None
    profile_url: str | None = None
    follower_count: int = 0
    engagement_rate: float | None = None
    avg_views: int | None = None
    source: str = "auto_collect"
    matched_tags: list[str] = field(default_factory=list)
    match_score: float = 0.0
    extra_data: dict[str, Any] = field(default_factory=dict)


class BaseCollector(ABC):
    platform: str

    @abstractmethod
    def search(self, keyword: str, filters: SearchFilters) -> list[RawInfluencer]:
        pass