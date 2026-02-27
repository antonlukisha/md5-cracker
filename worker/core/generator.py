import logging
from typing import Generator

logger = logging.getLogger(__name__)


class StringGenerator:
    def __init__(self, alphabet: str) -> None:
        self.alphabet = alphabet
        self.alphabet_size = len(alphabet)

    def index_to_string(self, index: int, max_length: int) -> str:
        length = 1
        total_prev = 0

        while length <= max_length:
            count = self.alphabet_size**length
            if index < total_prev + count:
                break
            total_prev += count
            length += 1

        if length > max_length:
            raise ValueError(
                f"Index {index} exceeds maximum combinations for length {max_length}"
            )

        remainder = index - total_prev

        chars: list[str] = []
        for _ in range(length):
            remainder, char_index = divmod(remainder, self.alphabet_size)
            chars.append(self.alphabet[char_index])

        return "".join(reversed(chars))

    def generate_range(self, start_index: int, count: int, max_length: int) -> Generator:
        for i in range(count):
            yield self.index_to_string(start_index + i, max_length)
