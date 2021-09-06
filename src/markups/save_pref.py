#!/usr/bin/env python3
"""
Handler for save preference inline keyboard markup.

The Telegram bot uses this keyboard markup to ask user for global/local save preferences.

Usage:
    To obtain the pattern regex for CallbackQueryHandlers: SavePrefMarkup.get_pattern()
    To initialise a save preference keyboard markup: markup.get_markup()
    To verify if an option is defined: SavePrefMarkup.is_option(option)
    To check which pre-defined option is selected: option == SavePrefMarkup.get_save_always() OR
                                                   option == SavePrefMarkup.get_never_save() OR
                                                   option == SavePrefMarkup.get_ask_again()

TODO include dependencies
"""

from markups import BaseMarkup
from telegram import InlineKeyboardMarkup


class SavePrefMarkup(BaseMarkup):
    """SavePrefMarkup class for save preference inline keyboard.

    Attributes
        _OPTIONS    The options provided on the inline keyboard.
    """

    # Define constants
    _SAVE_ALWAYS = "ALWAYS Save"
    _NEVER_SAVE = "NEVER Save"
    _ASK_AGAIN = "Always ASK Me First"

    # region Get constants

    @classmethod
    def get_save_always(cls) -> str:
        """Gets the save always constant.

        :return: The save always constant.
        """

        return cls._SAVE_ALWAYS

    @classmethod
    def get_never_save(cls) -> str:
        """Gets the never save constant.

        :return: The never save constant.
        """

        return cls._NEVER_SAVE

    @classmethod
    def get_ask_again(cls) -> str:
        """Gets the ask again constant.

        :return: The ask again constant.
        """

        return cls._ASK_AGAIN

    # endregion Get constants

    @classmethod
    def get_pattern(cls, *_) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        return super().get_pattern(cls._SAVE_ALWAYS, cls._NEVER_SAVE, cls._ASK_AGAIN)

    @classmethod
    def is_option(cls, option: str) -> bool:
        """Checks if the option parsed is defined.

        :param option: The option parsed.
        :return: Whether the option is defined.
        """

        return option in (cls._SAVE_ALWAYS, cls._NEVER_SAVE, cls._ASK_AGAIN)

    def get_markup(self, *_) -> InlineKeyboardMarkup:
        """Sets the save preference options to the markup.

        :return: The inline keyboard markup.
        """

        return super().get_markup(("✅ {}".format(self._SAVE_ALWAYS), "❌ {}".format(self._NEVER_SAVE)),
                                  "❓ {} ❓".format(self._ASK_AGAIN))


if __name__ == '__main__':
    pass
