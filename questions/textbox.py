#!/usr/bin/env python3
"""
Handler for Google Form short-answer questions (textboxes).

This script allows for the standardised handling of the Google Form short-answer questions.

Usage:
    TODO

TODO include dependencies
"""

from browser import Browser
from questions.base import BaseQuestion
from selenium.webdriver.remote.webelement import WebElement
from typing import Optional, Tuple, Union


class SAQuestion(BaseQuestion):
    """
    SAQuestion class as generic Google Form question wrapper.

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

    def get_answer_elements(self) -> WebElement:
        """Gets the web element for the textbox input field.

        :return: The web element for the textbox input field.
        """

        return self._ANSWER_ELEMENTS

    def _set_answer_elements(self, element: WebElement) -> None:
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
        if result:
            # Obtain the answer element
            self._set_answer_elements(self._QUESTION_ELEMENT.find_element_by_class_name(self._SAQ_CLASS_NAME))
            return True
        else:
            # Cascade the unwanted result
            return result

    def answer(self, text: str) -> Tuple[WebElement, Optional[Union[str, WebElement]], Optional[str]]:
        """Provide instruction to answer the question.

        :param text: The answer to the question.
        :return: The instruction to perform.
        """

        # Instruction: Click the input field and enter text
        return self.get_answer_elements(), text, None


if __name__ == '__main__':
    pass
