from datetime import datetime
from typing import List, Optional, Dict
import uuid


class CrackRequest:
    """
    Модель запроса на взлом хэша
    """

    def __init__(self, target_hash: str, max_length: int):
        self.request_id = str(uuid.uuid4())
        self.hash = target_hash.lower()
        self.max_length = max_length
        self.status = 'IN_PROGRESS'
        self.results: List[str] = []
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict:
        """Конвертация в словарь для MongoDB"""
        return {
            'requestId': self.request_id,
            'hash': self.hash,
            'maxLength': self.max_length,
            'status': self.status,
            'results': self.results,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CrackRequest':
        """Создание из словаря MongoDB"""
        request = cls(data['hash'], data['maxLength'])
        request.request_id = data['requestId']
        request.status = data['status']
        request.results = data.get('results', [])
        request.created_at = data.get('created_at', datetime.utcnow())
        request.updated_at = data.get('updated_at', datetime.utcnow())
        return request


class Task:
    """
    Модель задачи для воркера
    """

    def __init__(self, request_id: str, start_index: int, count: int,
                 target_hash: str, max_length: int):
        self.task_id = str(uuid.uuid4())
        self.request_id = request_id
        self.start_index = start_index
        self.count = count
        self.target_hash = target_hash.lower()
        self.max_length = max_length
        self.status = 'PENDING'
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.results: List[str] = []
        self.needs_retry = False

    def to_dict(self) -> Dict:
        """Конвертация в словарь для MongoDB"""
        return {
            'taskId': self.task_id,
            'requestId': self.request_id,
            'startIndex': self.start_index,
            'count': self.count,
            'targetHash': self.target_hash,
            'maxLength': self.max_length,
            'status': self.status,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'results': self.results,
            'needs_retry': self.needs_retry
        }

    def to_message(self) -> Dict:
        """Конвертация в сообщение для RabbitMQ"""
        return {
            'taskId': self.task_id,
            'requestId': self.request_id,
            'startIndex': self.start_index,
            'count': self.count,
            'targetHash': self.target_hash,
            'maxLength': self.max_length
        }

    def mark_done(self, results: List[str]):
        """Отметить задачу как выполненную"""
        self.status = 'DONE'
        self.completed_at = datetime.utcnow()
        self.results = results

    def mark_error(self):
        """Отметить задачу как ошибочную"""
        self.status = 'ERROR'
        self.completed_at = datetime.utcnow()

    def mark_queued(self):
        """Отметить задачу как поставленную в очередь"""
        self.status = 'QUEUED'
        self.needs_retry = True