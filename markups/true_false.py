#!/usr/bin/env python3
"""
Generic handler for Telegram true/false inline keyboard markups.

A true/false inline keyboard refers to an inline keyboard in Telegram with only two options.
These two options are (usually) opposites and are normally the only two appropriate responses.
This script standardises the initialisation of a generic true/false inline keyboard.

Usage:
    To obtain the pattern regex for CallbackQueryHandlers: TFMarkup.get_pattern()
    To initialise a true/false keyboard markup: markup.get_markup(pos, neg)
    To determine true/false: TFMarkup.confirm(value)

TODO include dependencies
"""

from markups.base import BaseMarkup
import logging
from telegram import InlineKeyboardMarkup
from typing import Optional

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class TFMarkup(BaseMarkup):
    """TFMarkup class for custom true/false inline keyboard.

    Attributes
        _OPTIONS    The options provided on the inline keyboard.
    """

    # Define constants
    _TRUE = "True"
    _FALSE = "False"

    # region Get constants

    @classmethod
    def get_true(cls) -> str:
        """Gets the TRUE constant.

        :return: The TRUE constant.
        """

        return cls._TRUE

    @classmethod
    def get_false(cls) -> str:
        """Gets the FALSE constant.

        :return: The FALSE constant.
        """

        return cls._FALSE

    # endregion Get constants

    @classmethod
    def get_pattern(cls, *_) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        return super().get_pattern(cls._TRUE, cls._FALSE)

    @classmethod
    def confirm(cls, value: str) -> Optional[bool]:
        """Checks if the data is True or False.

        :param value: The value of the callback data parsed.
        :return: True if the value is True, False if the value is False, and None otherwise.
        """

        if value == cls._TRUE:
            return True
        elif value == cls._FALSE:
            return False

    def get_markup(self, pos: Optional[str] = "YES", neg: Optional[str] = "NO") -> InlineKeyboardMarkup:
        """Sets true/false values to the markup.

        :param pos: The positive confirmation value.
        :param neg: The negative confirmation value.
        :return: The inline keyboard markup.
        """

        if pos == neg:
            _logger.warning("TFMarkup pos=%s, neg=%s", pos, neg)
        return super().get_markup(("✅ {}".format(pos), "❌ {}".format(neg)),
                                  option_datas={
                                      "✅ {}".format(pos): self._TRUE,
                                      "❌ {}".format(neg): self._FALSE
                                  })


if __name__ == '__main__':
    pass
