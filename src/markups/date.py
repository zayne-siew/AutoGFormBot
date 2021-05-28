#!/usr/bin/env python3
"""
Handler for custom date picker as Telegram inline keyboard markup.

This script has been modified from the calendar-telegram GitHub repo:
https://github.com/unmonoqueteclea/calendar-telegram/blob/master/telegramcalendar.py

Usage:
    To obtain the pattern regex for CallbackQueryHandlers: DateMarkup.get_pattern()
    To initialise a date picker keyboard markup: markup.get_markup()
    To process the callback data obtained: markup.perform_action(option)

TODO include dependencies
"""

import calendar
from datetime import datetime
import logging
from src.markups import BaseMarkup, BaseOptionMarkup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class DateMarkup(BaseOptionMarkup):
    """DateMarkup class for custom reusable date pickers as Telegram inline keyboards.

    Attributes
        _OPTIONS    Defined options available in the options menu.
        _YEAR       The year of the calendar to display.
        _MONTH      The month of the calendar to display.
    """

    # Define constants
    _PREV_MONTH = "PREV_MONTH"
    _NEXT_MONTH = "NEXT_MONTH"
    _FORMAT = "%Y-%m-%d"

    # region Constructors

    def __init__(self, year: Optional[int] = None, month: Optional[int] = None) -> None:
        """Initialisation of DateMarkup class.

        :param year: The year of the calendar to display.
        :param month: The month of the calendar to display.
        """

        # Initialisation
        calendar.setfirstweekday(calendar.SUNDAY)
        now = datetime.now()
        year = year if year else now.year
        month = month if month else now.month

        # Sanity check
        if not 1 <= month <= 12:
            _logger.warning("DateMarkup trying to initialise calendar with month=%d", month)
            month = now.month

        # Assign all attributes
        self._YEAR = year
        self._MONTH = month
        super().__init__(disable_warnings=True)

    def __repr__(self) -> str:
        """Overriden __repr__ of DateMarkup.

        :return: The __repr__ string.
        """

        return BaseMarkup.__repr__(self) + ": year={}, month={}".format(self._YEAR, self._MONTH)

    def __str__(self) -> str:
        """Overriden __str__ of DateMarkup class.

        :return: The __str__ string.
        """

        return BaseMarkup.__str__(self) + " with year = {} and month = {}".format(self._YEAR, self._MONTH)

    # endregion Constructors

    # region Helper functions

    def _next_month(self) -> None:
        """Helper function to set the stored year and month to the next chronological month."""

        self._MONTH += 1
        if self._MONTH == 13:
            self._YEAR += 1
            self._MONTH = 1

    def _prev_month(self) -> None:
        """Helper function to set the stored year and month to the previous chronological month."""

        self._MONTH -= 1
        if self._MONTH == 0:
            self._YEAR -= 1
            self._MONTH = 12

    @classmethod
    def _is_option(cls, option: str, *_) -> bool:
        """Verify if the option parsed is defined.

        :param option: The option to verify.
        :return: Flag to indicate if the option is defined.
        """

        if option not in (cls._IGNORE, cls._PREV_MONTH, cls._NEXT_MONTH):
            try:
                _ = datetime.strptime(option, cls._FORMAT)
            except ValueError:
                return False
        return True

    # endregion Helper functions

    # region Getters

    @classmethod
    def get_pattern(cls) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        return "^(" + "|".join((cls._IGNORE, cls._PREV_MONTH, cls._NEXT_MONTH)) + "|" + \
               cls._FORMAT.replace("%Y", "\\d{4}").replace("%m", "\\d{1,2}").replace("%d", "\\d{1,2}") + ")$"

    def get_markup(self, *_) -> InlineKeyboardMarkup:
        """Initialises the markup with parsed options.

        :return: The inline keyboard markup.
        """

        keyboard = [
            # Month and year to be inserted into the first row
            [
                # Days of the week displayed on the second row
                InlineKeyboardButton("Sun", callback_data=self._IGNORE),
                InlineKeyboardButton("Mon", callback_data=self._IGNORE),
                InlineKeyboardButton("Tue", callback_data=self._IGNORE),
                InlineKeyboardButton("Wed", callback_data=self._IGNORE),
                InlineKeyboardButton("Thu", callback_data=self._IGNORE),
                InlineKeyboardButton("Fri", callback_data=self._IGNORE),
                InlineKeyboardButton("Sat", callback_data=self._IGNORE)
            ],
            # Dates of the month to be inserted between the second and last rows
            [
                # Button handling displayed on the last row
                InlineKeyboardButton("<", callback_data=self._PREV_MONTH),
                InlineKeyboardButton(" ", callback_data=self._IGNORE),
                InlineKeyboardButton(">", callback_data=self._NEXT_MONTH)
            ]
        ]

        # Add year and month
        keyboard.insert(0, [InlineKeyboardButton(calendar.month_name[self._MONTH] + " " + str(self._YEAR),
                                                 callback_data=self._IGNORE)])

        # Add dates
        my_calendar = calendar.monthcalendar(self._YEAR, self._MONTH)
        for week in my_calendar:
            row = []
            for day in week:
                if day == 0:
                    row.append(InlineKeyboardButton(" ", callback_data=self._IGNORE))
                else:
                    row.append(InlineKeyboardButton(
                        str(day), callback_data=datetime(self._YEAR, self._MONTH, day).strftime(self._FORMAT)))
            keyboard.insert(len(keyboard) - 1, row)

        return InlineKeyboardMarkup(keyboard)

    # endregion Getters

    def perform_action(self, option: str) -> Optional[Union[InlineKeyboardMarkup, str]]:
        """Perform action according to the callback data.

        :param option: The option received from the callback data.
        :return: If the callback data is _IGNORE or invalid, return None.
                 Else if the callback data is _PREV_MONTH or _NEXT_MONTH,
                    return the markup instance of the calendar in the previous/next chronological month.
                 Else, return the date as selected by the user.
        """

        result = None
        if not self._is_option(option):
            _logger.error("DateMarkup perform_action received invalid option: %s", option)
        elif option == self._IGNORE:
            pass
        elif option == self._PREV_MONTH:
            self._prev_month()
            result = self.get_markup()
        elif option == self._NEXT_MONTH:
            self._next_month()
            result = self.get_markup()
        else:
            result = option
        return result


if __name__ == '__main__':
    pass
