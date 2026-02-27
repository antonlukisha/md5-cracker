import signal
import sys
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


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
