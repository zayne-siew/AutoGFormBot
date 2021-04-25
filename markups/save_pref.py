#!/usr/bin/env python3
"""
Handler for save preference inline keyboard markup.

The Telegram bot uses this keyboard markup to ask user for global/local save preferences.

Usage:
    To initialise a save preference keyboard markup: markups.save_pref.init()
    To verify callback data is from this markup instance: markups.save_pref.verify(callback_data)
    To verify callback data is from an option selected: markups.save_pref.verify(callback_data, option)
    To get option data from callback data: markups.save_pref.get_data(callback_data)

TODO include dependencies
"""

from markups.base import BaseMarkup
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)

# Define constants
_SAVE_ALWAYS = "ALWAYS Save"
_NEVER_SAVE = "NEVER Save"
_ASK_AGAIN = "Always ASK Me First"


class SavePrefMarkup(BaseMarkup):
    """SavePrefMarkup class for save preference inline keyboard.

    Attributes
        _SIGNATURE  The signature of the function that instantiated the markup.
        _OPTIONS    The options provided on the inline keyboard.
    """

    def init(self) -> InlineKeyboardMarkup:
        """Sets the save preference options to the markup.

        :return: The inline keyboard markup.
        """

        self.set_options(_SAVE_ALWAYS, _NEVER_SAVE, _ASK_AGAIN)
        keyboard = [
            [
                InlineKeyboardButton("✅ {}".format(_SAVE_ALWAYS),
                                     callback_data=self._format_callback_data(_SAVE_ALWAYS)),
                InlineKeyboardButton("❌ {}".format(_NEVER_SAVE),
                                     callback_data=self._format_callback_data(_NEVER_SAVE))
            ],
            [InlineKeyboardButton("❓ {} ❓".format(_ASK_AGAIN), callback_data=self._format_callback_data(_ASK_AGAIN))]
        ]
        return InlineKeyboardMarkup(keyboard)


if __name__ == '__main__':
    pass
