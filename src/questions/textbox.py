#!/usr/bin/env python3
"""
Handler for Google Form short-answer questions (textboxes).

This script allows for the standardised handling of the Google Form short-answer questions.

Usage:
    To get question metadata while checking for success/failure: if not SAQuestion.get_info(): ...
    To answer the question: SAQuestion.answer(answer)

TODO include dependencies
"""

import logging
from selenium.webdriver.remote.webelement import WebElement
from src import Browser
from src.questions import BaseQuestion
from typing import Optional

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class SAQuestion(BaseQuestion):
    """
    SAQuestion class as a Google Form short-answer question wrapper.

    This script caches the text input field used for answering and awaits user input to submit.

    Attributes
        _HEADER             The Google Form question header (title); also serves as the UID for the question class.
        _DESCRIPTION        The Google Form question description.
        _REQUIRED           The required flag for the Google Form question.
        _QUESTION_ELEMENT   The web element in the Google Form which represents the entire Google Form question.
        _ANSWER_ELEMENTS    The web element(s) in the Google Form which are used to answer the Google Form question.
        _BROWSER            The selenium browser instance used to host the Google Form.
    """

    # Define constants
    _SAQ_CLASS_NAME = "quantumWizTextinputPaperinputInput"

    # region Getters and Setters

    @classmethod
    def get_class_name(cls) -> str:
        """Helper function to get the textbox web element class name.

        :return: The textbox web element class name.
        """

        return cls._SAQ_CLASS_NAME

    def get_answer_elements(self) -> Optional[WebElement]:
        """Gets the web element for the textbox input field.

        :return: The web element for the textbox input field, if it has been successfully set.
        """

        if not self._ANSWER_ELEMENTS:
            _logger.warning("SAQuestion trying to get answer element that has not been set")
        return self._ANSWER_ELEMENTS

    def set_answer_elements(self, element: WebElement) -> None:
        """Sets the web element for the textbox input field if it has changed.

        :param element: The web element for the textbox input field.
        """

        self._ANSWER_ELEMENTS = element

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

        # Obtain the answer element
        self.set_answer_elements(self._QUESTION_ELEMENT.find_element_by_class_name(self._SAQ_CLASS_NAME))
        return True

    def answer(self, text: str) -> Optional[bool]:
        """Answers the question with specified user input.

        :param text: The answer to the question.
        :return: True if the question is answered successfully, False if a sanity check fails,
                 and None if _perform_submission returns None.
        """

        if not (bool(self.get_answer_elements()) and self._is_valid(self._ANSWER_ELEMENTS)):
            result = self.get_info()
            if not result:
                # Cascade unwanted result
                return result

        # Instruction: Click the input field and enter text
        self._ANSWER_ELEMENTS.click()
        self._ANSWER_ELEMENTS.send_keys(text)
        return True


if __name__ == '__main__':
    pass
