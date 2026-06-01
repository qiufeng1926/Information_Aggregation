"""星图 Playwright 自动化采集器"""

import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.collectors.base import RawInfluencer, SearchFilters
from app.config import settings

logger = logging.getLogger(__name__)

XINGTU_MARKET_URL = "https://www.xingtu.cn/ad/creator/market"
XINGTU_SEARCH_URL = "https://www.xingtu.cn/ad/creator/market?keyword={keyword}"

AUTHOR_ID_KEYS = ("author_id", "star_id", "uid", "user_id", "core_user_id", "id")
NICKNAME_KEYS = ("nick_name", "nickname", "author_name", "name", "unique_id")
FOLLOWER_KEYS = ("follower_count", "follower", "fans_num", "fans_count", "follower_num")
AVATAR_KEYS = ("avatar_uri", "avatar_url", "avatar", "head_image")
TAG_KEYS = ("tags", "tag_list", "content_tags", "category_tags")
AVG_PLAY_KEYS = ("avg_play", "avg_play_count", "play_count_avg", "average_play")

INTERCEPT_URL_KEYWORDS = (
    "author",
    "creator",
    "search",
    "market",
    "star",
    "kol",
    "talent",
)


class XingtuBrowserCollector:
    """通过 Playwright 自动化操作星图达人广场，拦截 API 响应获取达人数据"""

    def search(self, keyword: str, filters: SearchFilters) -> list[RawInfluencer]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("请先安装 Playwright: pip install playwright && playwright install chromium") from exc

        captured: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        def on_response(response) -> None:
            if response.status != 200:
                return
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                return
            url = response.url.lower()
            if "xingtu.cn" not in url:
                return
            if not any(k in url for k in INTERCEPT_URL_KEYWORDS):
                return
            try:
                data = response.json()
                for item in _extract_author_items(data):
                    uid = _pick(item, AUTHOR_ID_KEYS)
                    if uid and uid not in seen_ids:
                        seen_ids.add(uid)
                        captured.append(item)
            except Exception:
                pass

        logger.info("Xingtu Playwright collect start: keyword=%s", keyword)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=settings.PLAYWRIGHT_HEADLESS,
                slow_mo=settings.PLAYWRIGHT_SLOW_MO,
            )
            context = self._create_context(browser)
            page = context.new_page()
            page.on("response", on_response)

            try:
                page.goto(XINGTU_MARKET_URL, wait_until="domcontentloaded", timeout=settings.PLAYWRIGHT_TIMEOUT)
                page.wait_for_timeout(2000)

                if not self._is_logged_in(page):
                    raise RuntimeError(
                        "星图未登录或 Cookie 已过期。请运行: python scripts/save_xingtu_session.py"
                    )

                self._perform_search(page, keyword)
                page.wait_for_timeout(settings.PLAYWRIGHT_WAIT_AFTER_SEARCH)

                # 滚动加载更多
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    page.wait_for_timeout(1500)

                # DOM 兜底解析
                if len(captured) < filters.limit:
                    dom_items = self._parse_dom(page)
                    for item in dom_items:
                        uid = item.get("platform_uid", "")
                        if uid and uid not in seen_ids:
                            seen_ids.add(uid)
                            captured.append(item)

            finally:
                context.close()
                browser.close()

        results = self._to_raw_influencers(keyword, captured, filters)
        logger.info("Xingtu Playwright collect done: keyword=%s, count=%d", keyword, len(results))

        if not results:
            raise RuntimeError(f"星图未采集到达人，请检查关键词「{keyword}」或 Cookie 是否有效")

        return results[: filters.limit]

    def _create_context(self, browser):
        kwargs: dict[str, Any] = {
            "viewport": {"width": 1440, "height": 900},
            "user_agent": settings.PLAYWRIGHT_USER_AGENT,
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
        }

        storage_path = Path(settings.XINGTU_STORAGE_STATE)
        if storage_path.exists():
            logger.info("Loading Xingtu storage state: %s", storage_path)
            context = browser.new_context(storage_state=str(storage_path), **kwargs)
        else:
            context = browser.new_context(**kwargs)
            cookies = _load_cookies()
            if cookies:
                context.add_cookies(cookies)

        context.set_extra_http_headers(
            {
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": "https://www.xingtu.cn/",
            }
        )
        return context

    @staticmethod
    def _is_logged_in(page) -> bool:
        url = page.url.lower()
        if "login" in url or "passport" in url:
            return False
        # 已登录页面通常有用户菜单或达人列表
        indicators = [
            "text=达人广场",
            "text=创作者市场",
            "text=退出登录",
            '[class*="creator"]',
            '[class*="market"]',
        ]
        for sel in indicators:
            try:
                if page.locator(sel).first.is_visible(timeout=2000):
                    return True
            except Exception:
                continue
        return "market" in url or "creator" in url

    @staticmethod
    def _perform_search(page, keyword: str) -> None:
        search_selectors = [
            'input[placeholder*="搜索"]',
            'input[placeholder*="达人"]',
            'input[placeholder*="关键词"]',
            'input[type="search"]',
            ".search-input input",
            '[class*="search"] input',
        ]
        for selector in search_selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=2000):
                    locator.click()
                    locator.fill(keyword)
                    locator.press("Enter")
                    logger.info("Search submitted via selector: %s", selector)
                    page.wait_for_timeout(2000)
                    return
            except Exception:
                continue

        # 备用：带关键词 URL
        page.goto(XINGTU_SEARCH_URL.format(keyword=quote(keyword)), wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

    @staticmethod
    def _parse_dom(page) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        card_selectors = [
            '[class*="author-card"]',
            '[class*="creator-card"]',
            '[class*="star-card"]',
            '[class*="market"] [class*="item"]',
            '[class*="list"] [class*="row"]',
        ]
        for selector in card_selectors:
            cards = page.query_selector_all(selector)
            if not cards:
                continue
            for card in cards[:50]:
                try:
                    text = card.inner_text()
                    if not text.strip():
                        continue
                    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
                    nickname = lines[0] if lines else ""
                    follower_count = _parse_follower_from_text(text)
                    uid_match = re.search(r"\d{8,}", text)
                    platform_uid = uid_match.group() if uid_match else nickname
                    if nickname:
                        items.append(
                            {
                                "nick_name": nickname,
                                "author_id": platform_uid,
                                "follower_count": follower_count,
                                "_dom": True,
                            }
                        )
                except Exception:
                    continue
            if items:
                break
        return items

    def _to_raw_influencers(
        self, keyword: str, items: list[dict[str, Any]], filters: SearchFilters
    ) -> list[RawInfluencer]:
        results: list[RawInfluencer] = []
        for item in items:
            raw = self._map_item(keyword, item)
            if raw and self._passes_filters(raw, filters):
                results.append(raw)
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results

    def _map_item(self, keyword: str, item: dict[str, Any]) -> RawInfluencer | None:
        platform_uid = str(_pick(item, AUTHOR_ID_KEYS) or "")
        nickname = str(_pick(item, NICKNAME_KEYS) or "")
        if not platform_uid and not nickname:
            return None
        if not platform_uid:
            platform_uid = nickname

        tags = _pick(item, TAG_KEYS) or []
        if isinstance(tags, list):
            tag_names = [t.get("name", t) if isinstance(t, dict) else str(t) for t in tags]
        else:
            tag_names = [keyword]
        if keyword not in tag_names:
            tag_names.insert(0, keyword)

        follower_count = _to_int(_pick(item, FOLLOWER_KEYS))
        avg_views = _to_int(_pick(item, AVG_PLAY_KEYS))

        extra = {
            k: v
            for k, v in item.items()
            if k not in AUTHOR_ID_KEYS + NICKNAME_KEYS + FOLLOWER_KEYS + AVATAR_KEYS
        }
        if item.get("_dom"):
            extra["source_type"] = "dom_fallback"

        return RawInfluencer(
            platform="douyin",
            platform_uid=platform_uid,
            nickname=nickname,
            avatar_url=_pick(item, AVATAR_KEYS),
            profile_url=item.get("homepage") or item.get("profile_url"),
            follower_count=follower_count,
            engagement_rate=_to_float(item.get("engagement_rate") or item.get("interact_rate")),
            avg_views=avg_views,
            source="xingtu",
            matched_tags=tag_names[:10],
            match_score=_calc_match_score(keyword, nickname, tag_names),
            extra_data={
                "recent_gmv": item.get("gmv_30d") or item.get("sale_amount"),
                "showcase_count": item.get("showcase_count") or item.get("product_count"),
                "quote_min": item.get("quote_min") or item.get("price_min"),
                "quote_max": item.get("quote_max") or item.get("price_max"),
                "xingtu_raw": {k: v for k, v in extra.items() if not str(k).startswith("_")},
            },
        )

    @staticmethod
    def _passes_filters(raw: RawInfluencer, filters: SearchFilters) -> bool:
        if filters.follower_min and raw.follower_count < filters.follower_min:
            return False
        if filters.follower_max and raw.follower_count > filters.follower_max:
            return False
        if filters.avg_views_min and (raw.avg_views or 0) < filters.avg_views_min:
            return False
        return True


def _load_cookies() -> list[dict]:
    cookies: list[dict] = []

    cookie_file = Path(settings.XINGTU_COOKIE_FILE)
    if cookie_file.exists():
        with open(cookie_file, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data

    cookie_str = settings.XINGTU_COOKIE or settings.DOUYIN_COOKIE
    if not cookie_str:
        return cookies

    for domain in (".xingtu.cn", ".douyin.com"):
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                name, value = part.split("=", 1)
                cookies.append(
                    {
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": domain,
                        "path": "/",
                    }
                )
    return cookies


def _pick(data: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _extract_author_items(data: Any, depth: int = 0) -> list[dict]:
    if depth > 10:
        return []
    results: list[dict] = []
    if isinstance(data, dict):
        if _looks_like_author(data):
            results.append(data)
        for value in data.values():
            results.extend(_extract_author_items(value, depth + 1))
    elif isinstance(data, list):
        for item in data:
            results.extend(_extract_author_items(item, depth + 1))
    return results


def _looks_like_author(data: dict) -> bool:
    has_id = any(k in data for k in AUTHOR_ID_KEYS)
    has_name = any(k in data for k in NICKNAME_KEYS)
    has_metric = any(k in data for k in FOLLOWER_KEYS + AVG_PLAY_KEYS)
    return has_id and has_name and (has_metric or "avatar" in str(data.keys()).lower())


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).replace(",", "").strip()
    multiplier = 1
    if "万" in text:
        multiplier = 10000
        text = text.replace("万", "")
    if "w" in text.lower():
        multiplier = 10000
        text = re.sub(r"[wW]", "", text)
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return 0


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_follower_from_text(text: str) -> int:
    match = re.search(r"([\d.]+)\s*万?\s*粉丝", text)
    if match:
        num = float(match.group(1))
        return int(num * 10000) if "万" in text[match.start() : match.end() + 2] else int(num)
    match = re.search(r"粉丝\s*([\d,]+)", text)
    if match:
        return _to_int(match.group(1))
    return 0


def _calc_match_score(keyword: str, nickname: str, tags: list[str]) -> float:
    score = 40.0
    if keyword in nickname:
        score += 35
    if any(keyword in t for t in tags):
        score += 20
    return round(min(score, 100), 2)
