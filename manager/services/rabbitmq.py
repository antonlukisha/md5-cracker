import orjson
import time
import threading
import logging
from typing import Callable
import pika
from datetime import timezone, datetime
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
import config
from services.mongodb import MongoDBManager
from utils import retry

logger = logging.getLogger(__name__)

class RabbitMQManager:
    def __init__(self, mongo_manager: 'MongoDBManager') -> None:
        self.host = config.RABBITMQ_HOST
        self.port = config.RABBITMQ_PORT
        self.user = config.RABBITMQ_USER
        self.password = config.RABBITMQ_PASS
        self.mongo = mongo_manager
        self.connection: pika.BlockingConnection | None = None
        self.channel: BlockingChannel | None = None
        self.result_callback: Callable | None = None
        self.connect()
        self.start_consuming()

    @retry(max_attempts=config.MAX_RETRIES, delay=config.RETRY_DELAY)
    def connect(self) -> None:
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                **config.RABBITMQ_CONNECTION_SETTINGS,
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            self._setup_queues()

            logger.info("Successfully connected to RabbitMQ")
            return

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def _setup_queues(self) -> None:
        if self.channel:
            self.channel.queue_declare(queue="task.queue", durable=True)
            self.channel.queue_declare(queue="result.queue", durable=True)

            self.channel.basic_qos(prefetch_count=10)

    def ensure_connection(self) -> None:
        if not self.connection or self.connection.is_closed:
            logger.warning("RabbitMQ connection lost, reconnecting...")
            self.connect()

    def publish_task(self, task: dict) -> bool:
        try:
            self.ensure_connection()
            if self.channel:
                self.channel.basic_publish(
                    exchange="",
                    routing_key="task.queue",
                    body=orjson.dumps(task),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type="application/json"
                    ),
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to publish task: {e}")
            return False

    def _handle_result(
        self,
        ch: BlockingChannel,
        method: Basic.Deliver,
        _: BasicProperties,
        body: bytes,
    ) -> None:
        try:
            result = orjson.loads(body)
            task_id = result["taskId"]
            request_id = result["requestId"]

            logger.info(
                f"Received result for task {task_id}, status: {result['status']}"
            )

            self.mongo.update_task_status(
                task_id, result["status"], result.get("results", [])
            )

            if result.get("results"):
                self.mongo.add_results_to_request(request_id, result["results"])

            self._check_request_completion(request_id)

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"Error handling result: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def _check_request_completion(self, request_id: str) -> None:
        try:
            total_tasks = self.mongo.tasks.count_documents({"requestId": request_id})
            completed_tasks = self.mongo.tasks.count_documents(
                {"requestId": request_id, "status": {"$in": ["DONE", "ERROR"]}}
            )

            if completed_tasks == total_tasks and total_tasks > 0:
                request = self.mongo.get_request(request_id, use_secondary=False)
                if request:
                    status = "READY"

                    self.mongo.requests.update_one(
                        {"requestId": request_id},
                        {
                            "$set": {
                                "status": status,
                                "completed_at": datetime.now(timezone.utc),
                            }
                        },
                    )
                    logger.info(f"Request {request_id} completed with status {status}")
        except Exception as e:
            logger.error(f"Error checking request completion: {e}")

    def start_consuming(self) -> None:
        def consume() -> None:
            while True:
                try:
                    self.ensure_connection()
                    if self.channel:
                        self.channel.basic_consume(
                            queue="result.queue",
                            on_message_callback=self._handle_result,
                            auto_ack=False,
                        )
                        self.channel.start_consuming()
                except Exception as e:
                    logger.error(f"Consumer error: {e}")
                    time.sleep(5)

        thread = threading.Thread(target=consume, daemon=True)
        thread.start()
        logger.info("Result consumer started")
