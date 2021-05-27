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
from typing import Any, Mapping, Optional, Tuple, Union


class AbstractMarkup(ABC):
    """AbstractMarkup class as ABC for custom reusable Telegram inline keyboards."""

    @classmethod
    @abstractmethod
    def get_pattern(cls, *datas: str) -> str:
        """Gets the pattern regex for matching in ConversationHandler."""
        pass

    @abstractmethod
    def get_markup(self, *option_rows: Union[str, Tuple[str, ...]], option_datas: Optional[Mapping[str, str]] = None) \
            -> InlineKeyboardMarkup:
        """Initialises the markup with parsed arguments."""
        pass


class AbstractOptionMarkup(ABC):
    """AbstractOptionMarkup class as ABC for custom reusable option menus as Telegram inline keyboards."""

    @abstractmethod
    def _is_option(self, key: str, option: str) -> bool:
        """Verify if the option parsed is defined."""
        pass

    @abstractmethod
    def perform_action(self, option: str) -> Any:
        """Perform action according to the callback data."""
        pass


if __name__ == '__main__':
    pass
