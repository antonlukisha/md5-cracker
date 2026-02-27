import hashlib
import logging

logger = logging.getLogger(__name__)


class MD5Hasher:
    @staticmethod
    def hash_string(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    @staticmethod
    def check_match(candidate: str, target_hash: str) -> bool:
        return hashlib.md5(candidate.encode()).hexdigest() == target_hash.lower()

    @staticmethod
    def find_matches(strings: list[str], target_hash: str) -> list[str]:
        target = target_hash.lower()
        return [s for s in strings if hashlib.md5(s.encode()).hexdigest() == target]
