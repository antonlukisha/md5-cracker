from typing import Final

from decouple import config

TASK_SIZE: Final = int(config("TASK_SIZE", default="100000"))

ALPHABET: Final = "abcdefghijklmnopqrstuvwxyz0123456789"
ALPHABET_SIZE: Final = len(ALPHABET)

LOGGER_LEVEL: Final = config("LOGGER_LEVEL", default="INFO")

MONGO_URI: Final = config(
    "MONGO_URI",
    default="mongodb://localhost:27017/md5_cracker?directConnection=true",
)
MONGO_CONNECTION_SETTINGS = {
    "readPreference": "secondaryPreferred",
    "serverSelectionTimeoutMS": 5000,
    "connectTimeoutMS": 5000,
}

RABBITMQ_HOST: Final = config("RABBITMQ_HOST", default="localhost")
RABBITMQ_PORT: Final = int(config("RABBITMQ_PORT", default="5672"))
RABBITMQ_USER: Final = config("RABBITMQ_USER", default="guest")
RABBITMQ_PASS: Final = config("RABBITMQ_PASS", default="guest")
RABBITMQ_CONNECTION_SETTINGS = {"heartbeat": 600, "blocked_connection_timeout": 300}

MAX_RETRIES: Final = 5
RETRY_DELAY: Final = 2
RETRY_CHECK_INTERVAL: Final = 30
RETRY_BACKOFF_MULTIPLIER: Final = 1.5

MAX_HASH_LENGTH: Final = 32
MAX_ALLOWED_LENGTH: Final = 8
MIN_ALLOWED_LENGTH: Final = 1
