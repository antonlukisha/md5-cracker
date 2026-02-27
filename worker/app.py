import logging
import sys
import orjson
import config
from services import RabbitMQClient, TaskProcessor
from utils.metrics import start_metrics_server, update_memory_usage
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
from utils import SignalHandler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WorkerApp:
    def __init__(self) -> None:
        self.worker_id = config.WORKER_ID
        logger.info(f"Initializing worker {self.worker_id}")

        self.processor = TaskProcessor(self.worker_id)
        self.rabbitmq = RabbitMQClient()

        start_metrics_server()
        update_memory_usage()

        self.signal_handler = SignalHandler(self.shutdown)

        logger.info(f"Worker {self.worker_id} initialized successfully")

    def shutdown(self) -> None:
        logger.info("Initiating graceful shutdown...")
        self.rabbitmq.stop_consuming()
        self.rabbitmq.close()

        logger.info("All resources released")

    def _callback(
        self,
        ch: BlockingChannel,
        method: Basic.Deliver,
        _: BasicProperties,
        body: bytes,
    ) -> None:
        if not self.signal_handler.is_running():
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        try:
            task_data = orjson.loads(body)
            logger.info(f"Worker {self.worker_id} received task {task_data['taskId']}")

            update_memory_usage()

            result = self.processor.process_task(task_data)

            if result is None:
                logger.info(f"Worker stopping, requeuing task {task_data['taskId']}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                return

            if self.rabbitmq.publish_result(result.to_dict()):
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"Task {task_data['taskId']} completed and acknowledged")

            else:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                logger.error(f"Failed to send result for task {task_data['taskId']}")

        except orjson.JSONDecodeError as e:
            logger.error(f"Failed to decode task JSON: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        except Exception as e:
            logger.error(f"Unexpected error in callback: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def run(self) -> int:
        logger.info(f"Worker {self.worker_id} started, waiting for tasks...")
        try:
            self.rabbitmq.consume_tasks(self._callback)
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            return 1

        return 0


def main() -> int:
    app = WorkerApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
