#!/usr/bin/env python3
"""
Generic handler for Telegram true/false inline keyboard markups.

A true/false inline keyboard refers to an inline keyboard in Telegram with only two options.
These two options are (usually) opposites and are normally the only two appropriate responses.
This script standardises the initialisation of a generic true/false inline keyboard.

Usage:
    To initialise a true/false keyboard markup: markups.true_false.init(pos, neg)
    To verify callback data is from this markup instance: markups.true_false.verify(callback_data)
    To verify callback data is from an option selected: markups.true_false.verify(callback_data, option)
    To get option data from callback data: markups.true_false.verify(callback_data, get_options()[0])

TODO include dependencies
"""

from markups.base import BaseMarkup
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class TFMarkup(BaseMarkup):
    """TFMarkup class for custom true/false inline keyboard.

    Attributes
        _SIGNATURE  The signature of the function that instantiated the markup.
        _OPTIONS    The options provided on the inline keyboard.
    """

    def init(self, pos: Optional[str] = "YES", neg: Optional[str] = "NO") -> InlineKeyboardMarkup:
        """Sets true/false values to the markup.

        :param pos: The positive confirmation value.
        :param neg: The negative confirmation value.
        :return: The inline keyboard markup.
        """

        # Sanity check
        if not (pos and neg):
            _logger.warning("TFMarkup init pos=%s, neg=%s", pos, neg)
        elif pos == neg:
            _logger.warning("TFMarkup init with both pos and neg = %s, you sure?", pos)

        # Return markup
        self.set_options(pos, neg)
        keyboard = [
            [
                InlineKeyboardButton("✅ {}".format(pos), callback_data=self._format_callback_data(pos)),
                InlineKeyboardButton("❌ {}".format(neg), callback_data=self._format_callback_data(neg))
            ]
        ]
        return InlineKeyboardMarkup(keyboard)


if __name__ == '__main__':
    pass
