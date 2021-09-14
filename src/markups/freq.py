#!/usr/bin/env python3
"""
Handler for frequency selection menu as Telegram inline keyboard markup.

This script standardises the initialisation of a frequency selection menu.

Usage:
    TODO usage
    To obtain the pattern regex for CallbackQueryHandlers: markup.get_pattern()
    To initialise a menu keyboard markup: markup.get_markup()
    To process the callback data obtained: markup.perform_action(option)

TODO include dependencies
"""

import logging
from markups import BaseMarkup, BaseOptionMarkup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class FreqMarkup(BaseMarkup):
    """FreqMarkup class for frequency selection menus as Telegram inline keyboards.

    Attributes
        _OPTIONS        Defined options available in the options menu.
    """

    # Define constants
    _MONTHLY = "Submit monthly"
    _WEEKLY = "Submit weekly"
    _DAILY = "Submit daily"
    _HOURLY = "Submit hourly"
    _CUSTOM = "Custom"

    # region Get constants

    @classmethod
    def get_monthly(cls) -> str:
        """Gets the monthly constant.

        :return: The monthly constant.
        """

        return cls._MONTHLY

    @classmethod
    def get_weekly(cls) -> str:
        """Gets the weekly constant.

        :return: The weekly constant.
        """

        return cls._WEEKLY

    @classmethod
    def get_daily(cls) -> str:
        """Gets the daily constant.

        :return: The daily constant.
        """

        return cls._DAILY

    @classmethod
    def get_hourly(cls) -> str:
        """Gets the hourly constant.

        :return: The hourly constant.
        """

        return cls._HOURLY

    @classmethod
    def get_custom(cls) -> str:
        """Gets the custom constant.

        :return: The custom constant.
        """

        return cls._CUSTOM

    # endregion Get constants

    @classmethod
    def get_pattern(cls, *_) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        return super().get_pattern(cls._MONTHLY, cls._WEEKLY, cls._DAILY, cls._HOURLY, cls._CUSTOM)

    @classmethod
    def is_option(cls, option: str) -> bool:
        """Checks if the option parsed is defined.

        :param option: The option parsed.
        :return: Whether the option is defined.
        """

        return option in (cls._MONTHLY, cls._WEEKLY, cls._DAILY, cls._HOURLY, cls._CUSTOM)

    @classmethod
    def get_markup(cls, *_) -> InlineKeyboardMarkup:
        """Sets the frequency options to the markup.

        :return: The inline keyboard markup.
        """

        return super().get_markup((cls._HOURLY, cls._DAILY), (cls._WEEKLY, cls._MONTHLY), cls._CUSTOM)


