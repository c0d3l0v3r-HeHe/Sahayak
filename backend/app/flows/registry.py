"""Loads flow definitions from JSON, validates them and caches them in memory."""

import json
import logging
from pathlib import Path

from app.db.mongo import Database
from app.flows.validator import validate_flow
from app.models.flow import FlowDefinition

log = logging.getLogger(__name__)

DEFINITIONS_DIR = Path(__file__).parent / "definitions"


class FlowRegistry:
    def __init__(self, flows: dict[str, FlowDefinition]):
        self._flows = flows

    @classmethod
    def load(cls, directory: Path = DEFINITIONS_DIR) -> "FlowRegistry":
        flows: dict[str, FlowDefinition] = {}
        for path in sorted(directory.glob("*.json")):
            flow = validate_flow(json.loads(path.read_text(encoding="utf-8")))
            flows[flow.id] = flow
        log.info("loaded %d flows: %s", len(flows), ", ".join(flows))
        return cls(flows)

    def get(self, flow_id: str) -> FlowDefinition | None:
        return self._flows.get(flow_id)

    def all(self, enabled_only: bool = True) -> list[FlowDefinition]:
        return [f for f in self._flows.values() if f.enabled or not enabled_only]

    async def sync_to_db(self, db: Database) -> None:
        """Persist definitions so other tools (and humans) can inspect them in Mongo."""
        for flow in self._flows.values():
            doc = flow.model_dump(mode="json", by_alias=True)
            doc["_id"] = doc.pop("id")
            await db.flows.replace_one({"_id": doc["_id"]}, doc, upsert=True)


_registry: FlowRegistry | None = None


def get_registry() -> FlowRegistry:
    global _registry
    if _registry is None:
        _registry = FlowRegistry.load()
    return _registry
