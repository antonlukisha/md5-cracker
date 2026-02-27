import os
from typing import Final

# Конфигурация из переменных окружения
MONGO_URI: Final = os.getenv('MONGO_URI', 'mongodb://mongodb-0.mongodb:27017,mongodb-1.mongodb:27017,mongodb-2.mongodb:27017/?replicaSet=rs0')
RABBITMQ_HOST: Final = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_PORT: Final = int(os.getenv('RABBITMQ_PORT', '5672'))
TASK_SIZE: Final = int(os.getenv('TASK_SIZE', '100000'))

# Константы
ALPHABET: Final = 'abcdefghijklmnopqrstuvwxyz0123456789'
ALPHABET_SIZE: Final = len(ALPHABET)

# Настройки подключений
MONGO_CONNECTION_SETTINGS = {
    'replicaSet': 'rs0',
    'readPreference': 'secondaryPreferred',
    'serverSelectionTimeoutMS': 5000,
    'connectTimeoutMS': 5000,
}

RABBITMQ_CONNECTION_SETTINGS = {
    'heartbeat': 600,
    'blocked_connection_timeout': 300,
    'connection_attempts': 3,
    'retry_delay': 2,
}

# Настройки retry
MAX_RETRIES: Final = 5
RETRY_DELAY: Final = 2
RETRY_CHECK_INTERVAL: Final = 30
RETRY_BACKOFF_MULTIPLIER: Final = 1.5

# Лимиты
MAX_HASH_LENGTH: Final = 32
MAX_ALLOWED_LENGTH: Final = 8
MIN_ALLOWED_LENGTH: Final = 1