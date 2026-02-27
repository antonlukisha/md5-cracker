from typing import Callable
import orjson
import logging
import pika
from pika.adapters.blocking_connection import BlockingChannel
import config
from utils import retry

logger = logging.getLogger(__name__)


class RabbitMQClient:
    def __init__(self) -> None:
        self.host = config.RABBITMQ_HOST
        self.port = config.RABBITMQ_PORT
        self.user = config.RABBITMQ_USER
        self.password = config.RABBITMQ_PASS
        self.connection: pika.BlockingConnection | None = None
        self.channel: BlockingChannel | None = None
        self.connect()

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

            self.channel.basic_qos(prefetch_count=1)

    def ensure_connection(self) -> None:
        if not self.connection or self.connection.is_closed:
            logger.warning("RabbitMQ connection lost, reconnecting...")
            self.connect()

    def publish_result(self, result: dict) -> bool:
        try:
            self.ensure_connection()
            if self.channel:
                self.channel.basic_publish(
                    exchange="",
                    routing_key="result.queue",
                    body=orjson.dumps(result),
                    properties=pika.BasicProperties(
                        delivery_mode=2, content_type="application/json"
                    ),
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to publish task: {e}")
            return False

    def consume_tasks(self, callback: Callable) -> None:
        try:
            self.ensure_connection()
            if self.channel:
                self.channel.basic_consume(
                    queue="task.queue", on_message_callback=callback, auto_ack=False
                )
                logger.info("Started consuming tasks from task.queue")
                self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Error in consume_tasks: {e}")
            raise

    def stop_consuming(self) -> None:
        if self.channel:
            self.channel.stop_consuming()
            logger.info("Stopped consuming tasks")

    def close(self) -> None:
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ connection closed")
