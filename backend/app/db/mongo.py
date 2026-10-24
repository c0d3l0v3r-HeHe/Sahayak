"""MongoDB client, collection accessors and index creation."""

from dataclasses import dataclass

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import Settings


@dataclass
class Database:
    client: AsyncMongoClient
    db: AsyncDatabase

    @property
    def users(self) -> AsyncCollection:
        return self.db["users"]

    @property
    def flows(self) -> AsyncCollection:
        return self.db["flows"]

    @property
    def tasks(self) -> AsyncCollection:
        return self.db["tasks"]

    @property
    def handoffs(self) -> AsyncCollection:
        return self.db["handoffs"]

    @property
    def jobs(self) -> AsyncCollection:
        return self.db["jobs"]

    async def close(self) -> None:
        await self.client.close()


def connect(settings: Settings) -> Database:
    client: AsyncMongoClient = AsyncMongoClient(
        settings.mongo_url, tz_aware=True, serverSelectionTimeoutMS=5000
    )
    return Database(client=client, db=client[settings.mongo_db])


async def ensure_indexes(database: Database) -> None:
    await database.users.create_index("device_id", unique=True)
    await database.tasks.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await database.tasks.create_index([("status", ASCENDING), ("flow_id", ASCENDING)])
    # TTL: documents disappear once `expires_at` is in the past.
    await database.tasks.create_index("expires_at", expireAfterSeconds=0, name="tasks_ttl")
    await database.handoffs.create_index("expires_at", expireAfterSeconds=0, name="handoffs_ttl")
    await database.handoffs.create_index("task_id")
    await database.jobs.create_index([("state", ASCENDING), ("run_after", ASCENDING)])
    await database.jobs.create_index("task_id")
    await database.jobs.create_index("expires_at", expireAfterSeconds=0, name="jobs_ttl")
