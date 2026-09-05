"""Dataflow 小红书 API 客户端（用户笔记列表 / 笔记详情）。"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from agentpay.config import Settings, get_settings

logger = logging.getLogger(__name__)

DATAFLOW_USER_POSTED_PATH = "/api/xhs/v3/appuserposted"
DATAFLOW_NOTE_DETAIL_PATH = "/api/xhs/v3/notedetail"
DATAFLOW_VIDEO_NOTE_DETAIL_PATH = "/api/xhs/v3/videonotedetail"


class DataflowClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _base_url(self) -> str:
        return (self.settings.dataflow_base_url or "https://dataflowserver.org").rstrip("/")

    def _headers(self) -> dict[str, str]:
        token = (self.settings.dataflow_api_token or "").strip()
        if not token:
            raise ValueError("未配置 DATAFLOW_API_TOKEN")
        return {
            "Authorization": f"Token {token}",
            "Accept": "application/json",
        }

    @staticmethod
    def _unwrap_data_field(value: Any) -> Any:
        cur = value
        for _ in range(3):
            if isinstance(cur, str):
                text = cur.strip()
                if not text:
                    return cur
                try:
                    cur = json.loads(text)
                except json.JSONDecodeError:
                    return cur
                continue
            if isinstance(cur, dict) and isinstance(cur.get("data"), str):
                try:
                    cur = {**cur, "data": json.loads(cur["data"])}
                except json.JSONDecodeError:
                    return cur
                continue
            break
        return cur

    @staticmethod
    def _validate_outer(payload: dict[str, Any]) -> None:
        code = payload.get("code")
        if code not in (0, "0", 200, "200"):
            raise ValueError(payload.get("msg") or payload.get("message") or "Dataflow 请求失败")

    async def get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self._base_url()}{path}"
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Dataflow 响应格式异常")
        self._validate_outer(payload)
        return payload

    async def get_user_posted_notes(self, *, user_id: str, cursor: str = "") -> dict[str, Any]:
        user_id = (user_id or "").strip()
        if not user_id:
            raise ValueError("user_id 不能为空")
        params: dict[str, str] = {"userId": user_id}
        if (cursor or "").strip():
            params["cursor"] = cursor.strip()
        payload = await self.get_json(DATAFLOW_USER_POSTED_PATH, params)
        logger.info("Dataflow user notes ok user_id=%s", user_id)
        return payload

    async def fetch_note_detail(
        self,
        *,
        note_id: str,
        is_video: bool | None = None,
    ) -> dict[str, Any]:
        note_id = (note_id or "").strip()
        if not note_id:
            raise ValueError("note_id 不能为空")

        if is_video is True:
            payload = await self.get_json(DATAFLOW_VIDEO_NOTE_DETAIL_PATH, {"noteId": note_id})
            return self.to_mobile_detail_payload(payload)

        if is_video is False:
            payload = await self.get_json(DATAFLOW_NOTE_DETAIL_PATH, {"noteId": note_id})
            return self.to_mobile_detail_payload(payload)

        image_payload = await self.get_json(DATAFLOW_NOTE_DETAIL_PATH, {"noteId": note_id})
        image_normalized = self.to_mobile_detail_payload(image_payload)
        if self._payload_note_type(image_normalized) != "video":
            return image_normalized

        try:
            video_payload = await self.get_json(
                DATAFLOW_VIDEO_NOTE_DETAIL_PATH, {"noteId": note_id}
            )
            return self.to_mobile_detail_payload(video_payload)
        except Exception as exc:
            logger.warning("Dataflow video fallback to image note_id=%s: %s", note_id, exc)
            return image_normalized

    @classmethod
    def _payload_note_type(cls, payload: dict[str, Any]) -> str:
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return ""
        items = data.get("data")
        if not isinstance(items, list) or not items:
            return ""
        first = items[0]
        if not isinstance(first, dict):
            return ""
        note_list = first.get("note_list")
        if isinstance(note_list, list) and note_list and isinstance(note_list[0], dict):
            return str(note_list[0].get("type") or "").lower()
        return str(first.get("type") or "").lower()

    @classmethod
    def to_mobile_detail_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        unwrapped = cls._unwrap_data_field(payload)
        if not isinstance(unwrapped, dict):
            raise ValueError("Dataflow 笔记详情格式异常")

        body = unwrapped.get("data")
        body = cls._unwrap_data_field(body) if body is not None else None

        items: list[Any] | None = None
        if isinstance(body, list):
            items = body
        elif isinstance(body, dict):
            inner = body.get("data")
            if isinstance(inner, list):
                items = inner
            elif isinstance(inner, dict) and isinstance(inner.get("note_list"), list):
                items = [inner]
            elif isinstance(body.get("note_list"), list):
                items = [body]

        if not items:
            raise ValueError(unwrapped.get("msg") or "Dataflow 笔记详情 data 为空")

        normalized_items: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("note_list"), list):
                normalized_items.append(item)
            elif item.get("id") or item.get("note_id") or item.get("type"):
                normalized_items.append({"model_type": "note", "note_list": [item]})
            else:
                normalized_items.append(item)

        if not normalized_items:
            raise ValueError("Dataflow 笔记详情无法解析 note")

        return {"success": True, "code": 0, "data": {"data": normalized_items}}

    @staticmethod
    def extract_user_posted_notes(
        payload: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], bool, str]:
        if not isinstance(payload, dict):
            return [], False, ""

        body = payload.get("data")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return [], False, ""

        if isinstance(body, dict):
            inner = body.get("data") if isinstance(body.get("data"), (dict, list)) else body
            if isinstance(inner, dict) and (
                "notes" in inner or "has_more" in inner or "note_list" in inner
            ):
                body = inner
            elif isinstance(body.get("data"), str):
                try:
                    nested = json.loads(body["data"])
                except json.JSONDecodeError:
                    nested = None
                if isinstance(nested, dict):
                    body = nested.get("data") if isinstance(nested.get("data"), dict) else nested

        if not isinstance(body, dict):
            return [], False, ""

        notes_raw = body.get("notes") or body.get("note_list") or []
        notes = [item for item in notes_raw if isinstance(item, dict)]
        has_more = bool(body.get("has_more"))
        next_cursor = ""
        if notes:
            last = notes[-1]
            next_cursor = str(
                last.get("cursor") or last.get("id") or last.get("note_id") or ""
            ).strip()
        return notes, has_more, next_cursor
