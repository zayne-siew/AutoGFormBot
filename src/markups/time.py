#!/usr/bin/env python3
"""
Handler for custom time picker as Telegram inline keyboard markup.

This script standardises the initialisation of custom time pickers.

Usage:
    To obtain the pattern regex for CallbackQueryHandlers: TimeMarkup.get_pattern()
    To initialise a time picker keyboard markup: markup.get_markup()
    To process the callback data obtained: markup.perform_action(option)

TODO include dependencies
"""

from datetime import datetime
import logging
import math
from src.markups import BaseMarkup, BaseOptionMarkup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class TimeMarkup(BaseOptionMarkup):
    """TimeMarkup class for custom reusable time pickers as Telegram inline keyboards.

    Attributes
        _OPTIONS    Defined options available in the options menu.
        _REQUIRED   Flag to indicate if a response is required.
        _HOUR       The hour of the time picker to display.
        _MINUTE     The minute of the time picker to display.
        _SECOND     The second of the time picker to display.
    """

    # Define constants
    _CHOOSE_HOUR = "CHOOSE HOUR"
    _CHOOSE_MINUTE = "CHOOSE MINUTE"
    _CHOOSE_SECOND = "CHOOSE SECOND"
    _CHOOSE_AM_PM = "CHOOSE AM PM"
    _FINALISE = "FINALISE"
    _IGNORE = "IGNORE"

    # region Constructors

    def __init__(self, required: bool, hour: Optional[int] = None, minute: Optional[int] = None,
                 second: Optional[int] = None) -> None:
        """Initialisation of TimeMarkup class.

        The 'seconds' option will only be displayed if the 'second' parameter is defined.

        :param required: Flag to indicate if a response is required.
        :param hour: The hour of the time picker to display.
        :param minute: The minute of the time picker to display.
        :param second: The second of the time picker to display.
        """

        # Initialisation
        now = datetime.now()
        hour = hour if hour else now.hour
        minute = minute if minute else now.minute

        # Sanity check
        hour_limit = 23
        if not 0 <= minute <= 59:
            _logger.warning("TimeMarkup trying to initialise time picker with minute=%d", minute)
            minute = now.minute
        if second:
            hour_limit = 72  # Limit for duration questions is 72
            if not 0 <= second <= 59:
                _logger.warning("TimeMarkup trying to initialise time picker with second=%d", second)
                second = now.second
        if not 0 <= hour <= hour_limit:
            _logger.warning("TimeMarkup trying to initialise time picker with hour=%d", hour)
            hour = now.hour

        # Assign all attributes
        self._HOUR = hour
        self._MINUTE = minute
        self._SECOND = second
        super().__init__(required, disable_warnings=True)

    def __repr__(self) -> str:
        """Overriden __repr__ of TimeMarkup.

        :return: The __repr__ string.
        """

        return BaseMarkup.__repr__(self) + ": required={}, hour={}, minute={}, second={}" \
            .format(self._REQUIRED, self._HOUR, self._MINUTE, self._SECOND)

    def __str__(self) -> str:
        """Overriden __str__ of TimeMarkup class.

        :return: The __str__ string.
        """

        return BaseMarkup.__str__(self) + " displaying {}:{}{}\nA response is{} required" \
            .format(self._HOUR, self._MINUTE, (":" + str(self._SECOND)) * bool(self._SECOND),
                    " not" * (not self._REQUIRED))

    # endregion Constructors

    # region Helper functions

    def _individualise(self, start: int, stop: int) -> InlineKeyboardMarkup:
        """Helper function to return an inline keyboard markup with individual numbers as buttons.

        The function groups buttons into threes and appends blank buttons at the end to 'pretty-print' them.
        NOTE: The function is not meant to support large numbers of buttons.

        :param start: The number to start with, inclusive.
        :param stop: The number to stop at, inclusive.
        :return: The inline keyboard markup.
        """

        # Initialisation
        n = stop - start + 1
        blank = InlineKeyboardButton(" ", callback_data=self._IGNORE)

        buttons = [[InlineKeyboardButton(str(start+i*3+j), callback_data=str(start+i*3+j)) for j in range(3)]
                   for i in range(n//3)]
        if n % 3 == 1:
            buttons.append([blank, InlineKeyboardButton(str(stop), callback_data=str(stop)), blank])
        elif n % 3 == 2:
            buttons.append([InlineKeyboardButton(str(stop-1), callback_data=str(stop-1)), blank,
                            InlineKeyboardButton(str(stop), callback_data=str(stop))])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def _group(n: int) -> InlineKeyboardMarkup:
        """Helper function to return an inline keyboard markup with numbers grouped for visualisation.

        This function expects only either n=60 or n=72, hence, the numbers will be distributed into 6 groups.

        :param n: The total number of numbers to group.
        :return: The inline keyboard markup.
        """

        m = math.ceil(n/6)
        keyboard = []
        for i in range(3):
            button_row = []
            for j in range(2):
                _min = (2 * i + j) * m + 1
                _max = min((2 * i + j + 1) * m, n)
                button_row.append(InlineKeyboardButton("{} - {}".format(_min, _max),
                                                       callback_data="{}-{}".format(_min, _max)))
            keyboard.append(button_row)
        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def _is_option(cls, option: str) -> bool:
        """Verify if the option parsed is defined.

        :param option: The option to verify.
        :return: Flag to indicate if the option is defined.
        """

        if option not in (cls._SKIP, cls._CHOOSE_HOUR, cls._CHOOSE_MINUTE, cls._CHOOSE_SECOND, cls._CHOOSE_AM_PM,
                          cls._FINALISE, cls._IGNORE):
            try:
                if "-" in option:
                    # Expecting <1/2-digit number>-<1/2-digit number>
                    x, y = option.split("-")
                    x, y = int(x), int(y)
                else:
                    # Expecting a 1/2-digit number
                    x, y = int(option), 0
                if not (0 <= x <= 99 and 0 <= y <= 99):
                    raise ValueError
            except ValueError:
                return False
        return True

    # endregion Helper functions

    # region Getters

    @classmethod
    def get_pattern(cls, *_) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        return "^(" + "|".join((cls._SKIP, cls._CHOOSE_HOUR, cls._CHOOSE_MINUTE, cls._CHOOSE_SECOND, cls._CHOOSE_AM_PM,
                                cls._FINALISE, cls._IGNORE)) + "|\\d{1,2}(-\\d{1,2})?)$"

    def get_markup(self, *_) -> InlineKeyboardMarkup:
        """Initialises the markup with parsed options.

        :return: The inline keyboard markup.
        """

        # Determine correct label(s) and button(s) to display
        if self._SECOND is None:
            label = "AM/PM"
            button = InlineKeyboardButton("AM" if self._HOUR < 12 else "PM", callback_data=self._CHOOSE_AM_PM)
        else:
            label = "Second"
            button = InlineKeyboardButton("{:02d}".format(self._SECOND), callback_data=self._CHOOSE_SECOND)
        handler_buttons = [InlineKeyboardButton("Skip", callback_data=self._SKIP)] * (not self._REQUIRED) + \
                          [InlineKeyboardButton("OK", callback_data=self._FINALISE)]

        keyboard = [
            [
                # Labels to be displayed on the first row
                InlineKeyboardButton("Hour", callback_data=self._IGNORE),
                InlineKeyboardButton("Minute", callback_data=self._IGNORE),
                InlineKeyboardButton(label, callback_data=self._IGNORE)
            ],
            [
                # Values to be displayed on the second row
                InlineKeyboardButton("{:02d}".format(self._HOUR - 12 * (self._HOUR > 12)),
                                     callback_data=self._CHOOSE_HOUR),
                InlineKeyboardButton("{:02d}".format(self._MINUTE), callback_data=self._CHOOSE_MINUTE),
                button
            ],
            # Handler buttons on the last row
            handler_buttons
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_options(self) -> None:
        """Overriding of get_options in BaseOptionMarkup.

        Since this function is not applicable in TimeMarkup, it is overriden so as to prevent misuse.
        """
        pass

    # endregion Getters

    def perform_action(self, option: str) -> Optional[Union[InlineKeyboardMarkup, str]]:
        """Perform action according to the callback data.

        :param option: The option received from the callback data.
        :return: If the callback data is _IGNORE or invalid, return None.
                 Else if the callback data is _CHOOSE_AM_PM,
                    return the markup instance after toggling between the 'AM' and 'PM' values.
                 Else if the callback data is _CHOOSE_HOUR or _CHOOSE_MINUTE or _CHOOSE_SECOND,
                    return the markup instance of all the possible values to choose from.
                 Else if the callback data is _FINALISE,
                    return the selected time in the format '%H:%M' or '%H:%M:%S'.
                 Else if the callback data is of the format '{}-{}',
                    return the markup instance of all the individual values to choose from.
                 Else, return the main markup instance with the new selected value.
        """

        result = None
        if not self._is_option(option):
            _logger.error("TimeMarkup perform_action received invalid option: %s", option)
        elif option == self._IGNORE:
            pass
        elif option == self._SKIP:
            result = self.get_required_warning() if self._REQUIRED else self._SKIP
        elif option == self._CHOOSE_AM_PM:
            self._HOUR = (self._HOUR + 12) % 24
            result = self.get_markup()
        elif option == self._CHOOSE_HOUR:
            self._HOUR = -1
            result = self._group(12 if self._SECOND is None else 72)
        elif option == self._CHOOSE_MINUTE:
            self._MINUTE = -1
            result = self._group(60)
        elif option == self._CHOOSE_SECOND:
            self._SECOND = -1
            result = self._group(60)
        elif option == self._FINALISE:
            result = "{}:{}{}".format(self._HOUR, self._MINUTE,
                                      "" if self._SECOND is None else ":{}".format(self._SECOND))
        elif "-" in option:
            start, stop = option.split("-")
            return self._individualise(int(start), int(stop))
        else:
            # Assign the values back to the main markup menu
            if self._HOUR == -1:
                self._HOUR = int(option)
            elif self._MINUTE == -1:
                self._MINUTE = int(option)
            elif self._SECOND == -1:
                self._SECOND = int(option)
            else:
                # Something wrong happened
                _logger.error("TimeMarkup trying to assign user chosen value but none available to assign\n"
                              "hour=%s, minute=%s, second=%s, option=%s",
                              self._HOUR, self._MINUTE, self._SECOND, option)
                return
            result = self.get_markup()
        return result


if __name__ == '__main__':
    pass
