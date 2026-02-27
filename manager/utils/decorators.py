from typing import List, Dict
import config


def calculate_total_combinations(max_length: int) -> int:
    """
    Вычисление общего количества комбинаций для заданной максимальной длины
    """
    total = 0
    for length in range(1, max_length + 1):
        total += config.ALPHABET_SIZE ** length
    return total


def create_task_partitions(total_combinations: int, task_size: int) -> List[Dict]:
    """
    Создание партиций задач для распределения между воркерами
    """
    if task_size <= 0:
        raise ValueError("task_size must be positive")

    partitions = []
    start = 0

    while start < total_combinations:
        count = min(task_size, total_combinations - start)
        partitions.append({
            'start_index': start,
            'count': count
        })
        start += count

    return partitions


def validate_hash(target_hash: str) -> bool:
    """
    Проверка валидности MD5 хэша
    """
    if len(target_hash) != config.MAX_HASH_LENGTH:
        return False
    return all(c in '0123456789abcdef' for c in target_hash.lower())


def validate_max_length(max_length: int) -> bool:
    """
    Проверка допустимой длины
    """
    return (isinstance(max_length, int) and
            config.MIN_ALLOWED_LENGTH <= max_length <= config.MAX_ALLOWED_LENGTH)