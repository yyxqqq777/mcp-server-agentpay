"""Mock wholesale pricing data provider."""

from __future__ import annotations

import hashlib
from typing import Any


def _stable_price(keyword: str, index: int) -> float:
    seed = hashlib.md5(f"{keyword}:{index}".encode()).hexdigest()
    return round(0.5 + (int(seed[:8], 16) % 500) / 100, 2)


def _factory_locations() -> list[str]:
    return [
        "Yiwu, Zhejiang",
        "Shenzhen, Guangdong",
        "Guangzhou, Guangdong",
        "Dongguan, Guangdong",
        "Ningbo, Zhejiang",
        "Hangzhou, Zhejiang",
    ]


def query_wholesale_pricing(
    keyword: str,
    category_id: str | None = None,
    max_price: float | None = None,
) -> dict[str, Any]:
    """
    Return structured manufacturing/wholesale data.
    In production, this would call 1688/Yiwu APIs behind the paywall.
    """
    locations = _factory_locations()
    items: list[dict[str, Any]] = []

    for i in range(5):
        unit_price = _stable_price(keyword, i)
        if max_price is not None and unit_price > max_price:
            continue

        item_id = f"CN-{hashlib.md5(f'{keyword}{i}'.encode()).hexdigest()[:6].upper()}"
        items.append(
            {
                "item_id": item_id,
                "name": f"Factory Direct: {keyword.title()} — Model {i + 1}",
                "factory_location": locations[i % len(locations)],
                "supplier_verified": i % 2 == 0,
                "moq": [100, 200, 500, 1000][i % 4],
                "unit_price_usd": unit_price,
                "lead_time_days": [5, 7, 10, 14][i % 4],
                "platform": ["1688", "Yiwu Market", "Alibaba"][i % 3],
            }
        )

    return {
        "status": "success",
        "data": {
            "query": keyword,
            "category_id": category_id,
            "currency": "USD",
            "total_results": len(items),
            "items": items,
        },
    }
