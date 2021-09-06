#!/usr/bin/env python3
"""
Base class for custom reusable Telegram inline keyboards.

This script standardises the initialisation of a custom reusable inline keyboard.

Usage:
    This script should not be used directly, other than its base class functionalities.

TODO include dependencies
"""

import logging
from markups import AbstractMarkup, AbstractOptionMarkup
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Any, Mapping, Optional, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


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
        _REQUIRED   Flag to indicate if a response is required.
    """

    # Define constants
    _SKIP = "SKIP_THIS_QUESTION"

    # region Constructors

    def __init__(self, required: bool, *options: str, disable_warnings: Optional[bool] = False) -> None:
        """Initialisation of BaseOptionMarkup class.

        :param required: Flag to indicate if a response is required.
        :param options: Options parsed to be stored.
        :param disable_warnings: Flag to indicate if warnings should be disabled.
        """

        if len(options) == 0 and not disable_warnings:
            _logger.warning("%s instance initialising with no options defined", self.__class__.__name__)
        self._REQUIRED = required
        self._OPTIONS = options

    def __repr__(self) -> str:
        """Overriden __repr__ of BaseOptionMarkup.

        :return: The __repr__ string.
        """

        return BaseMarkup.__repr__(self) + ": required={}, options={}".format(self._REQUIRED, repr(self._OPTIONS))

    def __str__(self) -> str:
        """Overriden __str__ of BaseOptionMarkup.

        :return: The __str__ string.
        """

        return BaseMarkup.__str__(self) + " with the following options: {}\nA response is{} required" \
            .format(self._OPTIONS, " not" * (not self._REQUIRED))

    # endregion Constructors

    # region Getters

    @classmethod
    def get_skip(cls) -> str:
        """Gets the SKIP constant.

        :return: The SKIP constant.
        """

        return cls._SKIP

    @classmethod
    def get_required_warning(cls) -> str:
        """Obtain warning string.

        :return: The warning string.
        """

        return "ALERT: This is a required question."

    def get_pattern(self) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        return super().get_pattern(*self._OPTIONS)

    def get_options(self) -> Tuple[str, ...]:
        """Gets the options stored, if any.

        :return: The options stored, if any.
        """

        return self._OPTIONS

    # endregion Getters

    def _is_option(self, option: str) -> bool:
        """Verify if the option parsed is defined.

        :param option: The option to verify.
        :return: Flag to indicate if the option is defined.
        """

        return option in self._OPTIONS or option == self._SKIP

    def perform_action(self, option: str) -> Any:
        """Perform action according to the callback data.

        BaseOptionMarkup does not implement the perform_action function.

        :param option: The option received from the callback data.
        :return: The relevant result after performing the relevant action.
        """
        pass


if __name__ == '__main__':
    pass
