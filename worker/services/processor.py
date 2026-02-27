import time
import logging
from typing import Any
from models import Task, TaskResult
from core import StringGenerator, MD5Hasher
from utils.metrics import (
    update_combinations_speed,
    inc_tasks_in_progress,
    inc_tasks_processed,
    dec_tasks_in_progress,
)
import config

logger = logging.getLogger(__name__)


class TaskProcessor:
    def __init__(self, worker_id: str) -> None:
        self.worker_id = worker_id
        self.generator = StringGenerator(config.ALPHABET)
        self.hasher = MD5Hasher()
        self.current_task: Task | None = None
        self.combinations_processed = 0

    def _process_combinations(self, task: Task) -> list[str]:
        results: list[str] = []
        processed = 0

        for i, candidate in enumerate(
            self.generator.generate_range(task.startIndex, task.count, task.maxLength)
        ):

            if self.hasher.check_match(candidate, task.targetHash):
                logger.info(f"Found match: '{candidate}' for task {task.taskId}")
                results.append(candidate)

            processed += 1
            self.combinations_processed += 1

            if (i + 1) % config.PROGRESS_REPORT_INTERVAL == 0:
                logger.debug(
                    f"Task {task.taskId}: processed {i + 1}/{task.count} combinations"
                )
                update_combinations_speed(self.combinations_processed / time.time())

        return results

    def process_task(self, task_data: dict[str, Any]) -> TaskResult | None:
        task_start_time = time.time()
        task = Task.from_dict(task_data)
        self.current_task = task
        try:
            inc_tasks_in_progress()

            logger.info(
                f"Worker {self.worker_id} processing task {task.taskId}: "
                f"start={task.startIndex}, count={task.count}"
            )

            results = self._process_combinations(task)

            processing_time = time.time() - task_start_time
            status = "DONE"

            result = TaskResult(
                taskId=task.taskId,
                requestId=task.requestId,
                results=results,
                status=status,
            )

            inc_tasks_processed("success" if status == "DONE" else "interrupted")

            logger.info(
                f"Task {task.taskId} completed with {len(results)} matches "
                f"in {processing_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Error processing task {task.taskId}: {e}")
            inc_tasks_processed("error")

            return TaskResult(
                taskId=task.taskId, requestId=task.requestId, results=[], status="ERROR"
            )

        finally:
            dec_tasks_in_progress()
            self.current_task = None
