#!/usr/bin/env python3
"""
Handler for Google Form date questions.

This script allows for the standardised handling of the Google Form date questions.

Usage:
    To get question metadata while checking for success/failure: if not DateQuestion.get_info(): ...
    To answer the question: DateQuestion.answer(date=date) OR DateQuestion.answer(month=month, day=day)

TODO include dependencies
"""

from browser import Browser
from calendar import monthrange
from datetime import datetime
import logging
from questions.base import BaseQuestion
from selenium.webdriver.remote.webelement import WebElement
from typing import Optional, Tuple, Union

# region Define constants

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)

# Define date formats
_INPUT_FORMAT = "%Y %m %d"
_ANSWER_FORMAT = "%d%m%Y"

# endregion Define constants


class DateQuestion(BaseQuestion):
    """
    DateQuestion class as a Google Form date question wrapper.

    This script caches the date input field(s) used for answering and awaits user input to submit.
    It also validates user input before submission of date answer.

    Attributes
        _HEADER             The Google Form question header (title); also serves as the UID for the question class.
        _DESCRIPTION        The Google Form question description.
        _REQUIRED           The required flag for the Google Form question.
        _QUESTION_ELEMENT   The web element in the Google Form which represents the entire Google Form question.
        _ANSWER_ELEMENTS    The web element(s) in the Google Form which are used to answer the Google Form question.
        _BROWSER            The selenium browser instance used to host the Google Form.
        _INPUT_FORMAT       The date format expected for date string answers.
        _ANSWER_FORMAT      The date format to format date string answers to for submission.
    """

    # Define constants
    _DATE_TYPE = "date"
    _DAY_ARIA_LABEL = "Day of the month"
    _MONTH_ARIA_LABEL = "Month"

    # region Constructors

    def __init__(self, question_element: WebElement, browser: Browser, input_format: Optional[str] = _INPUT_FORMAT,
                 answer_format: Optional[str] = _ANSWER_FORMAT) -> None:
        """Initialisation of DateQuestion class.

        :param question_element: The web element which represents the entire question.
        :param browser: The selenium browser instance used to host the Google Form.
        :param input_format: The date format expected for date string answers.
        :param answer_format: The date format to format date string answers to for submission.
        """

        super().__init__(question_element, browser)
        self._INPUT_FORMAT = input_format
        self._ANSWER_FORMAT = answer_format

    def __repr__(self) -> str:
        """Overriden __repr__ of DateQuestion class.

        :return: The __repr__ string.
        """

        return super().__repr__() + ", input_format={}, answer_format={}" \
            .format(self._INPUT_FORMAT, self._ANSWER_FORMAT)

    # endregion Constructors

    # region Getters and Setters

    def get_answer_elements(self) -> Optional[Union[WebElement, Tuple[WebElement, WebElement]]]:
        """Gets the web element for the date input field(s).

        Returns either the date picker element or (month element, date element),
        depending on which one was found in the browser.

        :return: The web element(s) for the date input field(s), if it has been successfully set.
        """

        if not self._ANSWER_ELEMENTS:
            _logger.warning("%s trying to get answer element that has not been set", self.__class__.__name__)
        return self._ANSWER_ELEMENTS

    def set_answer_elements(self, *, date_picker_element: Optional[WebElement] = None,
                            month_element: Optional[WebElement] = None,
                            day_element: Optional[WebElement] = None) -> None:
        """Sets the web element(s) for the date input field(s) if it has changed.

        Sets either the date picker element or (month element, day element),
        depending on which one was found in the browser.

        :param date_picker_element: The web element for the date picker input field.
        :param month_element: The web element for the month input field.
        :param day_element: The web element for the day input field.
        """

        warning = "{} trying to set answer elements with date_picker_element={}, month_element={}, " \
                  "day_element={}".format(self.__class__.__name__, date_picker_element, month_element, day_element)

        # Sanity check
        if not (date_picker_element or (month_element and day_element)):
            _logger.warning(warning)
            return
        elif date_picker_element and (month_element or day_element):
            # Choose the date picker by default since it is easier to handle
            _logger.warning(warning)

        # Set the answer elements based on defined variables
        self._ANSWER_ELEMENTS = date_picker_element if date_picker_element else (month_element, day_element)

    # endregion Getters and Setters

    @Browser.monitor_browser
    def get_info(self) -> Optional[bool]:
        """Obtains question metadata from Google Form.

        :return: True if the question metadata has been successfully cached, False otherwise.
                 Returns None only if Browser.monitor_browser returns None.
        """

        result = super().get_info()
        if not result:
            # Cascade the unwanted result
            return result

        # Obtain the input field(s)
        date_picker_elements = self._QUESTION_ELEMENT.find_elements_by_xpath(
            ".//input[contains(@type, '{}')]".format(self._DATE_TYPE))
        month_elements = self._QUESTION_ELEMENT.find_elements_by_xpath(
            ".//input[contains(@aria-label, '{}')]".format(self._MONTH_ARIA_LABEL))
        day_elements = self._QUESTION_ELEMENT.find_elements_by_xpath(
            ".//input[contains(@aria-label, '{}')]".format(self._DAY_ARIA_LABEL))

        # If date picker element found, set this as answer element
        if date_picker_elements:
            if len(date_picker_elements) > 1:
                _logger.warning("%s found multiple date picker elements", self.__class__.__name__)
                # Assume the first element is the correct one
            self.set_answer_elements(date_picker_element=date_picker_elements[0])
            return True

        # If month and date element found, use this instead
        elif month_elements and day_elements:
            if len(month_elements) > 1:
                _logger.warning("%s found multiple month elements", self.__class__.__name__)
                # Assume the first element is the correct one
            if len(day_elements) > 1:
                _logger.warning("%s found multiple day elements", self.__class__.__name__)
                # Assume the first element is the correct one
            self.set_answer_elements(month_element=month_elements[0], day_element=day_elements[0])
            return True

        # Nothing found, log error
        else:
            _logger.error("%s no date picker, month or day elements found", self.__class__.__name__)
            return

    def answer(self, *, date: Optional[str] = None, month: Optional[str] = None, day: Optional[str] = None) -> \
            Optional[bool]:
        """Answers the question with specified user input.

        :param date: The date answer to the question.
        :param month: The month answer to the question.
        :param day: The day answer to the question.
        :return: True if the question is answered successfully, False if a sanity check fails,
                 and None if _perform_submission returns None.
        """

        # region Sanity checks for answer element(s)

        if (not bool(self.get_answer_elements())) or \
                (isinstance(self._ANSWER_ELEMENTS, Tuple) and not self._is_valid(*self._ANSWER_ELEMENTS)) or \
                (isinstance(self._ANSWER_ELEMENTS, WebElement) and not self._is_valid(self._ANSWER_ELEMENTS)):
            result = self.get_info()
            if not result:
                # Cascade unwanted result
                return result

        # endregion Sanity checks for answer element(s)

        # region Sanity checks for input(s)

        # Initialise warnings
        input_warning = "{} trying to answer question with date={}, month={}, day={}" \
            .format(self.__class__.__name__, date, month, day)
        mismatch_warning = "{} trying to answer {} with {}, date={}, month={}, day={}" \
            .format(self.__class__.__name__,
                    "date picker" if isinstance(self._ANSWER_ELEMENTS, WebElement) else "month, date",
                    "date string" if date else "month, date", date, month, day)

        # Sanity check for input(s)
        if not (date or (month and day)):
            _logger.error(input_warning)
            return
        elif date and (month or day):
            _logger.warning(input_warning)

        if isinstance(self._ANSWER_ELEMENTS, WebElement) and not date:
            _logger.error(mismatch_warning)
            return
        elif isinstance(self._ANSWER_ELEMENTS, Tuple) and not (month and day):
            _logger.error(mismatch_warning)
            return

        # endregion Sanity checks for input(s)

        if isinstance(self._ANSWER_ELEMENTS, WebElement):

            # Check for valid date string
            try:
                date_time = datetime.strptime(date, self._INPUT_FORMAT)
                if date_time > datetime(2071, 1, 1):
                    raise ValueError
                date = date_time.strftime(self._ANSWER_FORMAT)
            except ValueError:
                _logger.error("%s trying to answer a date with date=%s", self.__class__.__name__, date)
                return False

            # Instruction: Click the date picker input field and enter the date string
            self._ANSWER_ELEMENTS.click()
            self._ANSWER_ELEMENTS.send_keys(date)

        else:

            # Check for valid month and day
            try:
                month_int, day_int = int(month), int(day)
                # Use 2020 as day check since 2020 is a leap year; allow upper bound
                if not (1 <= month_int <= 12 and 1 <= day_int <= monthrange(2020, month_int)[1]):
                    raise ValueError
            except ValueError:
                _logger.error("%s trying to answer a date with month=%s, day=%s",
                              self.__class__.__name__, month, day)
                return False

            # Instruction: Click the month input field and enter the month,
            #              then click the day input field and enter the day
            for element, answer in zip(self._ANSWER_ELEMENTS, (month, day)):
                element.click()
                element.send_keys(answer)

        return True


if __name__ == '__main__':
    pass
