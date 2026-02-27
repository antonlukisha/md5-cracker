import time
import logging
from datetime import datetime, timezone
from pymongo import MongoClient, WriteConcern
from pymongo.read_preferences import ReadPreference
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.collection import Collection
import config
from utils.decorators import retry

logger = logging.getLogger(__name__)

class MongoDBManager:
    def __init__(self) -> None:
        self.host = config.MONGO_HOST
        self.port = config.MONGO_PORT
        self.client: MongoClient | None = None
        self.db = None
        self.requests: Collection | None = None
        self.tasks: Collection | None = None
        self.connect()

    @retry(max_attempts=config.MAX_RETRIES, delay=config.RETRY_DELAY)
    def connect(self) -> None:
        try:
            self.client = MongoClient(
                host=self.host, port=self.port, **config.MONGO_CONNECTION_SETTINGS
            )
            self.client.admin.command("ping")

            self.db = self.client.md5_cracker

            self.requests = self.db.requests # type: ignore[attr-defined]
            self.tasks = self.db.tasks # type: ignore[attr-defined]

            if self.requests is not None:
                self.requests = self.requests.with_options(
                    write_concern=WriteConcern(w="majority", wtimeout=5000)
                )

            if self.tasks is not None:
                self.tasks = self.tasks.with_options(
                    write_concern=WriteConcern(w="majority", wtimeout=5000)
                )

            self._create_indexes()

            logger.info("Successfully connected to MongoDB")
            return

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _create_indexes(self) -> None:
        if self.requests is not None:
            self.requests.create_index("requestId", unique=True)
            self.requests.create_index("status")
            self.requests.create_index("created_at")

        if self.tasks is not None:
            self.tasks.create_index("taskId", unique=True)
            self.tasks.create_index("requestId")
            self.tasks.create_index("status")
            self.tasks.create_index("needs_retry")

    def ensure_connection(self) -> None:
        try:
            if self.client:
                self.client.admin.command("ping")
        except Exception as e:
            logger.warning(f"MongoDB connection lost: {e}, reconnecting...")
            self.connect()

    @retry(max_attempts=3)
    def insert_request(self, request_data: dict) -> str:
        if self.requests is not None:
            result = self.requests.insert_one(request_data)
            return str(result.inserted_id)
        raise RuntimeError("MongoDB not initialized")

    @retry(max_attempts=3)
    def insert_tasks(self, tasks: list[dict]) -> list[str]:
        if self.tasks is not None:
            result = self.tasks.insert_many(tasks)
            return [str(i) for i in result.inserted_ids]
        raise RuntimeError("MongoDB not initialized")

    def get_request(self, request_id: str, use_secondary: bool = True) -> Collection | None:
        if self.requests is None:
            raise RuntimeError("MongoDB not initialized")

        collection = self.requests
        if use_secondary:
            collection = collection.with_options(
                read_preference=ReadPreference.SECONDARY
            )

        return collection.find_one({"requestId": request_id})

    def update_task_status(
        self, task_id: str, status: str, results: list[str] | None = None
    ) -> None:
        if self.tasks is None:
            raise RuntimeError("MongoDB not initialized")

        update_data = {"status": status, "completed_at": datetime.now(timezone.utc)}
        if results:
            update_data["results"] = results

        self.tasks.update_one({"taskId": task_id}, {"$set": update_data})

    def add_results_to_request(self, request_id: str, results: list[str]) -> None:
        if self.requests is None:
            raise RuntimeError("MongoDB not initialized")

        self.requests.update_one(
            {"requestId": request_id}, {"$push": {"results": {"$each": results}}}
        )

    def get_failed_tasks(self) -> list[dict]:
        if self.tasks is None:
            raise RuntimeError("MongoDB not initialized")

        return list(self.tasks.find({"needs_retry": True, "status": "QUEUED"}))

    def mark_task_retried(self, task_id: str) -> None:
        if self.tasks is None:
            raise RuntimeError("MongoDB not initialized")

        self.tasks.update_one({"taskId": task_id}, {"$set": {"needs_retry": False}})
