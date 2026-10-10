"""پاکسازی ماهانه: حذف کانفیگ‌های غیرفعال (بدون تست سالمِ ۳۰ روز اخیر)
به‌همراه کلیدهای posted/iran وابسته و بازسازی فهرست سالم."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.storage import KVStorage  # noqa: E402

STALE_DAYS = 30


async def main() -> None:
    storage = KVStorage(
        os.environ["CLOUDFLARE_API_TOKEN"],
        os.environ["CLOUDFLARE_ACCOUNT_ID"],
        os.environ["KV_NAMESPACE_ID"],
    )
    await storage.open()
    try:
        healthy_removed, healthy_kept = await storage.purge_unhealthy()
        cutoff = time.time() - timedelta(days=STALE_DAYS).total_seconds()
        stale_removed = 0
        for key in await storage.list_keys("config:"):
            record = await storage.get_json(key)
            if not isinstance(record, dict):
                await storage.delete(key)
                stale_removed += 1
                continue
            try:
                tested_at = float(record.get("tested_at", 0))
            except (TypeError, ValueError):
                tested_at = 0
            if tested_at < cutoff:
                cid = key.split(":", 1)[1]
                await storage.delete(key)
                await storage.delete(f"posted:{cid}")
                await storage.delete(f"iran:{cid}")
                stale_removed += 1
        summary = {
            "event": "monthly_purge",
            "stale_days": STALE_DAYS,
            "stale_removed": stale_removed,
            "healthy_removed": healthy_removed,
            "healthy_kept": healthy_kept,
        }
        await storage.append_admin_log({"level": "info", **summary})
        print(json.dumps(summary, ensure_ascii=False))
    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
