"""Small JPEG screenshots on a local (shared) volume, grouped per task."""

import re
import shutil
import time
from pathlib import Path

from app.models.common import new_id

_ID = re.compile(r"^[a-f0-9]{32}$")


class ScreenStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def save(self, task_id: str, data: bytes) -> str:
        shot_id = new_id()
        folder = self.root / task_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{shot_id}.jpg").write_bytes(data)
        return shot_id

    def path(self, task_id: str, shot_id: str) -> Path | None:
        if not (_ID.match(task_id) and _ID.match(shot_id)):
            return None
        p = self.root / task_id / f"{shot_id}.jpg"
        return p if p.is_file() else None

    def delete_task(self, task_id: str) -> None:
        if _ID.match(task_id):
            shutil.rmtree(self.root / task_id, ignore_errors=True)

    def sweep(self, live_task_ids: set[str], max_age_s: float) -> int:
        """Delete folders of tasks that no longer exist (TTL-expired) or are too old."""
        if not self.root.exists():
            return 0
        removed = 0
        now = time.time()
        for folder in self.root.iterdir():
            if not folder.is_dir():
                continue
            too_old = now - folder.stat().st_mtime > max_age_s
            if folder.name not in live_task_ids or too_old:
                shutil.rmtree(folder, ignore_errors=True)
                removed += 1
        return removed
