from typing import Any
from dataclasses import dataclass, asdict
import json


@dataclass
class Task:
    taskId: str
    requestId: str
    startIndex: int
    count: int
    targetHash: str
    maxLength: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            taskId=data["taskId"],
            requestId=data["requestId"],
            startIndex=data["startIndex"],
            count=data["count"],
            targetHash=data["targetHash"],
            maxLength=data["maxLength"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Task":
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskResult:
    taskId: str
    requestId: str
    results: list[str]
    status: str

    def to_dict(self) -> dict[str, Any]:
        result = {
            "taskId": self.taskId,
            "requestId": self.requestId,
            "results": self.results,
            "status": self.status,
        }
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
