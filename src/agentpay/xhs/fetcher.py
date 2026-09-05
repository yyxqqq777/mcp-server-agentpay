"""小红书笔记拉取：Dataflow 优先，TikHub 降级。"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

from agentpay.config import Settings, get_settings
from agentpay.xhs.dataflow import DataflowClient
from agentpay.xhs.normalize import (
    extract_note_card,
    normalize_to_tikhub_payload,
    note_card_has_video_stream,
    summarize_list_note,
    to_clean_note,
)
from agentpay.xhs.tikhub import TikHubClient

logger = logging.getLogger(__name__)

_NOTE_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{24}$")
NoteMediaType = Literal["image", "video"]


def parse_note_id(note_link: str) -> str:
    text = (note_link or "").strip()
    if not text:
        raise ValueError("笔记链接为空")
    if _NOTE_ID_PATTERN.fullmatch(text):
        return text

    parsed = urlparse(text)
    path = (parsed.path or "").strip("/")
    note_id = ""
    if path:
        parts = path.split("/")
        note_id = parts[-1] if parts else ""
    if not note_id:
        raise ValueError(f"无法从链接解析笔记 ID: {text}")
    return note_id


def extract_xsec_token(note_link: str) -> str:
    parsed = urlparse((note_link or "").strip())
    query = parse_qs(parsed.query or "")
    tokens = query.get("xsec_token") or query.get("xsecToken") or []
    return tokens[0].strip() if tokens else ""


def resolve_note_media_type(
    note_type_hint: str | None = None,
    *,
    note_link: str = "",
) -> NoteMediaType | None:
    text = str(note_type_hint or "").strip().lower()
    if text in ("2", "视频", "视频笔记", "video", "v"):
        return "video"
    if text in ("1", "图文", "图文笔记", "image", "normal", "图集", "笔记"):
        return "image"

    link = (note_link or "").lower()
    if "type=video" in link:
        return "video"
    if "type=normal" in link:
        return "image"
    return None


async def _fetch_dataflow(
    *,
    note_id: str,
    media_type: NoteMediaType | None,
    settings: Settings,
) -> dict[str, Any]:
    client = DataflowClient(settings)
    is_video: bool | None
    if media_type == "video":
        is_video = True
    elif media_type == "image":
        is_video = False
    else:
        is_video = None
    payload = await client.fetch_note_detail(note_id=note_id, is_video=is_video)
    return normalize_to_tikhub_payload(payload)


async def _fetch_tikhub(
    *,
    note_id: str,
    note_link: str,
    media_type: NoteMediaType | None,
    settings: Settings,
) -> dict[str, Any]:
    client = TikHubClient(settings)
    attempts: list[bool]
    if media_type == "video":
        attempts = [True]
    elif media_type == "image":
        attempts = [False]
    else:
        attempts = [False, True]

    last_error: Exception | None = None
    for is_video in attempts:
        try:
            payload = await client.fetch_app_v2_note_detail(
                note_id=note_id,
                share_text=note_link if not note_id else "",
                is_video=is_video,
            )
            normalized = normalize_to_tikhub_payload(payload)
            if not is_video and media_type is None:
                note_card = extract_note_card(normalized)
                if (
                    isinstance(note_card, dict)
                    and str(note_card.get("type") or "").lower() == "video"
                    and not note_card_has_video_stream(note_card)
                ):
                    continue
            return normalized
        except Exception as exc:
            last_error = exc
            logger.warning("TikHub %s failed note_id=%s: %s", "video" if is_video else "image", note_id, exc)

    raise ValueError(str(last_error) if last_error else "TikHub 笔记详情获取失败")


def _needs_video_fallback(payload: dict[str, Any], media_type: NoteMediaType | None) -> bool:
    note_card = extract_note_card(payload)
    if not isinstance(note_card, dict):
        return True
    card_type = str(note_card.get("type") or "").lower()
    is_video = media_type == "video" or card_type == "video"
    if not is_video:
        return False
    return not note_card_has_video_stream(note_card)


async def fetch_note_detail(
    *,
    note_id_or_link: str,
    note_type_hint: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    拉取笔记详情并返回干净结构。
    策略：Dataflow 优先 → 视频无 stream 或失败时降级 TikHub。
    """
    settings = settings or get_settings()
    raw = (note_id_or_link or "").strip()
    note_id = parse_note_id(raw)
    note_link = raw if not _NOTE_ID_PATTERN.fullmatch(raw) else ""
    media_type = resolve_note_media_type(note_type_hint, note_link=note_link or note_id)

    source = "dataflow"
    dataflow_token = (settings.dataflow_api_token or "").strip()
    tikhub_key = (settings.tikhub_api_key or "").strip()

    if not dataflow_token and not tikhub_key:
        raise ValueError("未配置 DATAFLOW_API_TOKEN 或 TIKHUB_API_KEY")

    payload: dict[str, Any] | None = None
    errors: list[str] = []

    if dataflow_token:
        try:
            payload = await _fetch_dataflow(
                note_id=note_id, media_type=media_type, settings=settings
            )
            if _needs_video_fallback(payload, media_type) and tikhub_key:
                logger.info("Dataflow video missing stream, fallback TikHub note_id=%s", note_id)
                payload = None
            else:
                source = "dataflow"
        except Exception as exc:
            errors.append(f"dataflow: {exc}")
            logger.warning("Dataflow failed note_id=%s: %s", note_id, exc)
            payload = None

    if payload is None and tikhub_key:
        try:
            payload = await _fetch_tikhub(
                note_id=note_id,
                note_link=note_link,
                media_type=media_type,
                settings=settings,
            )
            source = "tikhub"
        except Exception as exc:
            errors.append(f"tikhub: {exc}")
            raise ValueError(f"笔记详情获取失败: {'; '.join(errors)}") from exc

    if payload is None:
        raise ValueError(f"笔记详情获取失败: {'; '.join(errors) or '无可用数据源'}")

    note_card = extract_note_card(payload)
    if not note_card:
        raise ValueError("无法解析笔记详情")

    logger.info("note detail ok note_id=%s provider=%s", note_id, source)
    return {
        "status": "success",
        "note": to_clean_note(note_card, note_link=note_link),
    }


