from prometheus_client import Counter, Gauge, start_http_server
import logging
import config

logger = logging.getLogger(__name__)

tasks_processed = Counter(
    "worker_tasks_processed_total", "Total tasks processed", ["status"]
)

tasks_in_progress = Gauge("worker_tasks_in_progress", "Tasks currently in progress")

combinations_speed = Gauge(
    "worker_combinations_per_second", "Combinations processed per second"
)

memory_usage = Gauge("worker_memory_usage_bytes", "Memory usage in bytes")


def start_metrics_server() -> None:
    try:
        start_http_server(config.METRICS_PORT)
        logger.info(f"Metrics server started on port {config.METRICS_PORT}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")


def inc_tasks_processed(status: str = "success") -> None:
    tasks_processed.labels(status=status).inc()


def inc_tasks_in_progress() -> None:
    tasks_in_progress.inc()


def dec_tasks_in_progress() -> None:
    tasks_in_progress.dec()


def update_combinations_speed(speed: float) -> None:
    combinations_speed.set(speed)


def update_memory_usage() -> None:
    from psutil import Process

    process = Process()
    memory_usage.set(process.memory_info().rss)