class FreqCustomMarkup(BaseOptionMarkup):
    """FreqCustomMarkup class for frequency customisation menus as Telegram inline keyboards.

    Attributes
        _OPTIONS    Defined options available in the options menu.
        _REQUIRED   Flag to indicate if a response is required.
        _DAYS       The number of days to display.
        _HOURS      The number of hours to display.
        _MINUTES    The number of minutes to display.
    """

    # Define constants
    _CHOOSE_DAY = "CHOOSE_DAY"
    _CHOOSE_HOUR = "CHOOSE_HOUR"
    _CHOOSE_MINUTE = "CHOOSE_MINUTE"
    _SHOW_MINUTE = "SHOW_MINUTE"
    _IGNORE = "IGNORE"
    _FINALISE = "FINALISE"

    # region Constructors

    def __init__(self) -> None:
        """Initialisation of FreqCustomMarkup class."""

        self._DAYS = 0
        self._HOURS = 0
        self._MINUTES = 0
        super().__init__(True, disable_warnings=True)

    def __repr__(self) -> str:
        """Overriden __repr__ of FreqCustomMarkup.

        :return: The __repr__ string.
        """

        return BaseMarkup.__repr__(self) + ": required={}, days={}, hours={}, minutes={}" \
            .format(self._REQUIRED, self._DAYS, self._HOURS, self._MINUTES)

    def __str__(self) -> str:
        """Overriden __str__ of FreqCustomMarkup.

        :return: The __str__ string.
        """

        return BaseMarkup.__str__(self) + " displaying {}d {}h {}min".format(self._DAYS, self._HOURS, self._MINUTES)

    # endregion Constructors

    # region Helper functions

    @staticmethod
    def valid_freq(days: int, hours: int, minutes: int) -> bool:
        """Determine if the frequency selected is valid.

        A frequency is considered valid if its duration falls between
        5 minutes (includive) and 400 days (exclusive).

        :param days: The days of the frequency.
        :param hours: The hours of the frequency.
        :param minutes: The minutes of the frequency.
        :return: True if the frequency is valid, False otherwise.
        """

        # Sanity check
        if days < 0 or not 0 <= hours <= 23 or not 0 <= minutes <= 59:
            _logger.error("FreqCustomMarkup _valid_freq Invalid input parsed: days=%d, hours=%d, minutes=%d",
                          days, hours, minutes)
            return False

        return hours == minutes == 0 if days == 400 else days < 400 and (days > 0 or hours > 0 or minutes >= 5)

    @classmethod
    def _is_option(cls, option: str) -> bool:
        """Verify if the option parsed is defined.

       :param option: The option to verify.
       :return: Flag to indicate if the option is defined.
       """

        def _valid_int(value: str) -> bool:
            """Helper function to check if a string is a valid positive integer.

            :param value: The string to check.
            :return: True if the string is valid, False otherwise.
            """

            try:
                if not 0 <= int(value) <= 999:
                    raise ValueError
                return True
            except ValueError:
                return False

        return option in (cls._CHOOSE_HOUR, cls._CHOOSE_MINUTE, cls._FINALISE, cls._IGNORE) or _valid_int(option) \
            or (" " in option and (cls._CHOOSE_DAY in option or cls._SHOW_MINUTE in option) and
                _valid_int(option[option.index(" ") + 1:]))

    # endregion Helper functions

    # region Markup functions

    def _minute(self, start: int) -> InlineKeyboardMarkup:
        """Helper function to display 10 minute values from a certain value.

        :param start: The start value (inclusive) to display.
        :return: The inline keyboard markup instance.
        """

        markup = [[InlineKeyboardButton(str(start + i * 2 + j), callback_data=str(start + i * 2 + j))
                   if self.valid_freq(self._DAYS, self._HOURS, start + i * 2 + j)
                   else InlineKeyboardButton(" ", callback_data=self._IGNORE) for j in range(2)] for i in range(5)]
        return InlineKeyboardMarkup(markup)

    def _hour(self) -> InlineKeyboardMarkup:
        """Helper function to display all hour values.

        :return: The inline keyboard markup instance.
        """

        markup = [[InlineKeyboardButton(str(i * 6 + j), callback_data=str(i * 6 + j))
                   if self.valid_freq(self._DAYS, i * 6 + j, self._MINUTES)
                   else InlineKeyboardButton(" ", callback_data=self._IGNORE) for j in range(6)] for i in range(4)]
        return InlineKeyboardMarkup(markup)

    def _day(self, start: Optional[int] = 0) -> InlineKeyboardMarkup:
        """Helper function to display 30 date values from a certain value.

        :param start: The start value (inclusive) to display from.
        :return: THe inline keyboard markup instance.
        """

        blank = InlineKeyboardButton(" ", callback_data=self._IGNORE)
        markup = [[InlineKeyboardButton(str(start + i * 5 + j), callback_data=str(start + i * 5 + j))
                   if self.valid_freq(start + i * 5 + j, self._HOURS, self._MINUTES)
                   else blank for j in range(5)] for i in range(6)]
        markup.append([InlineKeyboardButton("<", callback_data="{} {}".format(self._CHOOSE_DAY, max(start - 30, 0)))
                       if start > 0 else blank,
                       blank,
                       InlineKeyboardButton(">", callback_data="{} {}".format(self._CHOOSE_DAY, min(start + 30, 371)))
                       if start < 371 else blank])
        return InlineKeyboardMarkup(markup)

    def _minute_group(self) -> InlineKeyboardMarkup:
        """Helper function to display 6 groups of minute values.

        :return: The inline keyboard markup instance.
        """

        markup = [[InlineKeyboardButton("{} - {}".format(10 * (i * 2 + j), 10 * (i * 2 + j + 1) - 1),
                                        callback_data="{} {}".format(self._SHOW_MINUTE, 10 * (i * 2 + j)))
                   for j in range(2)] for i in range(3)]
        return InlineKeyboardMarkup(markup)

    # endregion Markup functions

    # region Getters

    @classmethod
    def get_invalid_message(cls) -> str:
        """Obtains the invalid frequency message.

        :return: The invalid frequency message.
        """

        return "ALERT: Selected frequency is invalid!"

    @classmethod
    def get_pattern(cls, *_) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        num_regex = "\\d{1,3}"
        return "^(" + "|".join((cls._SKIP, cls._FINALISE, cls._IGNORE, cls._CHOOSE_HOUR, cls._CHOOSE_MINUTE,
                                "{} {}".format(cls._CHOOSE_DAY, num_regex),
                                "{} {}".format(cls._SHOW_MINUTE, num_regex), num_regex)) + ")$"

    def get_markup(self, *_) -> InlineKeyboardMarkup:
        """Initialises the markup with parsed options.

        :return: The inline keyboard markup.
        """

        markup = [
            # First row containing display headers
            [
                InlineKeyboardButton("Days", callback_data=self._IGNORE),
                InlineKeyboardButton("Hours", callback_data=self._IGNORE),
                InlineKeyboardButton("Minutes", callback_data=self._IGNORE)
            ],
            # Second row containing values
            [
                InlineKeyboardButton(str(self._DAYS), callback_data=self._CHOOSE_DAY + " 0"),
                InlineKeyboardButton(str(self._HOURS), callback_data=self._CHOOSE_HOUR),
                InlineKeyboardButton(str(self._MINUTES), callback_data=self._CHOOSE_MINUTE)
            ],
            # Last row containing confirmation button
            [InlineKeyboardButton("OK", callback_data=self._FINALISE)]
        ]
        return InlineKeyboardMarkup(markup)

    def get_options(self) -> None:
        """Overriding of get_options in BaseOptionMarkup.

        Since this function is not applicable in FreqCustomMarkup, it is overriden so as to prevent misuse.
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
            _logger.error("FreqCustomMarkup perform_action Received unrecognised callback data: %s", option)
        elif option == self._IGNORE:
            pass
        elif option == self._CHOOSE_HOUR:
            self._HOURS = -1
            result = self._hour()
        elif option == self._CHOOSE_MINUTE:
            self._MINUTES = -1
            result = self._minute_group()
        elif self._CHOOSE_DAY in option:
            self._DAYS = -1
            result = self._day(int(option[option.index(" ") + 1:]))
        elif self._SHOW_MINUTE in option:
            result = self._minute(int(option[option.index(" ") + 1:]))
        elif option == self._FINALISE:
            result = "{}d {}h {}min".format(self._DAYS, self._HOURS, self._MINUTES) \
                if self.valid_freq(self._DAYS, self._HOURS, self._MINUTES) else self.get_invalid_message()
        else:
            # Assign the values back to the main markup menu
            if self._DAYS == -1:
                self._DAYS = int(option)
            elif self._HOURS == -1:
                self._HOURS = int(option)
            elif self._MINUTES == -1:
                self._MINUTES = int(option)
            else:
                # Something wrong happened
                _logger.error("FreqCustomMarkup trying to assign user chosen value but none available to assign\n"
                              "days=%s, hours=%s, minutes=%s, option=%s",
                              self._DAYS, self._HOURS, self._MINUTES, option)
                return
            result = self.get_markup()
        return result


if __name__ == '__main__':
    pass
