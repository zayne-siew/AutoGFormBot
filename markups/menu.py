#!/usr/bin/env python3
"""
Handler for custom reusable Telegram inline menus.

This script allows for the standardised building of inline menus and menu options.

Usage:
    To initialise a menu keyboard markup: markups.menu.init(option_rows, *args, **kwargs)
    To verify callback data is from this markup instance: markups.menu.verify(callback_data)
    To verify callback data is from an option selected: markups.menu.verify(callback_data, option)
    To get option data from callback data: markups.menu.get_data(callback_data)

TODO include dependencies
"""

from markups.base import BaseMarkup
import logging
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Mapping, Optional, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class MenuMarkup(BaseMarkup):
    """
    MenuMarkup class for custom reusable Telegram inline menus.

    In addition to the BaseMarkup class on which it extends, the MenuMarkup class has several other
    features which may be useful for menu building:
        - Handling of emojis per menu item.
        - Handling of custom callback data formats.

    Attributes
        _SIGNATURE  The signature of the function that instantiated the markup.
        _OPTIONS    The options provided on the inline keyboard.
    """

    def init(self, *option_rows: Union[str, Tuple[str, ...]], includes_emojis: Optional[bool] = True,
             callback_format: Optional[str] = None, option_datas: Optional[Mapping[str, str]] = None) \
            -> InlineKeyboardMarkup:
        """Initialises the markup with parsed options and additional features.

        :param option_rows: The options, along with its formatting.
        :param includes_emojis: Flag to indicate if the options data includes emojis.
                                If there are emojis in the option data, it will be excluded in the callback data.
        :param callback_format: The format of the callback data to follow.
                                The function will format the callback data according to:
                                    '{SIGNATURE}': replaced with signature
                                    '{OPTION}': replaced with option data
                                    Other characters are left as plaintext in the formatted callback data.
                                If None, the default _format_callback_data() format will be used.
        :param option_datas: The callback data to replace the option data, if any.
        :return: The inline keyboard markup.
        """

        # Initialise
        keyboard, options = [], []

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
                if includes_emojis:
                    # Check head and tail of string for emojis
                    # Expecting string format: <EMOJI + " "><Option Data><" " + EMOJI>
                    if not re.match("^\\w$", option_data[0]):
                        assert len(option_data) >= 2
                        option_data = option_data[1:].lstrip()
                    if not re.match("^\\w$", option_data[len(option_data)-1]):
                        assert len(option_data) >= 2
                        option_data = option_data[:len(option_data)-1].rstrip()

            # Determine callback data format
            if isinstance(callback_format, str):
                option_data = callback_format.replace("{SIGNATURE}", self.get_signature()) \
                    .replace("{OPTION}", option_data)
            else:
                option_data = self._format_callback_data(option_data)

            # Save option and callback data
            if option in options:
                # Sanity check
                _logger.warning("%s init option %s already saved in options, appending duplicate",
                                self.__class__.__name__, option)
            options.append(option)
            return InlineKeyboardButton(option, callback_data=option_data)

        for option_row in option_rows:

            # Handle single option as string
            if isinstance(option_row, str):
                keyboard.append([_add_option(option_row)])

            # Handle multiple options
            else:
                keyboard.append([_add_option(option) for option in option_row])

        # Finalise
        self.set_options(*options)
        return InlineKeyboardMarkup(keyboard)


if __name__ == '__main__':
    pass
