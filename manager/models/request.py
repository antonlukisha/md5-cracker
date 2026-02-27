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
