#!/usr/bin/env python3
"""
Handler class for Google Form time questions.

This script allows for the standardised handling of the Google Form time questions.

Usage:
    To get question metadata while checking for success/failure: if not TimeQuestion.get_info(): ...
    To answer the question: TimeQuestion.answer(hour, minute)

TODO include dependencies
"""

from browser import Browser
import logging
from questions import BaseQuestion
from selenium.webdriver.remote.webelement import WebElement
from typing import Optional, Tuple

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class TimeQuestion(BaseQuestion):
    """
    TimeQuestion class as a Google Form time question wrapper.

    This script caches the hour and minute input fields used for answering and awaits user input.
    It also validates hour and minute user input before submission of time answer.

    Attributes
        _HEADER             The Google Form question header (title); also serves as the UID for the question class.
        _DESCRIPTION        The Google Form question description.
        _REQUIRED           The required flag for the Google Form question.
        _QUESTION_ELEMENT   The web element in the Google Form which represents the entire Google Form question.
        _ANSWER_ELEMENTS    The web element(s) in the Google Form which are used to answer the Google Form question.
        _BROWSER            The selenium browser instance used to host the Google Form.
    """

    # Define constants
    _TIME_HOUR_ARIA_LABEL = "Hour"
    _TIME_MINUTE_ARIA_LABEL = "Minute"

    # region Getters and Setters

    @classmethod
    def get_hour_label(cls) -> str:
        """Helper function to get the hour web element aria label.

        :return: The hour web element aria label.
        """

        return cls._TIME_HOUR_ARIA_LABEL

    @classmethod
    def get_minute_label(cls) -> str:
        """Helper function to get the minute web element aria label.

        :return: The minute web element aria label.
        """

        return cls._TIME_MINUTE_ARIA_LABEL

    def get_answer_elements(self) -> Optional[Tuple[WebElement, WebElement]]:
        """Gets the web elements for the hour and minute input fields.

        :return: (Web element for the hour input field, web element for the minute input field),
                 if it has been successfully set.
        """

        if not self._ANSWER_ELEMENTS:
            _logger.warning("%s trying to get answer element that has not been set", self.__class__.__name__)
        return self._ANSWER_ELEMENTS

    def set_answer_elements(self, hour_element: WebElement, minute_element: WebElement) -> None:
        """Sets the web element for the hour and minute input fields if it has changed.

        :param hour_element: The web element for the hour input field.
        :param minute_element: The web element for the minute input field.
        """

        self._ANSWER_ELEMENTS = hour_element, minute_element

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

        # Obtain the input fields
        hour_elements = self._QUESTION_ELEMENT.find_elements_by_xpath(
            ".//input[@aria-label='{}']".format(self._TIME_HOUR_ARIA_LABEL))
        minute_elements = self._QUESTION_ELEMENT.find_elements_by_xpath(
            ".//input[@aria-label='{}']".format(self._TIME_MINUTE_ARIA_LABEL))

        # Sanity check
        if len(hour_elements) == 0 or len(minute_elements) == 0:
            _logger.error("%s hour elements and/or minute elements not found, hour_elements=%s minute_elements=%s",
                          self.__class__.__name__, hour_elements, minute_elements)
            return
        if len(hour_elements) > 1:
            _logger.warning("%s found multiple hour elements", self.__class__.__name__)
            # Assume the first element is the correct one
        if len(minute_elements) > 1:
            _logger.warning("%s found multiple minute elements", self.__class__.__name__)
            # Assume the first element is the correct one

        self.set_answer_elements(hour_elements[0], minute_elements[0])
        return True

    def answer(self, time: str) -> Optional[bool]:
        """Answers the question with specified user input.

        :param time: The time answer to the question.
                     The time answer is expected to be of format "%H:%M".
        :return: True if the question is answered successfully, False if a sanity check fails,
                 and None if _perform_submission returns None.
        """

        # Sanity check for answer elements
        if not (bool(self.get_answer_elements()) and self._is_valid(*self._ANSWER_ELEMENTS)):
            result = self.get_info()
            if not result:
                # Cascade unwanted result
                return result

        # Ensure valid inputs
        try:
            hour, minute = time.split(":")
            hour, minute = int(hour), int(minute)
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            _logger.error("%s trying to answer a time with time=%s", self.__class__.__name__, time)
            return False
        assert bool(isinstance(val, int) for val in (hour, minute))

        # Send instructions to Google Forms
        for element, answer in zip(self._ANSWER_ELEMENTS, (hour, minute)):
            element.click()
            element.send_keys(answer)
        return True


if __name__ == '__main__':
    pass
