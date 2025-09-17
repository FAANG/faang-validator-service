import hashlib
import os
from typing import Dict, Any
from celery import states
from celery_app import celery_app


def _status(stage: int, msg: str) -> Dict[str, Any]:
    return {"stage": stage, "msg": msg}


@celery_app.task(bind=True)
def process_file(self, path: str, filename: str, total: int) -> Dict[str, Any]:
    """
    """
    try:
        self.update_state(state="PROGRESS", meta=_status(1, f"Preparing to parse: {filename}"))
        self.update_state(state="PROGRESS", meta=_status(2, "Scanning file structure..."))

        self.update_state(state="PROGRESS", meta=_status(3, "Computing checksum & stats..."))
        sha, lines = hashlib.sha256(), 0
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                sha.update(chunk)
                lines += chunk.count(b"\n")

        self.update_state(state="PROGRESS", meta=_status(4, "Post-processing..."))

        result = {
            "filename": filename,
            "size": total,
            "lines_estimate": int(lines),
            "sha256": sha.hexdigest(),
        }
        return result
    except Exception as e:
        self.update_state(state=states.FAILURE, meta={"detail": str(e)})
        raise
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
