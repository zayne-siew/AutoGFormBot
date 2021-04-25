#!/usr/bin/env python3
"""
Abstract base class (ABC) for custom reusable Telegram inline keyboards.

This script serves as an interface for documenting function implementation.

Usage:
    This script should not be used directly, other than its ABC functionalities.

TODO include dependencies
"""

from abc import ABC, abstractmethod
from telegram import InlineKeyboardMarkup
from typing import Any, Optional


class AbstractMarkup(ABC):
    """AbstractMarkup class as ABC for custom reusable Telegram inline keyboards."""

    @abstractmethod
    def _format_callback_data(self, data: str) -> str:
        """Prepend the callback data with the signature."""
        pass

    @abstractmethod
    def _is_option(self, option: str) -> bool:
        """Checks if the parsed option is stored as a valid option."""
        pass

    @abstractmethod
    def init(self, *args: Any, **kwargs: Any) -> InlineKeyboardMarkup:
        """Initialises the markup with parsed arguments."""
        pass

    @abstractmethod
    def verify(self, callback_data: str, option: Optional[str] = None) -> bool:
        """Verifies if the callback data came from selecting the option in the markup instance."""
        pass

    @abstractmethod
    def get_data(self, callback_data: str) -> Optional[str]:
        """Returns the unformatted data from the formatted callback data."""
        pass


if __name__ == '__main__':
    pass
