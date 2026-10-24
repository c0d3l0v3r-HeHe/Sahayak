"""Prepare a database: indexes (incl. TTL), flow definitions, and optional demo history.

    uv run python -m scripts.seed                          # indexes + flows
    uv run python -m scripts.seed --demo-history DEVICE_ID # + three finished sample tasks

The device id is shown in the app's debug settings logs; any id works for API-only demos.
Sample tasks use the same 7-day TTL as real ones and contain no personal data.
"""

import argparse
import asyncio
from datetime import timedelta

from app.core.config import get_settings
from app.db.mongo import connect, ensure_indexes
from app.flows.registry import get_registry
from app.models.common import new_id, utcnow
from app.models.task import TaskStatus
from app.services.stats import StatsService

SAMPLES = [
    (
        "train_running_status",
        {"train_no": "12301", "date": "today"},
        {
            "en": "12301 RAJDHANI EXPRES: Departed from KANPUR CENTRAL(CNB) at 05:43 (Delay: 00:53).",
            "hi": "ट्रेन 12301 RAJDHANI EXPRES: Departed from KANPUR CENTRAL(CNB) at 05:43 (Delay: 00:53)।",
        },
        {"train_name": "12301 RAJDHANI EXPRES"},
    ),
    (
        "pnr_status",
        {"pnr": "••••••5678"},
        {
            "en": "Train 12951 NDLS TEJAS RAJ. Passenger 1: CNF/B3/45. Chart Not Prepared.",
            "hi": "ट्रेन 12951 NDLS TEJAS RAJ। यात्री 1: CNF/B3/45। Chart Not Prepared।",
        },
        {},
    ),
    (
        "scheme_finder",
        {"age": "67", "gender": "female", "state": "delhi"},
        {
            "en": "1. Delhi Old Age Pension — ₹2,000–₹2,500 a month for senior citizens in Delhi.",
            "hi": "1. Delhi Old Age Pension — ₹2,000–₹2,500 a month for senior citizens in Delhi.",
        },
        {
            "schemes": [
                {
                    "name": "Delhi Old Age Pension",
                    "benefit": "₹2,000–₹2,500 a month",
                    "link": "https://www.myscheme.gov.in/schemes/oaps-delhi",
                }
            ]
        },
    ),
]


async def main(demo_device: str | None) -> None:
    settings = get_settings()
    db = connect(settings)
    await ensure_indexes(db)
    registry = get_registry()
    await registry.sync_to_db(db)
    print(f"indexes ready; {len(registry.all())} flows synced to {settings.mongo_db}")

    if demo_device:
        now = utcnow()
        user = await db.users.find_one_and_update(
            {"device_id": demo_device},
            {
                "$setOnInsert": {"_id": new_id(), "created_at": now, "language": "hi"},
                "$set": {"last_seen_at": now},
            },
            upsert=True,
            return_document=True,
        )
        stats = StatsService(db)
        for i, (flow_id, params, text, data) in enumerate(SAMPLES):
            flow = registry.get(flow_id)
            assert flow is not None
            created = now - timedelta(hours=3 * (i + 1))
            await db.tasks.insert_one(
                {
                    "_id": new_id(),
                    "user_id": user["_id"],
                    "flow_id": flow_id,
                    "flow_version": flow.version,
                    "title": flow.title.model_dump(),
                    "params": params,
                    "lang": "hi",
                    "status": TaskStatus.succeeded.value,
                    "events": [],
                    "event_seq": 0,
                    "result": {"text": text, "data": data},
                    "error": None,
                    "cancel_requested": False,
                    "created_at": created,
                    "started_at": created,
                    "finished_at": created + timedelta(seconds=40),
                    "expires_at": created + timedelta(days=settings.task_ttl_days),
                }
            )
            await stats.record(flow, TaskStatus.succeeded, utcnow() - timedelta(seconds=40))
        print(f"added {len(SAMPLES)} sample tasks for device {demo_device}")
    await db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--demo-history", metavar="DEVICE_ID")
    args = parser.parse_args()
    asyncio.run(main(args.demo_history))
