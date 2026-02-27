import time
import logging
import threading
from threading import Thread
import config
from services.rabbitmq import RabbitMQManager
from services.mongodb import MongoDBManager

logger = logging.getLogger(__name__)


class TaskRetryManager:
    def __init__(self, mongo: 'MongoDBManager', rabbitmq: 'RabbitMQManager') -> None:
        self.mongo = mongo
        self.rabbitmq = rabbitmq
        self.running = True
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Task retry manager started")

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Task retry manager stopped")

    def _run(self) -> None:
        while self.running:
            try:
                self._process_failed_tasks()
                time.sleep(config.RETRY_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Error in retry mechanism: {e}")
                time.sleep(60)

    def _process_failed_tasks(self) -> None:
        failed_tasks = self.mongo.get_failed_tasks()

        for task in failed_tasks:
            task_message = {
                "taskId": task["taskId"],
                "requestId": task["requestId"],
                "startIndex": task["startIndex"],
                "count": task["count"],
                "targetHash": task["targetHash"],
                "maxLength": task["maxLength"],
            }

            if self.rabbitmq.publish_task(task_message):
                self.mongo.mark_task_retried(task["taskId"])
                logger.info(f"Successfully retried task {task['taskId']}")
            else:
                logger.warning(f"Failed to retry task {task['taskId']}")
