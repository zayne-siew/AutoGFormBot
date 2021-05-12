#!/usr/bin/env python3
"""
Handler for Google Form drop-down questions.

This script allows for the standardised handling of the Google Form drop-down questions.

Usage:
    To get question metadata while checking for success/failure: if not DropdownQuestion.get_info(): ...
    To answer the question: DropdownQuestion.answer(answer)

TODO include dependencies
"""

from browser import Browser
import logging
from questions.base import BaseOptionQuestion
from selenium.webdriver.remote.webelement import WebElement
import time
from typing import Optional, Tuple

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class DropdownQuestion(BaseOptionQuestion):
    """
    DropdownQuestion class as a Google Form drop-down question wrapper.

    This script caches the drop-down option elements used for answering along with the options specified
    and awaits user input to submit.
    NOTE: Option elements are NOT stored in cache since the drop-down menu is to be closed.
          Upon re-opening, the IDs of the menu elements will change.

    Attributes
        _HEADER                 The Google Form question header (title); also serves as the UID for the question class.
        _DESCRIPTION            The Google Form question description.
        _REQUIRED               The required flag for the Google Form question.
        _QUESTION_ELEMENT       The web element in the Google Form which represents the entire Google Form question.
        _ANSWER_ELEMENTS        The web element(s) in the Google Form which are used to answer the Google Form question.
        _BROWSER                The selenium browser instance used to host the Google Form.
        _OPTIONS                The options defined by the Google Form question.
        _OTHER_OPTION_ELEMENT   The input field for the 'Other' option, if an 'Other' option is defined.
    """

    # Define constants
    _DROPDOWN_CLASS_NAME = "quantumWizMenuPaperselectOption"  # Drop-down Options
    _DROPDOWN_MENU_CLASS_NAME = "quantumWizMenuPaperselectPopup"  # Drop-down Menu
    _PLACEHOLDER_CLASS_NAME = "isPlaceholder"  # Drop-down placeholder
    _BUFFER_SECONDS = 1

    # region Getters and Setters

    @classmethod
    def get_class_name(cls) -> str:
        """Helper function to get the drop-down option web element class name.

        :return: The drop-down option web element class name.
        """

        return cls._DROPDOWN_CLASS_NAME

    def get_answer_elements(self) -> Optional[Tuple[WebElement, WebElement]]:
        """Gets the web elements for the drop-down input fields.

        :return: (The web element for the drop-down placeholder, the web element for the drop-down menu)
                 if it has been successfully set.
        """

        if not self._ANSWER_ELEMENTS:
            _logger.warning("DropdownQuestion trying to get elements that have not been set")
        return self._ANSWER_ELEMENTS

    def set_answer_elements(self, placeholder: WebElement, menu: WebElement) -> None:
        """Sets the web elements for the drop-down input fields if it has changed.

        Stores the web elements in the following format:
        (The web element for the drop-down placeholder, the web element for the drop-down menu).

        :param placeholder: The web element for the drop-down placeholder.
        :param menu: The web element for the drop-down menu.
        """

        self._ANSWER_ELEMENTS = placeholder, menu

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

        # Display drop-down menu using placeholder element
        # There should only be one such element
        placeholder = self._QUESTION_ELEMENT.find_element_by_class_name(self._PLACEHOLDER_CLASS_NAME)
        placeholder.click()
        time.sleep(self._BUFFER_SECONDS)

        # With drop-down menu displayed, crawl for options
        menu = self._QUESTION_ELEMENT.find_element_by_class_name(self._DROPDOWN_MENU_CLASS_NAME)
        menu_elements = menu.find_elements_by_class_name(self._DROPDOWN_CLASS_NAME)
        options = [element.text for element in menu_elements[1:]]

        # Simple sanity check, should not trigger
        if "" in options:
            _logger.warning("DropdownQuestion found blank option, please debug")
            options = list(filter(lambda option: option, options))

        # Cache web elements and options
        self.set_answer_elements(placeholder, menu)
        self._set_options(*options)
        menu_elements[0].click()
        time.sleep(self._BUFFER_SECONDS)
        return True

    @Browser.monitor_browser
    def answer(self, text: str) -> Optional[bool]:
        """Answers the question with specified user input.

        :param text: The answer to the question.
        :return: True if the question is answered successfully, False if a sanity check fails,
                 and None if _perform_submission returns None.
        """

        # region Sanity checks

        # Sanity check for web elements
        if not (self._get_question_element() and self._is_valid(self._QUESTION_ELEMENT)):
            # Refresh the question element before retrying
            return False
        elif not (bool(self.get_answer_elements()) and self._is_valid(*self._ANSWER_ELEMENTS)):
            result = self.get_info()
            if not result:
                # Cascade unwanted result
                return result

        # Sanity check for options
        if not self._is_option(text):
            _logger.error("DropdownQuestion specified option is not defined, text=%s", text)
            return False

        # endregion Sanity checks

        # Find the option element that contains the chosen option
        placeholder, menu = self.get_answer_elements()
        placeholder.click()
        time.sleep(self._BUFFER_SECONDS)
        menu_elements = menu.find_elements_by_class_name(self._DROPDOWN_CLASS_NAME)
        menu_elements = list(filter(lambda element: element.text == text, menu_elements[1:]))
        assert len(menu_elements) > 0  # Since sanity check passed
        if len(menu_elements) > 1:
            _logger.warning("DropdownQuestion specified option has duplicate web elements, "
                            "text=%s, elements=%s", text, menu_elements)
            # Take the first option to be the selected one

        # Instruction: Click the menu option
        menu_elements[0].click()
        time.sleep(self._BUFFER_SECONDS)
        return True


if __name__ == '__main__':
    pass
