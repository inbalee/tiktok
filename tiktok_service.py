"""TikTok user info scraper service — adapted from TikTok-User-Info-Scraper."""

import re
import urllib.parse

import requests
from bs4 import BeautifulSoup


class TikTokUserNotFoundError(Exception):
    pass


class TikTokFetchError(Exception):
    pass


def _parse_bool(value: str) -> bool:
    return value.lower() == "true"


def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class TikTokSearchNotFoundError(Exception):
    pass


class TikTokCommentsNotFoundError(Exception):
    pass


class TikTokVideoNotFoundError(Exception):
    pass


def _headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }


def _session() -> requests.Session:
    session = requests.Session()
    session.get("https://www.tiktok.com/", headers=_headers(), timeout=20)
    return session


def search_by_keyword(keyword: str) -> dict:
    """Search TikTok users, videos, hashtags, and sounds by keyword."""
    keyword = keyword.strip()
    if not keyword:
        raise TikTokFetchError("Keyword is required")

    session = _session()
    url = f"https://www.tiktok.com/node/share/discover?keyword={urllib.parse.quote(keyword)}"

    try:
        response = session.get(
            url,
            headers={**_headers(), "Referer": "https://www.tiktok.com/"},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise TikTokFetchError(f"Network error: {exc}") from exc

    if response.status_code != 200:
        raise TikTokFetchError(
            f"Unable to search (HTTP {response.status_code})"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TikTokFetchError("Invalid search response") from exc

    if payload.get("statusCode") != 0:
        raise TikTokFetchError("Search request failed")

    users: list[dict] = []
    hashtags: list[dict] = []
    sounds: list[dict] = []

    for section in payload.get("body", []):
        for item in section.get("exploreList", []):
            card = item.get("cardItem", {})
            card_type = card.get("type")
            if card_type == 2:
                users.append(_parse_user_card(card))
            elif card_type == 3:
                hashtags.append(_parse_hashtag_card(card))
            elif card_type == 1:
                sounds.append(_parse_sound_card(card))

    videos = _search_videos(keyword)

    if not users and not hashtags and not sounds and not videos:
        raise TikTokSearchNotFoundError(
            f"No results found for \"{keyword}\"."
        )

    return {
        "keyword": keyword,
        "users": users,
        "videos": videos,
        "hashtags": hashtags,
        "sounds": sounds,
    }


def _search_videos(keyword: str, count: int = 12) -> list[dict]:
    params = {
        "keywords": keyword,
        "count": max(1, min(count, 30)),
        "cursor": 0,
    }

    try:
        response = requests.get(
            "https://www.tikwm.com/api/feed/search",
            params=params,
            headers=_headers(),
            timeout=30,
        )
    except requests.RequestException:
        return []

    if response.status_code != 200:
        return []

    try:
        payload = response.json()
    except ValueError:
        return []

    if payload.get("code") != 0:
        return []

    return [
        _parse_video_item(item)
        for item in (payload.get("data") or {}).get("videos") or []
    ]


def _parse_video_item(item: dict) -> dict:
    author = item.get("author") or {}
    username = author.get("unique_id", "")
    video_id = item.get("video_id") or item.get("aweme_id") or item.get("id", "")

    return {
        "video_id": str(video_id),
        "title": item.get("title") or item.get("desc", ""),
        "cover": item.get("cover") or item.get("origin_cover", ""),
        "duration": _parse_int(item.get("duration")),
        "play_count": _parse_int(item.get("play_count")),
        "likes": _parse_int(item.get("digg_count")),
        "comment_count": _parse_int(item.get("comment_count")),
        "share_count": _parse_int(item.get("share_count")),
        "username": username,
        "nickname": author.get("nickname", ""),
        "author_avatar": author.get("avatar", ""),
        "video_url": (
            f"https://www.tiktok.com/@{username}/video/{video_id}"
            if username and video_id
            else f"https://www.tiktok.com/video/{video_id}"
        ),
    }


def _parse_user_card(card: dict) -> dict:
    extra = card.get("extraInfo", {})
    username = card.get("subTitle", "").lstrip("@")
    if not username and card.get("link", "").startswith("/@"):
        username = card["link"][2:]

    return {
        "user_id": extra.get("userId") or card.get("id", ""),
        "username": username,
        "nickname": card.get("title", ""),
        "biography": card.get("description", ""),
        "profile_pic": card.get("cover", ""),
        "profile_url": f"https://www.tiktok.com/@{username}" if username else "",
        "verified": bool(extra.get("verified")),
        "followers": _parse_int(extra.get("fans", 0)),
        "following": _parse_int(extra.get("following", 0)),
        "likes": _parse_int(extra.get("likes", 0)),
        "videos": _parse_int(extra.get("video", 0)),
        "heart": _parse_int(extra.get("heart", 0)),
        "digg_count": _parse_int(extra.get("digg", 0)),
        "sec_uid": extra.get("secUid", ""),
    }


def _parse_hashtag_card(card: dict) -> dict:
    link = card.get("link", "")
    tag = link.removeprefix("/tag/").lstrip("/")
    return {
        "title": card.get("title", ""),
        "views": card.get("subTitle", ""),
        "url": f"https://www.tiktok.com/tag/{tag}" if tag else "",
    }


def _parse_sound_card(card: dict) -> dict:
    link = card.get("link", "")
    return {
        "title": card.get("title", ""),
        "videos": card.get("subTitle", ""),
        "url": f"https://www.tiktok.com{link}" if link.startswith("/") else link,
    }


def _parse_video_id(value: str) -> str:
    value = value.strip()
    if not value:
        raise TikTokFetchError("Video ID is required")

    url_match = re.search(r"/video/(\d+)", value)
    if url_match:
        return url_match.group(1)

    if value.isdigit():
        return value

    raise TikTokFetchError("Invalid video ID. Enter a numeric ID or TikTok video URL.")


def _normalize_video_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise TikTokFetchError("Video link is required")

    if value.startswith("http://") or value.startswith("https://"):
        return value

    video_id = _parse_video_id(value)
    return f"https://www.tiktok.com/video/{video_id}"


def _parse_video_metadata(item: dict) -> dict:
    author = item.get("author") or {}
    username = author.get("unique_id", "")
    video_id = str(item.get("id") or item.get("video_id") or "")
    music = item.get("music_info") or {}
    create_time = _parse_int(item.get("create_time"))

    return {
        "video_id": video_id,
        "title": item.get("title") or "",
        "cover": item.get("cover") or item.get("origin_cover", ""),
        "duration": _parse_int(item.get("duration")),
        "region": item.get("region", ""),
        "play_count": _parse_int(item.get("play_count")),
        "likes": _parse_int(item.get("digg_count")),
        "comment_count": _parse_int(item.get("comment_count")),
        "share_count": _parse_int(item.get("share_count")),
        "download_count": _parse_int(item.get("download_count")),
        "collect_count": _parse_int(item.get("collect_count")),
        "create_time": create_time,
        "is_ad": bool(item.get("is_ad")),
        "username": username,
        "nickname": author.get("nickname", ""),
        "author_id": str(author.get("id", "")),
        "author_avatar": author.get("avatar", ""),
        "profile_url": f"https://www.tiktok.com/@{username}" if username else "",
        "video_url": (
            f"https://www.tiktok.com/@{username}/video/{video_id}"
            if username and video_id
            else f"https://www.tiktok.com/video/{video_id}"
        ),
        "music_title": music.get("title", ""),
        "music_author": music.get("author", ""),
        "music_duration": _parse_int(music.get("duration")),
    }


def get_video_metadata(value: str) -> dict:
    """Fetch metadata for a TikTok video link or ID."""
    video_url = _normalize_video_url(value)

    try:
        response = requests.get(
            "https://www.tikwm.com/api/",
            params={"url": video_url},
            headers=_headers(),
            timeout=30,
        )
    except requests.RequestException as exc:
        raise TikTokFetchError(f"Network error: {exc}") from exc

    if response.status_code != 200:
        raise TikTokFetchError(
            f"Unable to fetch video metadata (HTTP {response.status_code})"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TikTokFetchError("Invalid video metadata response") from exc

    if payload.get("code") == -1 and "limit" in payload.get("msg", "").lower():
        raise TikTokFetchError("Rate limited. Please wait a moment and try again.")

    if payload.get("code") != 0:
        raise TikTokFetchError(payload.get("msg") or "Failed to fetch video metadata")

    data = payload.get("data")
    if not data:
        raise TikTokVideoNotFoundError("Video not found. Check the link and try again.")

    metadata = _parse_video_metadata(data)
    metadata["source_url"] = video_url
    return metadata


def get_video_comments(
    video_id: str, cursor: int = 0, count: int = 50
) -> dict:
    """Fetch commenters and comment text for a TikTok video."""
    video_id = _parse_video_id(video_id)
    count = max(1, min(count, 50))
    cursor = max(0, cursor)

    params = {
        "url": f"https://www.tiktok.com/video/{video_id}",
        "count": count,
        "cursor": cursor,
    }

    try:
        response = requests.get(
            "https://www.tikwm.com/api/comment/list",
            params=params,
            headers=_headers(),
            timeout=30,
        )
    except requests.RequestException as exc:
        raise TikTokFetchError(f"Network error: {exc}") from exc

    if response.status_code != 200:
        raise TikTokFetchError(
            f"Unable to fetch comments (HTTP {response.status_code})"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TikTokFetchError("Invalid comment response") from exc

    if payload.get("code") == -1 and "limit" in payload.get("msg", "").lower():
        raise TikTokFetchError("Rate limited. Please wait a moment and try again.")

    if payload.get("code") != 0:
        raise TikTokFetchError(payload.get("msg") or "Failed to fetch comments")

    data = payload.get("data") or {}
    raw_comments = data.get("comments") or []
    if not raw_comments and cursor == 0:
        raise TikTokCommentsNotFoundError(
            "No comments found for this video."
        )

    comments = []
    for item in raw_comments:
        user = item.get("user") or {}
        username = user.get("unique_id") or user.get("uniqueId") or ""
        comments.append(
            {
                "comment_id": item.get("id", ""),
                "username": username,
                "nickname": user.get("nickname", ""),
                "text": item.get("text", ""),
                "likes": _parse_int(item.get("digg_count")),
                "reply_count": _parse_int(item.get("reply_total")),
                "create_time": _parse_int(item.get("create_time")),
                "profile_url": (
                    f"https://www.tiktok.com/@{username}" if username else ""
                ),
            }
        )

    return {
        "video_id": video_id,
        "video_url": f"https://www.tiktok.com/video/{video_id}",
        "total": _parse_int(data.get("total")),
        "cursor": _parse_int(data.get("cursor")),
        "has_more": bool(data.get("hasMore")),
        "comments": comments,
    }


def get_user_info(identifier: str, by_id: bool = False) -> dict:
    """Fetch TikTok user profile data by username or user ID."""
    if identifier.startswith("@"):
        identifier = identifier[1:]

    url = f"https://www.tiktok.com/@{identifier}"
    headers = _headers()

    try:
        response = requests.get(url, headers=headers, timeout=20)
    except requests.RequestException as exc:
        raise TikTokFetchError(f"Network error: {exc}") from exc

    if response.status_code != 200:
        raise TikTokFetchError(
            f"Unable to fetch profile (HTTP {response.status_code})"
        )

    html_content = response.text

    try:
        BeautifulSoup(html_content, "lxml")
    except Exception:
        BeautifulSoup(html_content, "html.parser")

    patterns = {
        "user_id": r'"webapp.user-detail":{"userInfo":{"user":{"id":"(\d+)"',
        "unique_id": r'"uniqueId":"(.*?)"',
        "nickname": r'"nickname":"(.*?)"',
        "followers": r'"followerCount":(\d+)',
        "following": r'"followingCount":(\d+)',
        "likes": r'"heartCount":(\d+)',
        "videos": r'"videoCount":(\d+)',
        "signature": r'"signature":"(.*?)"',
        "verified": r'"verified":(true|false)',
        "secUid": r'"secUid":"(.*?)"',
        "commentSetting": r'"commentSetting":(\d+)',
        "privateAccount": r'"privateAccount":(true|false)',
        "region": r'"ttSeller":false,"region":"([^"]*)"',
        "heart": r'"heart":(\d+)',
        "diggCount": r'"diggCount":(\d+)',
        "friendCount": r'"friendCount":(\d+)',
        "profile_pic": r'"avatarLarger":"(.*?)"',
    }

    raw: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, html_content)
        raw[key] = match.group(1) if match else ""

    if not raw.get("unique_id"):
        raise TikTokUserNotFoundError(
            "User not found. Check the username and try again."
        )

    profile_pic = raw.get("profile_pic", "").replace("\\u002F", "/")
    bio = raw.get("signature", "").replace("\\n", "\n")
    social_links = _extract_social_links(html_content, bio)

    return {
        "user_id": raw["user_id"],
        "username": raw["unique_id"],
        "nickname": raw["nickname"],
        "followers": _parse_int(raw["followers"]),
        "following": _parse_int(raw["following"]),
        "likes": _parse_int(raw["likes"]),
        "videos": _parse_int(raw["videos"]),
        "biography": bio,
        "verified": _parse_bool(raw["verified"]) if raw["verified"] else False,
        "sec_uid": raw["secUid"],
        "comment_setting": _parse_int(raw["commentSetting"]),
        "private_account": (
            _parse_bool(raw["privateAccount"]) if raw["privateAccount"] else False
        ),
        "region": raw["region"],
        "heart": _parse_int(raw["heart"]),
        "digg_count": _parse_int(raw["diggCount"]),
        "friend_count": _parse_int(raw["friendCount"]),
        "profile_pic": profile_pic,
        "profile_url": f"https://www.tiktok.com/@{raw['unique_id']}",
        "social_links": social_links,
    }


def _extract_social_links(html_content: str, bio: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(label: str, url: str) -> None:
        if url and not url.startswith(("http://", "https://", "mailto:")):
            url = f"https://{url.lstrip('/')}"
        key = f"{label}|{url}"
        if key not in seen:
            seen.add(key)
            links.append({"label": label, "url": url})

    link_urls = re.findall(
        r'href="(https://www\.tiktok\.com/link/v2\?[^"]*?scene=bio_url[^"]*?target=([^"&]+))"',
        html_content,
    )
    for full_url, target in link_urls:
        target_decoded = urllib.parse.unquote(target)
        text_pattern = (
            rf'href="{re.escape(full_url)}"[^>]*>.*?'
            r'<span[^>]*SpanLink[^>]*>([^<]+)</span>'
        )
        text_match = re.search(text_pattern, html_content, re.DOTALL)
        label = text_match.group(1) if text_match else target_decoded
        add(label, target_decoded)

    bio_link_pattern = r'"bioLink":{"link":"([^"]+)","risk":(\d+)}'
    for link, _ in re.findall(bio_link_pattern, html_content):
        clean_link = link.replace("\\u002F", "/")
        add(clean_link, clean_link)

    ig_pattern = re.search(r"[iI][gG]:\s*@?([a-zA-Z0-9._]+)", bio)
    if ig_pattern:
        username = ig_pattern.group(1)
        add(f"Instagram @{username}", f"https://instagram.com/{username}")

    social_patterns = {
        "twitter": (r"([tT]witter|[xX]):\s*@?([a-zA-Z0-9._]+)", "https://x.com/{}"),
        "youtube": (
            r"([yY][tT]|[yY]outube):\s*@?([a-zA-Z0-9._]+)",
            "https://youtube.com/@{}",
        ),
        "telegram": (r"[tT]elegram:\s*@?([a-zA-Z0-9._]+)", "https://t.me/{}"),
    }
    for _, (pattern, url_template) in social_patterns.items():
        match = re.search(pattern, bio)
        if match:
            username = match.group(2) if len(match.groups()) > 1 else match.group(1)
            add(username, url_template.format(username))

    email_pattern = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", bio)
    if email_pattern:
        email = email_pattern.group(0)
        add(email, f"mailto:{email}")

    return links
