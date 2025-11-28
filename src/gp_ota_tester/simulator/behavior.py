"""Behavior controller for simulation modes.

This module provides the BehaviorController that manages simulation
behaviors including error injection, timeout simulation, and response delays.
"""

import asyncio
import logging
import random
from typing import Optional

from .config import BehaviorConfig
from .models import BehaviorMode

logger = logging.getLogger(__name__)


class BehaviorController:
    """Controls simulator behavior modes.

    Manages error injection, timeout simulation, and response delays
    based on configuration.

    Attributes:
        config: Behavior configuration.

    Example:
        >>> controller = BehaviorController(BehaviorConfig(mode=BehaviorMode.ERROR))
        >>> if controller.should_inject_error():
        ...     sw = controller.get_error_code()
    """

    def __init__(self, config: BehaviorConfig):
        """Initialize with behavior configuration.

        Args:
            config: Behavior configuration.
        """
        self.config = config
        self._error_count = 0
        self._timeout_count = 0

    @property
    def mode(self) -> BehaviorMode:
        """Get current behavior mode."""
        return self.config.mode

    @property
    def error_count(self) -> int:
        """Get number of injected errors."""
        return self._error_count

    @property
    def timeout_count(self) -> int:
        """Get number of simulated timeouts."""
        return self._timeout_count

    def should_inject_error(self) -> bool:
        """Determine if error should be injected.

        Returns:
            True if error should be injected based on configured rate.

        Example:
            >>> if controller.should_inject_error():
            ...     return controller.get_error_code()
        """
        if self.config.mode != BehaviorMode.ERROR:
            return False

        if self.config.error_rate <= 0:
            return False

        inject = random.random() < self.config.error_rate
        if inject:
            self._error_count += 1
            logger.debug(f"Injecting error (count: {self._error_count})")

        return inject

    def get_error_code(self) -> str:
        """Get error status word to inject.

        Returns:
            Random error SW from configured list.

        Example:
            >>> sw = controller.get_error_code()
            >>> print(sw)  # e.g., "6A82"
        """
        if not self.config.error_codes:
            return "6F00"  # Unknown error

        return random.choice(self.config.error_codes)

    def should_timeout(self) -> bool:
        """Determine if timeout should be simulated.

        Returns:
            True if timeout should be simulated based on configured probability.

        Example:
            >>> if controller.should_timeout():
            ...     delay = controller.get_timeout_delay()
            ...     await asyncio.sleep(delay)
        """
        if self.config.mode != BehaviorMode.TIMEOUT:
            return False

        if self.config.timeout_probability <= 0:
            return False

        timeout = random.random() < self.config.timeout_probability
        if timeout:
            self._timeout_count += 1
            logger.debug(f"Simulating timeout (count: {self._timeout_count})")

        return timeout

    def get_timeout_delay(self) -> float:
        """Get delay in seconds for timeout simulation.

        Returns:
            Delay duration in seconds within configured range.

        Example:
            >>> delay = controller.get_timeout_delay()
            >>> await asyncio.sleep(delay)
        """
        min_delay = self.config.timeout_delay_min_ms / 1000.0
        max_delay = self.config.timeout_delay_max_ms / 1000.0
        return random.uniform(min_delay, max_delay)

    def get_response_delay(self) -> float:
        """Get normal response delay in seconds.

        Returns:
            Configured response delay in seconds.

        Example:
            >>> await asyncio.sleep(controller.get_response_delay())
        """
        return self.config.response_delay_ms / 1000.0

    async def apply_delay(self) -> None:
        """Apply configured response delay.

        Sleeps for the configured response delay duration.
        """
        delay = self.get_response_delay()
        if delay > 0:
            await asyncio.sleep(delay)

    async def maybe_inject_behavior(self) -> Optional[str]:
        """Check and apply behavior modifications.

        Checks if error or timeout should be applied, and applies
        appropriate behavior modification.

        Returns:
            Error SW if error should be injected, None otherwise.
            Also applies timeout delay if applicable.

        Example:
            >>> error_sw = await controller.maybe_inject_behavior()
            >>> if error_sw:
            ...     return bytes.fromhex(error_sw)
        """
        # Check for timeout simulation first
        if self.should_timeout():
            delay = self.get_timeout_delay()
            logger.info(f"Simulating timeout: {delay:.2f}s delay")
            await asyncio.sleep(delay)

        # Check for error injection
        if self.should_inject_error():
            error_sw = self.get_error_code()
            logger.info(f"Injecting error: SW={error_sw}")
            return error_sw

        # Apply normal response delay
        await self.apply_delay()

        return None

    def reset_stats(self) -> None:
        """Reset error and timeout counts."""
        self._error_count = 0
        self._timeout_count = 0
        logger.debug("Behavior stats reset")
