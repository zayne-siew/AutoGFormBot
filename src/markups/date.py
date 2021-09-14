#!/usr/bin/env python3
"""
Handler for custom date picker as Telegram inline keyboard markup.

This script has been modified from the calendar-telegram GitHub repo:
https://github.com/unmonoqueteclea/calendar-telegram/blob/master/telegramcalendar.py

                           START OF COPYRIGHT NOTICE
------------------------------------------------------------------------------
MIT License

Copyright (c) 2016 unmonoqueteclea

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
------------------------------------------------------------------------------
                            END OF COPYRIGHT NOTICE

Usage:
    To obtain the pattern regex for CallbackQueryHandlers: DateMarkup.get_pattern()
    To initialise a date picker keyboard markup: markup.get_markup()
    To process the callback data obtained: markup.perform_action(option)

TODO include dependencies
"""

import calendar
from datetime import datetime
import logging
from markups import BaseMarkup, BaseOptionMarkup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class DateMarkup(BaseOptionMarkup):
    """DateMarkup class for custom reusable date pickers as Telegram inline keyboards.

    Attributes
        _OPTIONS    Defined options available in the options menu.
        _REQUIRED   Flag to indicate if a response is required.
        _YEAR       The year of the calendar to display.
        _MONTH      The month of the calendar to display.
        _FROM       The date to display from.
    """

    # Define constants
    _IGNORE = "IGNORE"
    _PREV_MONTH = "PREV_MONTH"
    _NEXT_MONTH = "NEXT_MONTH"
    _FORMAT = "%Y-%m-%d"

    # region Constructors

    def __init__(self, required: bool, *, year: Optional[int] = None, month: Optional[int] = None,
                 from_date: Optional[datetime] = None) -> None:
        """Initialisation of DateMarkup class.

        :param required: Flag to indicate if a response is required.
        :param year: The year of the calendar to display.
        :param from_date: The date to display the calendar from.
        :param month: The month of the calendar to display.
        """

        # Initialisation
        calendar.setfirstweekday(calendar.SUNDAY)
        now = datetime.now()
        year = year if year else now.year
        month = month if month else now.month
        self._FROM = from_date

        # Sanity check
        if not 1 <= year <= 9999:
            _logger.warning("DateMarkup trying to initialise calendar with year=%d", year)
            year = now.year
        elif not 1 <= month <= 12:
            _logger.warning("DateMarkup trying to initialise calendar with month=%d", month)
            month = now.month

        # Compare against from_date
        if from_date and not self._display(year, month, calendar.monthrange(year, month)[1]):
            year = from_date.year
            month = from_date.month

        # Assign all attributes
        self._YEAR = year
        self._MONTH = month
        super().__init__(required, disable_warnings=True)

    def __repr__(self) -> str:
        """Overriden __repr__ of DateMarkup.

        :return: The __repr__ string.
        """

        return BaseMarkup.__repr__(self) + ": required={}, year={}, month={}, from={}" \
            .format(self._REQUIRED, self._YEAR, self._MONTH, self._FROM.strftime(self._FORMAT) if self._FROM else None)

    def __str__(self) -> str:
        """Overriden __str__ of DateMarkup.

        :return: The __str__ string.
        """

        return BaseMarkup.__str__(self) + " with year = {} and month = {}{}\nA response is{} required" \
            .format(self._YEAR, self._MONTH, ", from " + self._FROM.strftime(self._FORMAT) if self._FROM else "",
                    " not" * (not self._REQUIRED))

    # endregion Constructors

    # region Helper functions

    def _display(self, year: int, month: int, day: int) -> bool:
        """Helper function to determine if a date value is after the _FROM date value.

        :param year: The year of the date value.
        :param month The month of the date value.
        :prarm day: The day of the date value.
        :return: True if the date value is after the _FROM date value, False otherwise.
        """

        # Sanity check
        if not 1 <= year <= 9999:
            _logger.error("DateMarkup _display parsing invalid year: %d", year)
            return False
        elif not 1 <= month <= 12:
            _logger.error("DateMarkup _display parsing invalid month: %d", month)
            return False
        elif not 1 <= day <= calendar.monthrange(year, month)[1]:
            _logger.error("DateMarkup _display parsing invalid day: %d", day)
            return False

        return self._FROM is None or \
            datetime(year, month, day) >= datetime(self._FROM.year, self._FROM.month, self._FROM.day)

    @staticmethod
    def _get_next_month(month: int, year: int) -> Tuple[int, int]:
        """Helper function to get the next chronological month of a given month and year.

        :param month: The month to get the next chronological month from.
        :param year: The year to get the next chronological month from.
        :return: The next chronological month and year, if the parsed month and year are valid.
                 If the inputs are not valid, returns the parsed month and year.
        """

        # Sanity check
        if not 1 <= month <= 12:
            _logger.error("DateMarkup _get_next_month Parsed month is not valid: %d", month)
            return month, year
        elif not 1 <= year <= 9999:
            _logger.error("DateMarkup _get_next_month Parsed year is not valid: %d", year)
            return month, year

        month += 1
        if month == 13:
            if year == 9999:
                _logger.warning("DateMarkup _get_next_month Dec 9999 is the maximum year and month")
                month -= 1
            else:
                year += 1
                month = 1
        return month, year

    @staticmethod
    def _get_prev_month(month: int, year: int) -> Tuple[int, int]:
        """Helper function to get the previous chronological month of a given month and year.

        :param month: The month to get the previous chronological month from.
        :param year: The year to get the previous chronological month from.
        :return: The previous chronological month and year, if the parsed month and year are valid.
                 If the inputs are not valid, returns the parsed month and year.
        """

        # Sanity check
        if not 1 <= month <= 12:
            _logger.error("DateMarkup _get_prev_month Parsed month is not valid: %d", month)
            return month, year
        elif not 1 <= year <= 9999:
            _logger.error("DateMarkup _get_prev_month Parsed year is not valid: %d", year)
            return month, year

        month -= 1
        if month == 0:
            if year == 1:
                _logger.warning("DateMarkup _get_prev_month Jan 0001 is the minimum year and month")
                month += 1
            else:
                year -= 1
                month = 12
        return month, year

    @classmethod
    def _is_option(cls, option: str) -> bool:
        """Verify if the option parsed is defined.

        :param option: The option to verify.
        :return: Flag to indicate if the option is defined.
        """

        if option not in (cls._SKIP, cls._IGNORE, cls._PREV_MONTH, cls._NEXT_MONTH):
            try:
                _ = datetime.strptime(option, cls._FORMAT)
            except ValueError:
                return False
        return True

    # endregion Helper functions

    # region Getters

    @classmethod
    def get_format(cls) -> str:
        """Gets the format of the dates.

        :return: The specified date format.
        """

        return cls._FORMAT

    def get_from(self) -> Optional[datetime]:
        """Gets the date from which to display.

        :return: The date from which to display, if any.
        """

        return self._FROM

    @classmethod
    def get_pattern(cls, *_) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        return "^(" + "|".join((cls._SKIP, cls._IGNORE, cls._PREV_MONTH, cls._NEXT_MONTH)) + "|" + \
               cls._FORMAT.replace("%Y", "\\d{4}").replace("%m", "\\d{1,2}").replace("%d", "\\d{1,2}") + ")$"

    def get_markup(self, *_) -> InlineKeyboardMarkup:
        """Initialises the markup with parsed options.

        :return: The inline keyboard markup.
        """

        # region Initialisation

        blank = InlineKeyboardButton(" ", callback_data=self._IGNORE)
        prev_month, prev_year = self._get_prev_month(self._MONTH, self._YEAR)
        next_month, next_year = self._get_next_month(self._MONTH, self._YEAR)
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
                # Previous button
                InlineKeyboardButton("<", callback_data=self._PREV_MONTH)
                if self._display(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1]) else blank,
                # Skip button
                blank if self._REQUIRED else InlineKeyboardButton("Skip", callback_data=self._SKIP),
                # Next button
                InlineKeyboardButton(">", callback_data=self._NEXT_MONTH)
                if self._display(next_year, next_month, calendar.monthrange(next_year, next_month)[1]) else blank
            ]
        ]

        # endregion Initialisation

        # Add year and month
        keyboard.insert(0, [InlineKeyboardButton(calendar.month_name[self._MONTH] + " " + str(self._YEAR),
                                                 callback_data=self._IGNORE)])

        # Add dates
        my_calendar = calendar.monthcalendar(self._YEAR, self._MONTH)
        for week in my_calendar:
            row = [blank if day == 0 or not self._display(self._YEAR, self._MONTH, day) else
                   InlineKeyboardButton(str(day),
                                        callback_data=datetime(self._YEAR, self._MONTH, day).strftime(self._FORMAT))
                   for day in week]
            keyboard.insert(len(keyboard) - 1, row)
        return InlineKeyboardMarkup(keyboard)

    def get_options(self) -> None:
        """Overriding of get_options in BaseOptionMarkup.

        Since this function is not applicable in DateMarkup, it is overriden so as to prevent misuse.
        """
        pass

    # endregion Getters

    def perform_action(self, option: str) -> Optional[Union[InlineKeyboardMarkup, str]]:
        """Perform action according to the callback data.

        :param option: The option received from the callback data.
        :return: The relevant action as determined by the callback data.
        """

        result = None
        if not self._is_option(option):
            _logger.error("DateMarkup perform_action received invalid option: %s", option)
        elif option == self._IGNORE:
            pass
        elif option == self._SKIP:
            result = self.get_required_warning() if self._REQUIRED else self._SKIP
        elif option == self._PREV_MONTH:
            self._MONTH, self._YEAR = self._get_prev_month(self._MONTH, self._YEAR)
            result = self.get_markup()
        elif option == self._NEXT_MONTH:
            self._MONTH, self._YEAR = self._get_next_month(self._MONTH, self._YEAR)
            result = self.get_markup()
        else:
            result = option
        return result


if __name__ == '__main__':
    pass
