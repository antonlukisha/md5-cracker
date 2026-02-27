from datetime import datetime, timezone
import uuid
from typing import Any


class CrackRequest:
    def __init__(self, target_hash: str, max_length: int) -> None:
        self.request_id = str(uuid.uuid4())
        self.hash = target_hash.lower()
        self.max_length = max_length
        self.status = "IN_PROGRESS"
        self.results: list[str] = []
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "hash": self.hash,
            "maxLength": self.max_length,
            "status": self.status,
            "results": self.results,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrackRequest":
        request = cls(data["hash"], data["maxLength"])
        request.request_id = data["requestId"]
        request.status = data["status"]
        request.results = data.get("results", [])
        request.created_at = data.get("created_at", datetime.now(timezone.utc))
        request.updated_at = data.get("updated_at", datetime.now(timezone.utc))
        return request


class Task:
    def __init__(
        self,
        request_id: str,
        start_index: int,
        count: int,
        target_hash: str,
        max_length: int,
    ) -> None:
        self.task_id = str(uuid.uuid4())
        self.request_id = request_id
        self.start_index = start_index
        self.count = count
        self.target_hash = target_hash.lower()
        self.max_length = max_length
        self.status = "PENDING"
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self.results: list[str] = []
        self.needs_retry = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "requestId": self.request_id,
            "startIndex": self.start_index,
            "count": self.count,
            "targetHash": self.target_hash,
            "maxLength": self.max_length,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "results": self.results,
            "needs_retry": self.needs_retry,
        }

    def to_message(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "requestId": self.request_id,
            "startIndex": self.start_index,
            "count": self.count,
            "targetHash": self.target_hash,
            "maxLength": self.max_length,
        }

    def mark_done(self, results: list[str]) -> None:
        self.status = "DONE"
        self.completed_at = datetime.now(timezone.utc)
        self.results = results

    def mark_error(self) -> None:
        self.status = "ERROR"
        self.completed_at = datetime.now(timezone.utc)

    def mark_queued(self) -> None:
        self.status = "QUEUED"
        self.needs_retry = True
