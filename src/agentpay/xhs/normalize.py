"""将 Dataflow / TikHub 原始响应统一为干净的笔记结构。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

NoteMediaType = Literal["image", "video"]


def _extract_mobile_raw_note(data_block: dict[str, Any]) -> dict[str, Any] | None:
    inner = data_block.get("data")
    if not isinstance(inner, list) or not inner:
        return None
    first = inner[0]
    if not isinstance(first, dict):
        return None
    note_list = first.get("note_list")
    if isinstance(note_list, list) and note_list:
        item = note_list[0]
        return item if isinstance(item, dict) else None
    if first.get("id") or first.get("note_id"):
        return first
    return None


def _mobile_images_to_image_list(images_list: list[Any] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for img in images_list or []:
        if not isinstance(img, dict):
            continue
        url = img.get("original") or img.get("url") or img.get("url_default") or img.get("url_pre")
        if not url:
            url_multi = img.get("url_multi_level") or {}
            if isinstance(url_multi, dict):
                url = url_multi.get("high") or url_multi.get("medium") or url_multi.get("low")
        if url:
            result.append({"url_default": str(url), "url_pre": str(url)})
    return result


def _mobile_raw_note_to_note_card(raw: dict[str, Any]) -> dict[str, Any]:
    note_type_raw = str(raw.get("type") or "normal").lower()
    user = raw.get("user") or {}
    interaction = raw.get("interaction_info") or {}

    interact_info = {
        "liked_count": raw.get("liked_count") or interaction.get("liked_count"),
        "comment_count": raw.get("comments_count") or interaction.get("comment_count"),
        "collected_count": raw.get("collected_count") or interaction.get("collected_count"),
        "share_count": raw.get("shared_count") or interaction.get("share_count"),
    }

    tag_list = [
        {"name": str(tag.get("name"))}
        for tag in (raw.get("hash_tag") or raw.get("tag_list") or raw.get("topics") or [])
        if isinstance(tag, dict) and tag.get("name")
    ]

    image_list = raw.get("image_list")
    if not image_list:
        image_list = _mobile_images_to_image_list(raw.get("images_list"))

    note_card: dict[str, Any] = {
        "note_id": raw.get("id") or raw.get("note_id"),
        "type": "video" if note_type_raw == "video" else note_type_raw,
        "title": raw.get("title") or "",
        "desc": raw.get("desc") or "",
        "user": {
            "user_id": user.get("userid") or user.get("user_id") or user.get("id"),
            "nickname": user.get("nickname") or user.get("name"),
        },
        "interact_info": interact_info,
        "time": raw.get("time"),
        "image_list": image_list,
        "tag_list": tag_list,
    }

    video_info = raw.get("video_info_v2") or raw.get("video")
    if isinstance(video_info, dict):
        media = video_info.get("media") or {}
        if media.get("stream"):
            note_card["video"] = {"media": media}
        elif video_info.get("media"):
            note_card["video"] = video_info

    return note_card


def normalize_to_tikhub_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    if raw_payload.get("code") == 200:
        data = raw_payload.get("data")
        if isinstance(data, dict):
            inner_data = data.get("data")
            if isinstance(inner_data, dict) and inner_data.get("items"):
                return raw_payload
            raw_note = _extract_mobile_raw_note(data)
            if raw_note:
                note_card = _mobile_raw_note_to_note_card(raw_note)
                return {"code": 200, "data": {"data": {"items": [{"note_card": note_card}]}}}
        return raw_payload

    data = raw_payload.get("data")
    if not isinstance(data, dict):
        raise ValueError(raw_payload.get("error") or raw_payload.get("detail") or "笔记详情获取失败")

    if raw_payload.get("success"):
        raw_note = _extract_mobile_raw_note(data)
        if raw_note:
            note_card = _mobile_raw_note_to_note_card(raw_note)
            return {"code": 200, "data": {"data": {"items": [{"note_card": note_card}]}}}

    if isinstance(data.get("data"), dict) and (data.get("data") or {}).get("items"):
        return {"code": 200, "data": data}

    if data.get("items"):
        return {"code": 200, "data": {"data": data}}

    if data.get("note_card"):
        return {"code": 200, "data": {"data": {"items": [data]}}}

    if data.get("note_id") or data.get("type"):
        return {"code": 200, "data": {"data": {"items": [{"note_card": data}]}}}

    raise ValueError("无法解析笔记详情响应结构")


def extract_note_card(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        inner = payload.get("data") or {}
        data_block = inner.get("data") if isinstance(inner, dict) else {}
        items = (data_block or {}).get("items") or []
        if not items:
            return None
        first = items[0] or {}
        note_card = first.get("note_card") or {}
        return note_card if isinstance(note_card, dict) else None
    except (AttributeError, TypeError, KeyError):
        return None


def note_card_has_video_stream(note_card: dict[str, Any]) -> bool:
    video_block = note_card.get("video") or {}
    media = video_block.get("media") or {}
    stream = media.get("stream") or {}
    for codec in ("h264", "h265", "h266", "av1"):
        entries = stream.get(codec) or []
        if entries and isinstance(entries[0], dict) and entries[0].get("master_url"):
            return True
    return False


def extract_video_url(note_card: dict[str, Any]) -> str | None:
    video_block = note_card.get("video") or {}
    media = video_block.get("media") or {}
    stream = media.get("stream") or {}
    for codec in ("h264", "h265", "h266", "av1"):
        entries = stream.get(codec) or []
        if entries and isinstance(entries[0], dict):
            url = entries[0].get("master_url") or entries[0].get("backup_url")
            if url:
                return str(url)
    return None


def extract_image_urls(note_card: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for img in note_card.get("image_list") or []:
        if not isinstance(img, dict):
            continue
        url = img.get("url_default") or img.get("url_pre") or img.get("url") or img.get("original")
        if url:
            urls.append(str(url))
    return urls


def _ms_to_iso(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        ts = int(value)
        if ts > 10_000_000_000:
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(value)


def to_clean_note(note_card: dict[str, Any], *, note_link: str = "", source: str = "") -> dict[str, Any]:
    """面向 MCP / Agent 的干净笔记结构（不暴露上游实现）。"""
    note_type_raw = str(note_card.get("type") or "").lower()
    is_video = note_type_raw == "video"
    user = note_card.get("user") or {}
    interact = note_card.get("interact_info") or {}
    tags = [
        str(t.get("name"))
        for t in (note_card.get("tag_list") or [])
        if isinstance(t, dict) and t.get("name")
    ]
    # source arg kept for internal logs only — never returned to agents
    _ = source

    return {
        "note_id": note_card.get("note_id"),
        "note_link": note_link or None,
        "note_type": "video" if is_video else "image",
        "title": (note_card.get("title") or "").strip(),
        "desc": note_card.get("desc") or "",
        "topics": tags,
        "author": {
            "user_id": user.get("user_id"),
            "nickname": user.get("nickname"),
        },
        "stats": {
            "liked": interact.get("liked_count"),
            "comments": interact.get("comment_count"),
            "collected": interact.get("collected_count"),
            "shared": interact.get("share_count"),
        },
        "published_at": _ms_to_iso(note_card.get("time")),
        "images": extract_image_urls(note_card),
        "video_url": extract_video_url(note_card) if is_video else None,
    }


def summarize_list_note(raw: dict[str, Any]) -> dict[str, Any]:
    """用户主页列表项精简。"""
    note_id = raw.get("id") or raw.get("note_id") or raw.get("noteId")
    user = raw.get("user") or {}
    return {
        "note_id": note_id,
        "title": raw.get("title") or raw.get("display_title") or "",
        "type": str(raw.get("type") or "").lower() or None,
        "liked_count": raw.get("liked_count") or raw.get("likes"),
        "cover": (
            (raw.get("cover") or {}).get("url")
            if isinstance(raw.get("cover"), dict)
            else raw.get("cover")
        ),
        "author": {
            "user_id": user.get("userid") or user.get("user_id") or user.get("id"),
            "nickname": user.get("nickname") or user.get("name"),
        },
        "cursor": raw.get("cursor"),
    }