async def fetch_user_notes(
    *,
    user_id: str,
    cursor: str = "",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """拉取用户已发布笔记列表。Dataflow 优先，失败降级 TikHub。"""
    settings = settings or get_settings()
    user_id = (user_id or "").strip()
    if not user_id:
        raise ValueError("user_id 不能为空")

    dataflow_token = (settings.dataflow_api_token or "").strip()
    tikhub_key = (settings.tikhub_api_key or "").strip()
    if not dataflow_token and not tikhub_key:
        raise ValueError("未配置 DATAFLOW_API_TOKEN 或 TIKHUB_API_KEY")

    notes: list[dict[str, Any]] = []
    has_more = False
    next_cursor = ""
    source = ""
    last_error: Exception | None = None

    if dataflow_token:
        try:
            client = DataflowClient(settings)
            payload = await client.get_user_posted_notes(user_id=user_id, cursor=cursor)
            notes, has_more, next_cursor = DataflowClient.extract_user_posted_notes(payload)
            source = "dataflow"
        except Exception as exc:
            last_error = exc
            logger.warning("Dataflow user notes failed user_id=%s: %s", user_id, exc)

    if not source and tikhub_key:
        try:
            client = TikHubClient(settings)
            payload = await client.get_user_posted_notes(user_id=user_id, cursor=cursor)
            notes, has_more, next_cursor = TikHubClient.extract_user_posted_notes(payload)
            source = "tikhub"
        except Exception as exc:
            last_error = exc
            raise ValueError(f"用户笔记列表获取失败: {exc}") from exc

    if not source:
        raise ValueError(f"用户笔记列表获取失败: {last_error or '无可用数据源'}")

    logger.info("user notes ok user_id=%s provider=%s count=%s", user_id, source, len(notes))
    return {
        "status": "success",
        "user_id": user_id,
        "has_more": has_more,
        "next_cursor": next_cursor or None,
        "total": len(notes),
        "notes": [summarize_list_note(n) for n in notes],
    }
