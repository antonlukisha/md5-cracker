import os
from typing import Final

TASK_SIZE: Final = int(os.getenv("TASK_SIZE", "100000"))

ALPHABET: Final = "abcdefghijklmnopqrstuvwxyz0123456789"
ALPHABET_SIZE: Final = len(ALPHABET)

MONGO_HOST: Final = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT: Final = int(os.getenv("MONGO_PORT", "27017"))
MONGO_CONNECTION_SETTINGS = {
    "replicaSet": "rs0",
    "readPreference": "secondaryPreferred",
    "serverSelectionTimeoutMS": 5000,
    "connectTimeoutMS": 5000,
}

RABBITMQ_HOST: Final = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT: Final = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER: Final = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS: Final = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_CONNECTION_SETTINGS = {
    "heartbeat": 600,
    "blocked_connection_timeout": 300
}

MAX_RETRIES: Final = 5
RETRY_DELAY: Final = 2
RETRY_CHECK_INTERVAL: Final = 30
RETRY_BACKOFF_MULTIPLIER: Final = 1.5

MAX_HASH_LENGTH: Final = 32
MAX_ALLOWED_LENGTH: Final = 8
MIN_ALLOWED_LENGTH: Final = 1
