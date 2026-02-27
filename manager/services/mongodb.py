import json
import time
import threading
import logging
from typing import Dict, Callable, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

import config

logger = logging.getLogger(__name__)


class RabbitMQManager:
    """
    Менеджер для работы с RabbitMQ с поддержкой отказоустойчивости
    """

    def __init__(self, host: str, port: int, mongo_manager):
        self.host = host
        self.port = port
        self.mongo = mongo_manager
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None
        self.result_callback: Optional[Callable] = None
        self.reconnect()
        self.start_consuming()

    def reconnect(self):
        """Переподключение к RabbitMQ"""
        for attempt in range(config.MAX_RETRIES):
            try:
                credentials = pika.PlainCredentials('guest', 'guest')
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=credentials,
                    **config.RABBITMQ_CONNECTION_SETTINGS
                )

                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()

                # Настройка очередей
                self._setup_queues()

                logger.info("Successfully connected to RabbitMQ")
                return

            except Exception as e:
                if attempt < config.MAX_RETRIES - 1:
                    wait_time = config.RETRY_DELAY * (attempt + 1)
                    logger.warning(f"RabbitMQ connection attempt {attempt + 1} failed: {e}")
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Failed to connect to RabbitMQ after all retries")
                    raise

    def _setup_queues(self):
        """Настройка очередей"""
        if self.channel:
            # Декларируем очереди
            self.channel.queue_declare(queue='task.queue', durable=True)
            self.channel.queue_declare(queue='result.queue', durable=True)

            # Настройка QoS
            self.channel.basic_qos(prefetch_count=10)

    def ensure_connection(self):
        """Проверка и восстановление подключения"""
        if not self.connection or self.connection.is_closed:
            logger.warning("RabbitMQ connection lost, reconnecting...")
            self.reconnect()

    def publish_task(self, task: Dict) -> bool:
        """Публикация задачи в очередь"""
        try:
            self.ensure_connection()
            if self.channel:
                self.channel.basic_publish(
                    exchange='',
                    routing_key='task.queue',
                    body=json.dumps(task),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Persistent message
                        content_type='application/json'
                    )
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to publish task: {e}")
            return False

    def _handle_result(self, ch: BlockingChannel, method: Basic.Deliver,
                       properties: BasicProperties, body: bytes):
        """Обработка результата от воркера"""
        try:
            result = json.loads(body)
            task_id = result['taskId']
            request_id = result['requestId']

            logger.info(f"Received result for task {task_id}, status: {result['status']}")

            # Обновляем задачу в MongoDB
            self.mongo.update_task_status(
                task_id,
                result['status'],
                result.get('results', [])
            )

            # Если есть результаты, добавляем их к запросу
            if result.get('results'):
                self.mongo.add_results_to_request(request_id, result['results'])

            # Проверяем, все ли задачи выполнены
            self._check_request_completion(request_id)

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"Error handling result: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def _check_request_completion(self, request_id: str):
        """Проверка завершения всех задач запроса"""
        try:
            total_tasks = self.mongo.tasks.count_documents({'requestId': request_id})
            completed_tasks = self.mongo.tasks.count_documents({
                'requestId': request_id,
                'status': {'$in': ['DONE', 'ERROR']}
            })

            if completed_tasks == total_tasks and total_tasks > 0:
                # Все задачи выполнены
                request = self.mongo.get_request(request_id, use_secondary=False)
                if request:
                    has_results = len(request.get('results', [])) > 0
                    status = 'READY'

                    self.mongo.requests.update_one(
                        {'requestId': request_id},
                        {'$set': {
                            'status': status,
                            'completed_at': datetime.utcnow()
                        }}
                    )
                    logger.info(f"Request {request_id} completed with status {status}")
        except Exception as e:
            logger.error(f"Error checking request completion: {e}")

    def start_consuming(self):
        """Запуск consumer в отдельном потоке"""

        def consume():
            while True:
                try:
                    self.ensure_connection()
                    if self.channel:
                        self.channel.basic_consume(
                            queue='result.queue',
                            on_message_callback=self._handle_result,
                            auto_ack=False
                        )
                        self.channel.start_consuming()
                except Exception as e:
                    logger.error(f"Consumer error: {e}")
                    time.sleep(5)

        thread = threading.Thread(target=consume, daemon=True)
        thread.start()
        logger.info("Result consumer started")