"""Unit tests for Xiaohongshu note parsing / normalization (no live API)."""

from agentpay.xhs.fetcher import parse_note_id, resolve_note_media_type
from agentpay.xhs.normalize import normalize_to_tikhub_payload, to_clean_note


def test_parse_note_id_from_url():
    url = "https://www.xiaohongshu.com/explore/64f1a2b3c4d5e6f7a8b9c0d1?xsec_token=abc"
    assert parse_note_id(url) == "64f1a2b3c4d5e6f7a8b9c0d1"


def test_parse_note_id_raw():
    assert parse_note_id("64f1a2b3c4d5e6f7a8b9c0d1") == "64f1a2b3c4d5e6f7a8b9c0d1"


def test_resolve_media_type():
    assert resolve_note_media_type("视频") == "video"
    assert resolve_note_media_type("图文") == "image"
    assert resolve_note_media_type(None, note_link="https://x.com/?type=video") == "video"


def test_normalize_dataflow_shaped_payload():
    raw = {
        "success": True,
        "code": 0,
        "data": {
            "data": [
                {
                    "note_list": [
                        {
                            "id": "64f1a2b3c4d5e6f7a8b9c0d1",
                            "type": "normal",
                            "title": "测试笔记",
                            "desc": "内容描述 #话题",
                            "user": {"userid": "u1", "nickname": "作者"},
                            "liked_count": 12,
                            "comments_count": 3,
                            "collected_count": 5,
                            "shared_count": 1,
                            "time": 1700000000000,
                            "images_list": [{"url": "https://img.example/1.jpg"}],
                            "hash_tag": [{"name": "话题"}],
                        }
                    ]
                }
            ]
        },
    }
    normalized = normalize_to_tikhub_payload(raw)
    items = normalized["data"]["data"]["items"]
    note_card = items[0]["note_card"]
    clean = to_clean_note(note_card, note_link="https://xhslink.com/a")
    assert clean["note_id"] == "64f1a2b3c4d5e6f7a8b9c0d1"
    assert clean["title"] == "测试笔记"
    assert clean["author"]["nickname"] == "作者"
    assert clean["stats"]["liked"] == 12
    assert clean["images"] == ["https://img.example/1.jpg"]
    assert "source" not in clean
