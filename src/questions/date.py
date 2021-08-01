#!/usr/bin/env python3
"""
Handler for Google Form date questions.

This script allows for the standardised handling of the Google Form date questions.

Usage:
    To get question metadata while checking for success/failure: if not DateQuestion.get_info(): ...
    To answer the question: DateQuestion.answer(date=date) OR DateQuestion.answer(month=month, day=day)

TODO include dependencies
"""

from datetime import datetime
import logging
from selenium.webdriver.remote.webelement import WebElement
from src import Browser
from src.questions import BaseQuestion
from typing import Optional, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


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
    """

    # Define constants
    _DATE_TYPE = "date"
    _DAY_ARIA_LABEL = "Day of the month"
    _MONTH_ARIA_LABEL = "Month"

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

    def answer(self, date: str) -> Optional[bool]:
        """Answers the question with specified user input.

        :param date: The date answer to the question.
                     The parsed date is expected to be of format "%Y-%m-%d".
        :return: True if the question is answered successfully, False if a sanity check fails,
                 and None if _perform_submission returns None.
        """

        # Sanity checks for answer element(s)
        if (not bool(self.get_answer_elements())) or \
                (isinstance(self._ANSWER_ELEMENTS, Tuple) and not self._is_valid(*self._ANSWER_ELEMENTS)) or \
                (isinstance(self._ANSWER_ELEMENTS, WebElement) and not self._is_valid(self._ANSWER_ELEMENTS)):
            result = self.get_info()
            if not result:
                # Cascade unwanted result
                return result

        # Check for valid date string
        try:
            date_time = datetime.strptime(date, "%Y-%m-%d")
            if date_time > datetime(2071, 1, 1):
                raise ValueError
            day, month, year = date_time.day, date_time.month, date_time.year
        except ValueError:
            _logger.error("%s trying to answer a date with date=%s", self.__class__.__name__, date)
            return False
        assert bool(isinstance(val, int) for val in (date, month, year))

        # Send instructions to Google Forms
        if isinstance(self._ANSWER_ELEMENTS, WebElement):
            self._ANSWER_ELEMENTS.click()
            self._ANSWER_ELEMENTS.send_keys(str(day) + str(month) + str(year))
        else:
            for element, answer in zip(self._ANSWER_ELEMENTS, (month, day)):
                element.click()
                element.send_keys(answer)
        return True


if __name__ == '__main__':
    pass
