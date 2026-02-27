import os
from typing import Final

WORKER_ID: Final = os.getenv("WORKER_ID", f"worker-{os.getpid()}")

ALPHABET: Final = "abcdefghijklmnopqrstuvwxyz0123456789"
ALPHABET_SIZE: Final = len(ALPHABET)

RABBITMQ_HOST: Final = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT: Final = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER: Final = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS: Final = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_CONNECTION_SETTINGS = {"heartbeat": 600, "blocked_connection_timeout": 300}

METRICS_PORT: Final = int(os.getenv("METRICS_PORT", "8000"))

MAX_RETRIES: Final = 5
RETRY_DELAY: Final = 2
PROGRESS_REPORT_INTERVAL: Final = 10000
