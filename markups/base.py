#!/usr/bin/env python3
"""
Base class for custom reusable Telegram inline keyboards.

This script standardises the initialisation of a custom reusable inline keyboard.

Usage:
    To initialise a base keyboard markup: markups.base.init(option_rows)
    To verify callback data is from this markup instance: markups.base.verify(callback_data)
    To verify callback data is from an option selected: markups.base.verify(callback_data, option)
    To get option data from callback data: markups.base.get_data(callback_data)

TODO include dependencies
"""

from markups.abstract import AbstractMarkup
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class BaseMarkup(AbstractMarkup):
    """
    BaseMarkup class for custom reusable Telegram inline keyboards.

    Attributes
        _SIGNATURE  The signature of the function that instantiated the markup.
        _OPTIONS    The options provided on the inline keyboard.
    """

    # region Constructors

    def __init__(self, signature: str) -> None:
        """Initialisation of BaseMarkup class.

        :param signature: The signature of the method that instantiated the markup.
        """

        self._SIGNATURE = signature
        self._OPTIONS = None

    def __repr__(self) -> str:
        """Overriden __repr__ of BaseMarkup class.

        :return: The __repr__ string.
        """

        return super().__repr__() + ": signature={}, options={}".format(self._SIGNATURE, self._OPTIONS)

    def __str__(self) -> str:
        """Overriden __str__ of BaseMarkup class.

        :return: The __str__ string.
        """

        return "{} object with signature {}".format(self.__class__.__name__, self._SIGNATURE)

    def __eq__(self, other) -> bool:
        """Overriden __eq__ of BaseMarkup class.

        Two BaseMarkup classes are equal if their signatures are equal.

        :param other: The other instance of the BaseMarkup class.
        :return: Whether the two instances are equal.
        """

        return self._SIGNATURE == other.get_signature()

    # endregion Constructors

    # region Getters and Setters

    def get_signature(self) -> str:
        """Gets the signature of the BaseMarkup instance.

        :return: The signature of the BaseMarkup instance.
        """

        return self._SIGNATURE

    # region Handling options

    def get_options(self) -> Optional[Tuple[str]]:
        """Gets the defined options.

        :return: The defined options as a tuple, otherwise None.
        """

        return self._OPTIONS

    def set_options(self, *options: str) -> None:
        """Sets the parsed options.

        :param options: The options to set.
        """

        if len(options) < 1:
            _logger.warning("%s instance trying to set options with options=%s",
                            self.__class__.__name__, options)
        else:
            self._OPTIONS = tuple(options)

    def _is_option(self, option: str) -> bool:
        """Check if option is defined in options list.

        :param option: The option to check.
        :return: Whether the option is defined.
        """

        return self._OPTIONS and option in self._OPTIONS

    # endregion Handling options

    # endregion Getters and Setters

    def _format_callback_data(self, data: str) -> str:
        """Prepends the callback data with the signature.

        :param data: The callback data to format.
        :return: The formatted callback data with the prepended signature.
        """

        return self._SIGNATURE + " " + data

    def init(self, *option_rows: Union[str, Tuple[str, ...]]) -> InlineKeyboardMarkup:
        """Initialises the markup with parsed options.

        The function accepts the options along with its parsed structural formatting,
        and returns a markup with the defined structure and options.

        The formatting for options is defined as follows:
        BaseMarkup.init(
            (
                row_1_option_1,
                ...                                     R1O1    R1O2    ...     R1O(M-1)    R1OM
                row_1_option_M                          R2O1    R2O2    ...     R2O(M-1)    R2OM
            ),                                                    .                .
            ...                            --->                   .                .
            (                                                     .                .
                row_N_option_1,                         R(N-1)O1        ...             R(N-1)OM
                ...                                     RNO1    RNO2    ...     RNO(M-1)    RNOM
                row_N_option_M
            )
        )

        :param option_rows: The options, along with its formatting.
        :return: The inline keyboard markup.
        """

        # Initialise
        keyboard, options = [], []

        def _add_option(option: str) -> InlineKeyboardButton:
            """Helper function to add option to the keyboard.

            :param option: The option to add.
            :return: The inline keyboard button to add to the keyboard.
            """

            if option in options:
                # Sanity check
                _logger.warning("%s init option %s already saved in options, appending duplicate",
                                self.__class__.__name__, option)
            options.append(option)
            return InlineKeyboardButton(option, callback_data=self._format_callback_data(option))

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

    def verify(self, callback_data: str, option: Optional[str] = None) -> bool:
        """Verifies if the callback data came from selecting the option in the markup instance.

        :param callback_data: The callback data to verify.
        :param option: The option that was supposedly selected to verify.
        :return Flag to indicate whether the callback data contains the markup instance signature.
                If option is specified, the flag also indicates if the option matches the option data.
        """

        if option:
            # Expecting format self._SIGNATURE + " " + data
            return self._is_option(option) and callback_data == self._format_callback_data(option)
        else:
            return self.get_signature() in callback_data

    def get_data(self, callback_data: str) -> Optional[str]:
        """Returns the unformatted data from the formatted callback data.

        :param callback_data: The formatted callback data to obtain data from.
        :return: The unformatted data.
        """

        if not self.verify(callback_data):
            # Sanity check
            _logger.warning("%s get_data callback data does not contain signature!\ncallback_data=%s, signature=%s",
                            self.__class__.__name__, callback_data, self.get_signature())
        else:
            return callback_data.replace(self.get_signature() + " ", "")


if __name__ == '__main__':
    pass
