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
from markups import BaseMarkup, BaseOptionMarkup
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
        _FROM       The date to display the time picker from.
    """

    # Define constants
    _MIN_SEC = "MIN_SEC"
    _HOUR_GROUP = "HOUR_GROUP"
    _CHOOSE_HOUR = "CHOOSE_HOUR"
    _CHOOSE_MINUTE = "CHHOSE_MINUTE"
    _CHOOSE_SECOND = "CHOOSE_SECOND"
    _CHOOSE_AM_PM = "CHOOSE_AM_PM"
    _FINALISE = "FINALISE"
    _IGNORE = "IGNORE"
    _FORMAT = "%H:$M"

    # region Constructors

    def __init__(self, required: bool, *, hour: Optional[int] = None, minute: Optional[int] = None,
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
        if second is not None:
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
        self._FROM = None
        super().__init__(required, disable_warnings=True)

    def __repr__(self) -> str:
        """Overriden __repr__ of TimeMarkup.

        :return: The __repr__ string.
        """

        return BaseMarkup.__repr__(self) + ": required={}, hour={}, minute={}, second={}, from={}" \
            .format(self._REQUIRED, self._HOUR, self._MINUTE, self._SECOND,
                    self._FROM.strftime(self._FORMAT) if self._FROM else None)

    def __str__(self) -> str:
        """Overriden __str__ of TimeMarkup.

        :return: The __str__ string.
        """

        return BaseMarkup.__str__(self) + " displaying {}:{}{}{}\nA response is{} required" \
            .format(self._HOUR, self._MINUTE, (":" + str(self._SECOND)) * bool(self._SECOND),
                    ", from " + self._FROM.strftime(self._FORMAT) if self._FROM else "", " not" * (not self._REQUIRED))

    # endregion Constructors

    # region Helper functions

    def _display(self, hour: int, minute: int) -> bool:
        """Helper function to determine if a date value is after the _FROM date value.

        :param hour: The hour of the date value.
        :prarm minute: The minute of the date value.
        :return: True if the date value is after the _FROM date value, False otherwise.
        """

        # Sanity check
        if not 0 <= hour <= 23:
            _logger.error("TimeMarkup _display parsing invalid hour: %d", hour)
            return False
        elif not 0 <= minute <= 59:
            _logger.error("TimeMarkup _display parsing invalid minute: %d", minute)
            return False

        return self._FROM is None or datetime(self._FROM.year, self._FROM.month, self._FROM.day, hour, minute) \
            .replace(tzinfo=timezone.utc) >= self._FROM

    @classmethod
    def _is_option(cls, option: str) -> bool:
        """Verify if the option parsed is defined.

        :param option: The option to verify.
        :return: Flag to indicate if the option is defined.
        """

        def _valid_int(*args: str) -> bool:
            """Helper function to check if a string is a valid 2-digit positive integer.

            :param args: The strings to check.
            :return: True if all strings are valid, False otherwise.
            """

            # Sanity check
            if len(args) == 0:
                _logger.info("TimeMarkup _valid_int No values received")

            for arg in args:
                try:
                    if not 0 <= int(arg) <= 99:
                        raise ValueError
                except ValueError:
                    return False
            return True

        if option in (cls._SKIP, cls._CHOOSE_HOUR, cls._CHOOSE_MINUTE, cls._CHOOSE_SECOND,
                      cls._CHOOSE_AM_PM, cls._FINALISE, cls._IGNORE):
            return True
        elif " " in option and (cls._MIN_SEC in option or cls._HOUR_GROUP in option):
            args = option.split(" ")
            return 2 <= len(args) <= 3 and _valid_int(*args[1:])
        else:
            return _valid_int(option)

    # endregion Helper functions

    # region Markup functions

    def _min_sec(self, start: int) -> InlineKeyboardMarkup:
        """Helper function to display 10 minute/second values from a certain value.

        :param start: The start value (inclusive) to display.
        :return: The inline keyboard markup instance.
        """

        markup = [[InlineKeyboardButton(str(start + i * 2 + j), callback_data=str(start + i * 2 + j))
                   if self._SECOND is not None or self._display(self._HOUR, start + i * 2 + j)
                   else InlineKeyboardButton(" ", callback_data=self._IGNORE) for j in range(2)] for i in range(5)]
        return InlineKeyboardMarkup(markup)

    def _time_hour(self, pm: bool) -> InlineKeyboardMarkup:
        """Helper function to display 1-12 as time hour values.

        :param pm: Flag to indicate if the hour values are AM or PM.
        :return: The inline keyboard markup instance.
        """

        markup = [[InlineKeyboardButton("{}{}".format(str(i * 2 + j + 12 * int(i == j == 0)), "PM" if pm else "AM"),
                                        callback_data=str(i * 2 + j + 12 * int(pm)))
                   if self._display(i * 2 + j + 12 * int(pm), self._MINUTE)
                   else InlineKeyboardButton(" ", callback_data=self._IGNORE) for j in range(2)] for i in range(6)]
        return InlineKeyboardMarkup(markup)

    def _duration_hour(self, start: int, stop: int) -> InlineKeyboardMarkup:
        """Helper function to display duration hour values within a certain range.

        :param start: The start value (inclusive) to display.
        :param stop: The stop value (inclusive) to display. Expecting either start - stop = 11 or 12.
                     If the stop value is not valid, the function defaults to start + 11.
        :return: The inline keyboard markup instance.
        """

        # Sanity check
        if not 11 <= stop - start <= 12:
            _logger.warning("TimeMarkup _duration_hour invalid start and stop parsed: start=%d, stop=%d", start, stop)
            stop = start + 11

        blank = InlineKeyboardButton(" ", callback_data=self._IGNORE)
        markup = [[InlineKeyboardButton(str(start + i * 3 + j), callback_data=str(start + i * 3 + j))
                   for j in range(3)] for i in range(4)]
        if stop - start == 12:
            markup.append([blank, InlineKeyboardButton(str(stop), callback_data=str(stop)), blank])
        return InlineKeyboardMarkup(markup)

    def _min_sec_group(self) -> InlineKeyboardMarkup:
        """Helper function to display 6 groups of minute/second values.

        :return: The inline keyboard markup instance.
        """

        markup = [[InlineKeyboardButton("{} - {}".format(10 * (i * 2 + j), 10 * (i * 2 + j + 1) - 1),
                                        callback_data="{} {}".format(self._MIN_SEC, 10 * (i * 2 + j)))
                   if self._SECOND is not None or self._display(self._HOUR, 10 * (i * 2 + j + 1) - 1)
                   else InlineKeyboardButton(" ", callback_data=self._IGNORE) for j in range(2)] for i in range(3)]
        return InlineKeyboardMarkup(markup)

    def _hour_group(self) -> InlineKeyboardMarkup:
        """Helper function to display 6 groups of duration hour values.

        :return: The inline keyboard markup instance.
        """

        groups = ((0, 11), (12, 23), (24, 35), (36, 47), (48, 59), (60, 72))
        markup = [[InlineKeyboardButton("{} - {}".format(*groups[i * 2 + j]),
                                        callback_data="{} {} {}".format(self._HOUR_GROUP, *groups[i * 2 + j]))
                   for j in range(2)] for i in range(3)]
        return InlineKeyboardMarkup(markup)

    # endregion Markup functions

    # region Getters

    @classmethod
    def get_pattern(cls, *_) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        num_regex = "\\d{1,2}"
        return "^(" + "|".join((cls._SKIP, cls._FINALISE, cls._IGNORE, cls._CHOOSE_HOUR, cls._CHOOSE_MINUTE,
                                cls._CHOOSE_SECOND, cls._CHOOSE_AM_PM, "{} {}".format(cls._MIN_SEC, num_regex),
                                "{0} {1} {1}".format(cls._HOUR_GROUP, num_regex), num_regex)) + ")$"

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
                InlineKeyboardButton("{:02d}".format(self._HOUR - 12 * (self._SECOND is None and self._HOUR > 12)),
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

    def set_from(self, from_date: datetime) -> None:
        """Sets the date to display the time picker from.

        :param from_date: The date to display the time picker from.
        """

        self._FROM = from_date
        if self._HOUR < from_date.hour:
            self._HOUR = from_date.hour
            self._MINUTE = from_date.minute
        elif self._MINUTE < from_date.minute:
            self._MINUTE = from_date.minute

    def perform_action(self, option: str) -> Optional[Union[InlineKeyboardMarkup, str]]:
        """Perform action according to the callback data.

        :param option: The option received from the callback data.
        :return: The relevant action as determined by the callback data.
        """

        result = None
        if not self._is_option(option):
            _logger.error("TimeMarkup perform_action received invalid option: %s", option)
        elif option == self._IGNORE:
            pass
        elif option == self._SKIP:
            result = self.get_required_warning() if self._REQUIRED else self._SKIP
        elif option == self._CHOOSE_HOUR:
            result = self._time_hour(self._HOUR >= 12) if self._SECOND is None else self._hour_group()
            self._HOUR = -1
        elif option == self._CHOOSE_MINUTE:
            self._MINUTE = -1
            result = self._min_sec_group()
        elif option == self._CHOOSE_SECOND:
            self._SECOND = -1
            result = self._min_sec_group()
        elif option == self._CHOOSE_AM_PM:
            if self._display((self._HOUR + 12) % 24, self._MINUTE):
                self._HOUR = (self._HOUR + 12) % 24
                result = self.get_markup()
        elif self._MIN_SEC in option:
            result = self._min_sec(int(option[option.index(" ") + 1:]))
        elif self._HOUR_GROUP in option:
            start, stop = option.split(" ")[1:]
            result = self._duration_hour(int(start), int(stop))
        elif option == self._FINALISE:
            result = "{:02d}:{:02d}{}".format(self._HOUR, self._MINUTE,
                                              "" if self._SECOND is None else ":{:02d}".format(self._SECOND))
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
