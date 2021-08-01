#!/usr/bin/env python3
"""
Handler for custom date-time picker as Telegram inline keyboard markup.

This script standardises the initialisation of custom date-time pickers.

Usage:
    To obtain the pattern regex for CallbackQueryHandlers: DatetimeMarkup.get_pattern()
    To initialise a date-time picker keyboard markup: markup.get_markup()
    To process the callback data obtained: markup.perform_action(option)

TODO include dependencies
"""

import logging
from src.markups import BaseMarkup, BaseOptionMarkup, DateMarkup, TimeMarkup
from telegram import InlineKeyboardMarkup
from typing import Optional, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class DatetimeMarkup(BaseOptionMarkup):
    """DatetimeMarkup class for custom reusable date-time pickers as Telegram inline keyboards.

    Attributes
        _OPTIONS        Defined options available in the options menu.
        _REQUIRED   Flag to indicate if a response is required.
        _DATE_MARKUP    DateMarkup instance to display date picker.
        _TIME_MARKUP    TimeMarkup instance to display time picker.
        _DATE_ANSWER    Stores user input for date.
    """

    # region Constructors

    def __init__(self, required: bool, year: Optional[int] = None, month: Optional[int] = None,
                 hour: Optional[int] = None, minute: Optional[int] = None, second: Optional[int] = None) -> None:
        """Initialisation of DatetimeMarkup class.

        :param required: Flag to indicate if a response is required.
        :param year: The year of the calendar to display.
        :param month: The month of the calendar to display.
        :param hour: The hour of the time picker to display.
        :param minute: The minute of the time picker to display.
        :param second: The second of the time picker to display.
        """

        self._DATE_MARKUP = DateMarkup(required, year, month)
        self._TIME_MARKUP = TimeMarkup(required, hour, minute, second)
        self._DATE_ANSWER = None
        super().__init__(required, disable_warnings=True)

    def __repr__(self) -> str:
        """Overriden __repr__ of DatetimeMarkup.

        :return: The __repr__ string.
        """

        return BaseMarkup.__repr__(self) + ": date_markup={}, time_markup={}, date_answer={}" \
            .format(repr(self._DATE_MARKUP), repr(self._TIME_MARKUP), self._DATE_ANSWER)

    def __str__(self) -> str:
        """Overriden __str__ of DatetimeMarkup class.

        :return: The __str__ string.
        """

        return BaseMarkup.__str__(self) + ":\n{}\n{}\nSelected date: {}" \
            .format(self._DATE_MARKUP, self._TIME_MARKUP, self._DATE_ANSWER)

    # endregion Constructors

    # region Getters

    @classmethod
    def get_pattern(cls, *_) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        date_regex = DateMarkup.get_pattern()[2:-2]
        time_regex = TimeMarkup.get_pattern()[2:-2]
        return "^(" + "|".join(set.union(set(date_regex.split("|")), set(time_regex.split("|")))) + ")$"

    def get_markup(self, *_) -> InlineKeyboardMarkup:
        """Initialises the markup with parsed options.

        :return: The inline keyboard markup.
        """

        return self._TIME_MARKUP.get_markup() if bool(self._DATE_ANSWER) else self._DATE_MARKUP.get_markup()

    def get_options(self) -> None:
        """Overriding of get_options in BaseOptionMarkup.

        Since this function is not applicable in DatetimeMarkup, it is overriden so as to prevent misuse.
        """
        pass

    # endregion Getters

    def perform_action(self, option: str) -> Optional[Union[InlineKeyboardMarkup, str]]:
        """Perform action according to the callback data.

        :param option: The option received from the callback data.
        :return: The relevant result, according to either the DateMarkup or TimeMarkup function.
        """

        if self._DATE_ANSWER:
            result = self._TIME_MARKUP.perform_action(option)
            if isinstance(result, str):
                if result not in (self.get_required_warning(), self._SKIP):
                    # Expecting time answer (in format %H:%M(:%S))
                    result = "{} {}".format(self._DATE_ANSWER, result)
        else:
            result = self._DATE_MARKUP.perform_action(option)
            if isinstance(result, str) and result not in (self.get_required_warning(), self._SKIP):
                # Expecting date answer (in format %Y-%m-%d)
                self._DATE_ANSWER = result
                result = self._TIME_MARKUP.get_markup()
        return result


if __name__ == '__main__':
    pass
