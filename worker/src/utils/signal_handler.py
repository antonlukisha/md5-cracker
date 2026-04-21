import signal
import sys
from typing import Any, Callable

from src.core.logging import get_logger

logger = get_logger("signal_handler")


class SignalHandler:
    def __init__(self, shutdown_callback: Callable[[], None]) -> None:
        self.shutdown_callback = shutdown_callback
        self.running = True

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        logger.info("Signal handlers registered (SIGTERM, SIGINT)")

    def _handle_signal(self, signum: int, _: Any) -> None:
        signal_name = signal.Signals(signum).name
        logger.info(f"Received signal {signal_name}, initiating graceful shutdown...")

        self.running = False

        logger.info("Shutdown complete")
        sys.exit(0)

    def is_running(self) -> bool:
        return self.running
