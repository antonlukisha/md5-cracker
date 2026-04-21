import os
from typing import Final

from decouple import config

WORKER_ID: Final = config("WORKER_ID", default=f"worker-{os.getpid()}")

LOGGER_LEVEL: Final = config("LOGGER_LEVEL", default="INFO")

ALPHABET: Final = "abcdefghijklmnopqrstuvwxyz0123456789"
ALPHABET_SIZE: Final = len(ALPHABET)

RABBITMQ_HOST: Final = config("RABBITMQ_HOST", default="rabbitmq")
RABBITMQ_PORT: Final = int(config("RABBITMQ_PORT", default="5672"))
RABBITMQ_USER: Final = config("RABBITMQ_USER", default="guest")
RABBITMQ_PASS: Final = config("RABBITMQ_PASS", default="guest")
RABBITMQ_CONNECTION_SETTINGS = {"heartbeat": 600, "blocked_connection_timeout": 300}

METRICS_PORT: Final = int(config("METRICS_PORT", default="7077"))

MAX_RETRIES: Final = 5
RETRY_DELAY: Final = 2
PROGRESS_REPORT_INTERVAL: Final = 10000
