#!/usr/bin/env python3
"""
Base class for custom reusable Telegram inline keyboards.

This script standardises the initialisation of a custom reusable inline keyboard.

Usage:
    To obtain the pattern regex for CallbackQueryHandlers: BaseMarkup.get_pattern(*datas)
    To initialise a base keyboard markup: markup.get_markup(*option_rows, option_datas=option_datas)

TODO include dependencies
"""

from markups.abstract import AbstractMarkup, AbstractOptionMarkup
import logging
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Any, Mapping, Optional, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)

# Define constants
_DEFAULT_LABEL = "DEFAULT_LABEL"


class BaseMarkup(AbstractMarkup):
    """BaseMarkup class for custom reusable Telegram inline keyboards."""

    def __str__(self) -> str:
        """Overriden __str__ of BaseMarkup class.

        :return: The __str__ string.
        """

        return "{} class instance".format(self.__class__.__name__)

    @classmethod
    def get_pattern(cls, *datas: str) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :param datas: The callback data(s) to format into pattern regex.
        :return: The pattern regex.
        """

        if len(datas) == 0:
            _logger.warning("%s get_pattern does not accept zero callback data", cls.__name__)
            return ""
        elif len(datas) == 1:
            return "^" + datas[0] + "$"
        else:
            return "^(" + "|".join(datas) + ")$"

    def get_markup(self, *option_rows: Union[str, Tuple[str, ...]], option_datas: Optional[Mapping[str, str]] = None) \
            -> InlineKeyboardMarkup:
        """Initialises the markup with parsed options.

        :param option_rows: The options, along with its formatting.
        :param option_datas: The callback data to replace the options, if any.
        :return: The inline keyboard markup.
        """

        def _add_option(option: str) -> InlineKeyboardButton:
            """Helper function to add option to the keyboard.

            :param option: The option to add.
            :return: The inline keyboard button to add to the keyboard.
            """

            # Determine option data
            if option_datas and option in option_datas.keys():
                option_data = option_datas.get(option)
            else:
                option_data = option

            # Check head and tail of string for emojis
            # Expecting string format: <EMOJI + " "><Option Data><" " + EMOJI>
            if not re.match("^\\w$", option_data[0]):
                assert len(option_data) >= 2
                option_data = option_data[1:].lstrip()
            if not re.match("^\\w$", option_data[len(option_data) - 1]):
                assert len(option_data) >= 2
                option_data = option_data[:len(option_data) - 1].rstrip()

            return InlineKeyboardButton(option, callback_data=option_data)

        keyboard = []
        for option_row in option_rows:
            if isinstance(option_row, str):
                keyboard.append([_add_option(option_row)])
            else:
                keyboard.append([_add_option(option) for option in option_row])
        return InlineKeyboardMarkup(keyboard)


class BaseOptionMarkup(AbstractOptionMarkup, BaseMarkup):
    """BaseOptionMarkup class for custom option menus as Telegram inline keyboards.

    Attributes
        _OPTIONS    Defined options available in the options menu.
    """

    # Define constants
    _IGNORE = "IGNORE"

    # region Constructors

    def __init__(self, *options: str, label: Optional[str] = _DEFAULT_LABEL, disable_warnings: Optional[bool] = False,
                 **kw_options: Mapping[str, Union[str, Tuple[str, ...]]]) -> None:
        """Initialisation of BaseOptionMarkup class.

        :param options: Argument options parsed to be stored.
        :param label: The label for the argument options to be stored.
        :param disable_warnings: Flag to indicate if warnings should be disabled.
        :param kw_options: Keyword-based option dictionary to be stored.
        """

        # Sanity check
        if len(options) == 0 and len(kw_options) == 0:
            if not disable_warnings:
                _logger.warning("%s instance trying to initialise with no options defined", self.__class__.__name__)
            self._OPTIONS = {_DEFAULT_LABEL: None}
            return
        elif len(options) > 0 and len(kw_options) > 0 and not disable_warnings:
            _logger.warning("%s instance initialising with both options=%s and kw_options=%s defined",
                            self.__class__.__name__, options, kw_options)
        elif len(options) > 0 and not bool(label):
            if not disable_warnings:
                _logger.warning("%s instance trying to initialise with options=%s without defining label",
                                self.__class__.__name__, options)
            label = _DEFAULT_LABEL

        self._OPTIONS = dict(**kw_options) if len(kw_options) > 0 else \
            {label: options[0] if len(options) == 1 else options}

    def __repr__(self) -> str:
        """Overriden __repr__ of BaseOptionMarkup.

        :return: The __repr__ string.
        """

        return BaseMarkup.__repr__(self) + ": options={}".format(repr(self._OPTIONS))

    def __str__(self) -> str:
        """Overriden __str__ of BaseOptionMarkup.

        :return: The __str__ string.
        """

        return BaseMarkup.__str__(self) + " with the following options: {}".format(self._OPTIONS)

    # endregion Constructors

    # region Getters

    @classmethod
    def get_ignore(cls) -> str:
        """Gets the IGNORE constant.

        :return: The IGNORE constant.
        """

        return cls._IGNORE

    def get_pattern(self, *keys: str) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :param keys: The key(s) to obtain the options from, for formatting.
        :return: The pattern regex.
        """

        if len(keys) == 0:
            _logger.warning("%s get_pattern does not accept zero parsed keys", self.__class__.__name__)
            return ""
        else:
            return "^(" + "|".join("|".join(self._OPTIONS.get(key, {})) for key in keys) + ")$"

    def get_options(self, key: str) -> Optional[Union[str, Tuple[str, ...]]]:
        """Gets the options stored, if any.

        :param key: The key to obtain the options from.
        :return: The options stored, if any.
        """

        return self._OPTIONS.get(key)

    # endregion Getters

    def _is_option(self, option: str, key: str) -> bool:
        """Verify if the option parsed is defined.

        :param option: The option to verify.
        :param key: The key to obtain options from.
        :return: Flag to indicate if the option is defined.
        """

        return option in self._OPTIONS.get(key)

    def perform_action(self, option: str) -> Any:
        """Perform action according to the callback data.

        BaseOptionMarkup does not implement the perform_action function.

        :param option: The option received from the callback data.
        :return: The relevant result after performing the relevant action.
        """
        pass


if __name__ == '__main__':
    pass
