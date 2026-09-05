"""TikHub 小红书 API 客户端（Dataflow 失败时降级）。"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from agentpay.config import Settings, get_settings

logger = logging.getLogger(__name__)

TIKHUB_IMAGE_NOTE_DETAIL_PATH = "/api/v1/xiaohongshu/app_v2/get_image_note_detail"
TIKHUB_VIDEO_NOTE_DETAIL_PATH = "/api/v1/xiaohongshu/app_v2/get_video_note_detail"
TIKHUB_USER_POSTED_NOTES_PATH = "/api/v1/xiaohongshu/app_v2/get_user_posted_notes"
TIKHUB_FETCH_NOTE_DETAIL_PATH = "/api/v1/xiaohongshu/web_v3/fetch_note_detail"


class TikHubClient:
    BASE_URL = "https://api.tikhub.io"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _headers(self) -> dict[str, str]:
        token = (self.settings.tikhub_api_key or "").strip()
        if not token:
            raise ValueError("未配置 TIKHUB_API_KEY")
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _validate_payload(payload: dict[str, Any]) -> None:
        if payload.get("code") != 200:
            raise ValueError(
                payload.get("message_zh") or payload.get("message") or "TikHub 请求失败"
            )
        inner = payload.get("data") or {}
        if isinstance(inner, dict) and inner.get("ok") is False:
            raise ValueError(inner.get("msg") or "TikHub 请求失败")

    async def get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("TikHub 响应格式异常")
        self._validate_payload(payload)
        return payload

    async def get_user_posted_notes(self, *, user_id: str, cursor: str = "") -> dict[str, Any]:
        user_id = (user_id or "").strip()
        if not user_id:
            raise ValueError("user_id 不能为空")
        params: dict[str, str] = {"user_id": user_id}
        if (cursor or "").strip():
            params["cursor"] = cursor.strip()
        payload = await self.get_json(TIKHUB_USER_POSTED_NOTES_PATH, params)
        logger.info("TikHub user notes ok user_id=%s", user_id)
        return payload

    async def fetch_app_v2_note_detail(
        self,
        *,
        note_id: str = "",
        share_text: str = "",
        is_video: bool,
    ) -> dict[str, Any]:
        note_id = (note_id or "").strip()
        share_text = (share_text or "").strip()
        if not note_id and not share_text:
            raise ValueError("note_id 与 share_text 不能同时为空")

        path = TIKHUB_VIDEO_NOTE_DETAIL_PATH if is_video else TIKHUB_IMAGE_NOTE_DETAIL_PATH
        params: dict[str, str] = {}
        if note_id:
            params["note_id"] = note_id
        else:
            params["share_text"] = share_text

        payload = await self.get_json(path, params)
        logger.info("TikHub App V2 %s note ok", "video" if is_video else "image")
        return payload

    async def fetch_web_v3_note_detail(self, *, note_id: str, xsec_token: str) -> dict[str, Any]:
        note_id = (note_id or "").strip()
        xsec_token = (xsec_token or "").strip()
        if not note_id or not xsec_token:
            raise ValueError("note_id 与 xsec_token 不能为空")
        return await self.get_json(
            TIKHUB_FETCH_NOTE_DETAIL_PATH,
            {"note_id": note_id, "xsec_token": xsec_token},
        )

    @staticmethod
    def extract_user_posted_notes(
        payload: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], bool, str]:
        outer = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(outer, dict):
            return [], False, ""
        inner = outer.get("data") if isinstance(outer.get("data"), dict) else outer
        notes_raw = inner.get("notes") if isinstance(inner, dict) else None
        notes = [item for item in (notes_raw or []) if isinstance(item, dict)]
        has_more = bool(inner.get("has_more")) if isinstance(inner, dict) else False
        next_cursor = ""
        if notes:
            last = notes[-1]
            next_cursor = str(last.get("cursor") or last.get("id") or "").strip()
        return notes, has_more, next_cursor
