#!/usr/bin/env python3
"""Fetch Xiaohongshu note detail via AgentPay paid API (x402).

Usage:
  export GATEWAY_BASE_URL=https://your-agentpay-host
  python scripts/fetch_note.py "<note_url_or_id>" [--type image|video]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _xhs_lib import paid_get  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentPay paid XHS note detail")
    parser.add_argument("note", help="Note share URL or note_id")
    parser.add_argument(
        "--type",
        dest="note_type",
        choices=["image", "video", "图文", "视频"],
        default=None,
    )
    args = parser.parse_args()
    params = {"note": args.note}
    if args.note_type:
        params["note_type"] = args.note_type

    try:
        result = asyncio.run(paid_get("/api/v1/paid/xhs/note", params))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") != "error" else 1
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
