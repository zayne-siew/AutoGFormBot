#!/usr/bin/env python3
"""
Handler for Google Form date-time composite questions.

This script allows for the standardised handling of Google Form date-time composite questions.

Usage:
    To get question metadata while checking for success/failure: if not DatetimeQuestion.get_info(): ...
    To answer the question: DatetimeQuestion.answer(hour, minute, date=date) OR
                            DateQuestion.answer(hour, minute, month=month, day=day)

TODO include dependencies
"""

import logging
from selenium.webdriver.remote.webelement import WebElement
from src import Browser
from src.questions import BaseQuestion, DateQuestion, TimeQuestion
from typing import Any, Optional, Tuple

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class DatetimeQuestion(BaseQuestion):
    """
    DatetimeQuestion class as a Google Form date-time composite question wrapper.

    This script merges a DateQuestion and a TimeQuestion instance into one class and provides name-shadowing functions
    to invoke the methods of each question class with one function call.

    Attributes
        _DATE_QUESTION  The DateQuestion instance parsed.
        _TIME_QUESTION  The TimeQuestion instance parsed.
    """

    # region Constructors

    def __init__(self, date_question: DateQuestion, time_question: TimeQuestion) -> None:
        """Initialisation of DatetimeQuestion class.

        :param date_question: The DateQuestion instance to be merged.
        :param time_question: The TimeQuestion instance to be merged.
        """

        # Sanity check
        if not (date_question._get_question_element() == time_question._get_question_element() and
                date_question._BROWSER == time_question._BROWSER):
            _logger.warning("DatetimeQuestion initialising with incompatible DateQuestion and TimeQuestion instances\n"
                            "date_question=%s, time_question=%s", repr(date_question), repr(time_question))

        super().__init__(date_question._get_question_element(), date_question._BROWSER)
        self._DATE_QUESTION = date_question
        self._TIME_QUESTION = time_question

    def __repr__(self) -> str:
        """Overriden __repr__ of DatetimeQuestion class.

        :return: The __repr__ string.
        """

        return "DatetimeQuestion object {}, date_question={}, time_question={}"\
            .format(super().__repr__(), repr(self._DATE_QUESTION), repr(self._TIME_QUESTION))

    def __str__(self) -> str:
        """Overriden __str__ of DatetimeQuestion class.

        :return: The __str__ string.
        """

        return "DatetimeQuestion object:\n\t{}\n\t{}".format(str(self._DATE_QUESTION), str(self._TIME_QUESTION))

    def __eq__(self, other: "DatetimeQuestion") -> bool:
        """Overriden __eq__ of DatetimeQuestion class.

        Two DatetimeQuestion classes are equal if their DateQuestion instance is equal
        and their TimeQuestion instance is equal.

        :param other: The other instance of the DatetimeQuestion class.
        :return: Whether the two instances are equal.
        """

        return self._DATE_QUESTION == other._DATE_QUESTION and self._TIME_QUESTION == other._TIME_QUESTION

    # endregion Constructors

    def _union(self, function: str, has_return: bool, *args: Any, var: Optional[str] = "") -> Any:
        """Helper function to merge function calling into a single function call.

        :param function: The function to call for both date and time instances.
        :param has_return: Flag to indicate if the function should return anything.
        :param args: The arguments to be parsed into the function calls.
        :param var: Variable name to use if an error needs to be thrown.
        :return: Whatever the function should return. If there is an error, return None.
        """

        try:
            date_result = getattr(self._DATE_QUESTION, function)(*args)
            time_result = getattr(self._TIME_QUESTION, function)(*args)
            if has_return:
                if date_result == time_result:
                    return date_result
                else:
                    _logger.error("%s getting different %s from date and time question: "
                                  "%s=%s, %s=%s", self, var, "date_"+var, date_result, "time_"+var, time_result)
        except AttributeError:
            _logger.error("%s function %s is not defined in DateQuestion and/or TimeQuestion", self, function)

    # region Getter methods

    def _get_question_element(self) -> Optional[WebElement]:
        """Gets the web element which represents the entire question.

        :return: The web element which represents the entire question, if it has been successfully set.
        """

        return self._union("_get_question_element", True, var="question_element")

    def get_browser(self) -> Browser:
        """Gets the Browser object.

        :return: The Browser object.
        """

        return self._union("get_browser", True, var="browser")

    def get_header(self) -> Optional[str]:
        """Gets the question header.

        :return: The question header, if it has been successfully set.
        """

        return self._union("get_header", True, var="header")

    def get_description(self) -> Optional[str]:
        """Gets the question description.

        :return: The question description, if it has been successfully set.
        """

        return self._union("get_description", True, var="description")

    def is_required(self) -> Optional[bool]:
        """Checks if the question is required.

        :return: The _REQUIRED flag, if it has been successfully set.
        """

        return self._union("is_required", True, var="required")

    def get_answer_elements(self) -> Optional[Tuple[WebElement, ...]]:
        """Gets the web elements for the date and time input fields.

        :return: The web elements for the date and time input fields, if it has been successfully set.
        """

        date_answer_elements = self._DATE_QUESTION.get_answer_elements()
        date_answer_elements = date_answer_elements if isinstance(date_answer_elements, Tuple) \
            else (date_answer_elements,)
        return self._TIME_QUESTION.get_answer_elements() + date_answer_elements

    # endregion Getter methods

    # region Setter methods

    def _set_header(self, header: str) -> None:
        """Sets the question header.

        The question header is only to be set on __init__ as it is the UID of the class.

        :param header: The question header.
        """

        self._union("_set_header", False, header)

    def set_question_element(self, element: WebElement) -> None:
        """Sets the web element representing the entire question if it has changed.

        :param element: The new web element representing the entire question if it has changed.
        """

        self._union("set_question_element", False, element)

    def set_description(self, description: str) -> None:
        """Sets the question description if it has changed.

        :param description: The new question description.
        """

        self._union("set_description", False, description)

    def set_required(self, required: bool) -> None:
        """Toggles the required flag if it has changed.

        :param required: The new required flag.
        """

        self._union("set_required", False, required)

    # endregion Setter methods

    def get_info(self) -> Optional[bool]:
        """Obtains question metadata from Google Form.

        :return: True if the question metadata has been successfully cached, False otherwise.
                 Returns None only if Browser.monitor_browser returns None.
        """

        # Process DateQuestion.get_info()
        result = self._DATE_QUESTION.get_info()
        if not result:
            return result

        # Process TimeQuestion.get_info()
        result = self._TIME_QUESTION.get_info()
        if not result:
            return result

        # Both get_info() calls passed without error
        return True

    def answer(self, datetime: str) -> Optional[bool]:
        """Answers the question with specified user input.

        :param datetime: Datetime for answering the DateQuestion and TimeQuestion instances.
                         The datetime is expected to be of format "%Y-%m-%d %H:%M"
        :return: True if the question is answered successfully, False if a sanity check fails,
                 and None if _perform_submission returns None.
        """

        date, time = datetime.split(" ")

        # Process DateQuestion.answer()
        result = self._DATE_QUESTION.answer(date)
        if not result:
            return result

        # Process TimeQuestion.answer()
        result = self._TIME_QUESTION.answer(time)
        if not result:
            return result

        # Both answer() calls passed without error
        return True


if __name__ == '__main__':
    pass
