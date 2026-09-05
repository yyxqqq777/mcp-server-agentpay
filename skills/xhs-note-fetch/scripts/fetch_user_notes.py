#!/usr/bin/env python3
"""Fetch Xiaohongshu user notes via AgentPay paid API (x402).

Usage:
  export GATEWAY_BASE_URL=https://your-agentpay-host
  python scripts/fetch_user_notes.py "<user_id>" [--cursor CURSOR]
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
    parser = argparse.ArgumentParser(description="AgentPay paid XHS user notes")
    parser.add_argument("user_id", help="Xiaohongshu user ID")
    parser.add_argument("--cursor", default="", help="Pagination cursor")
    args = parser.parse_args()
    params = {"user_id": args.user_id}
    if args.cursor:
        params["cursor"] = args.cursor

    try:
        result = asyncio.run(paid_get("/api/v1/paid/xhs/user_notes", params))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") != "error" else 1
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
