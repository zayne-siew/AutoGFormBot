#!/usr/bin/env python3
"""
Base class for Google Form questions.

This script standardises the initialisation and base functionality of a question class.

Usage:
    This script should not be used directly, other than its base class functionalities.

TODO include dependencies
"""

from browser import Browser
from questions.abstract import AbstractQuestion
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from typing import Any, Optional, Tuple, Union


class BaseQuestion(AbstractQuestion):
    """
    BaseQuestion class as generic Google Form question wrapper.

    This script caches the necessary question metadata and web elements required for answering.
    This speeds up the performing of answer submission to the Google Form,
    and it also serves as a marker for when a server-side / network-side error occurs.

    Attributes
        _HEADER             The Google Form question header (title); also serves as the UID for the question class.
        _DESCRIPTION        The Google Form question description.
        _REQUIRED           The required flag for the Google Form question.
        _QUESTION_ELEMENT   The web element in the Google Form which represents the entire Google Form question.
        _ANSWER_ELEMENTS    The web element(s) in the Google Form which are used to answer the Google Form question.
        _BROWSER            The selenium browser instance used to host the Google Form.
    """

    # Define constants
    _TITLE_CLASS_NAME = "freebirdFormviewerComponentsQuestionBaseTitle"  # Question Title
    _DESCRIPTION_CLASS_NAME = "freebirdFormviewerComponentsQuestionBaseDescription"  # Question Description
    _REQUIRED_CLASS_NAME = "freebirdFormviewerComponentsQuestionBaseRequiredAsterisk"  # Required Asterisk

    # region Constructors

    def __init__(self, question_element: WebElement, browser: Browser) -> None:
        """Initialisation of BaseQuestion class.

        :param question_element: The web element which represents the entire question.
        :param browser: The selenium browser instance used to host the Google Form.
        """

        # Initialise variables
        self._HEADER = ""
        self._DESCRIPTION = ""
        self._REQUIRED = False
        self._QUESTION_ELEMENT = question_element
        self._ANSWER_ELEMENTS = None
        self._BROWSER = browser

        self.get_info()

    def __repr__(self) -> str:
        """Overriden __repr__ of BaseQuestion class.

        :return: The __repr__ string.
        """

        return super().__repr__() + \
            ": header={}, description={}, required={}, question_element={}, answer_elements={}" \
            .format(self._HEADER, self._DESCRIPTION, self._REQUIRED, self._QUESTION_ELEMENT, self._ANSWER_ELEMENTS)

    def __str__(self) -> str:
        """Overriden __str__ of BaseQuestion class.

        :return: The __str__ string.
        """

        return "{} object with header: {}".format(self.__class__.__name__, self._HEADER)

    def __eq__(self, other) -> bool:
        """Overriden __eq__ of BaseQuestion class.

        Two BaseQuestion classes are equal if their headers are equal.

        :param other: The other instance of the BaseQuestion class.
        :return: Whether the two instances are equal.
        """

        return self._HEADER == other.get_header()

    # endregion Constructors

    # region Getter methods

    def _get_question_element(self) -> WebElement:
        """Gets the web element which represents the entire question.

        :return: The web element which represents the entire question.
        """

        return self._QUESTION_ELEMENT

    def get_header(self) -> str:
        """Gets the question header.

        :return: The question header.
        """

        return self._HEADER

    def get_description(self) -> str:
        """Gets the question description.

        :return: The question description.
        """

        return self._DESCRIPTION

    def is_required(self) -> bool:
        """Checks if the question is required.

        :return: The _REQUIRED flag.
        """

        return self._REQUIRED

    def get_answer_elements(self) -> Any:
        """Gets the web elements related to answering of the question.

        For BaseQuestion, answer_elements functions are not implemented.
        """
        pass

    # endregion Getter methods

    # region Setter methods

    def _set_header(self, header: str) -> None:
        """Sets the question header.

        The question header is only to be set on __init__ as it is the UID of the class.

        :param header: The question header.
        """

        self._HEADER = header

    def _set_question_element(self, element: WebElement) -> None:
        """Sets the web element representing the entire question if it has changed.

        :param element: The new web element representing the entire question if it has changed.
        """

        self._QUESTION_ELEMENT = element

    def _set_answer_elements(self, *args, **kwargs) -> None:
        """Sets the web elements required for answering the question if it has changed.

        For BaseQuestion, answer_elements functions are not implemented.
        """
        pass

    def set_description(self, description: str) -> None:
        """Sets the question description if it has changed.

        :param description: The new question description.
        """

        self._DESCRIPTION = description

    def set_required(self, required: bool) -> None:
        """Toggles the required flag if it has changed.

        :param required: The new required flag.
        """

        self._REQUIRED = required

    # endregion Setter methods

    @Browser.monitor_browser
    def _is_valid(self, element: WebElement) -> bool:
        """Check if the web element is still valid.

        :param element: The web element to validate.
        :return: True if the web element can be found, False otherwise.
                 Returns None only if Browser.monitor_browser returns None.
        """

        return bool(self._BROWSER.get_browser().find_elements_by_id(element.id))

    @Browser.monitor_browser
    def get_info(self) -> Optional[bool]:
        """Obtains question metadata from Google Form.

        For BaseQuestion, answer_elements functions are not implemented.

        :return: True if the question metadata has been successfully cached, False otherwise.
                 Returns None only if Browser.monitor_browser returns None.
        """

        # Check if the browser has been reset
        if not self._is_valid(self._QUESTION_ELEMENT):
            return False

        # Obtain the question metadata
        header = str(self._QUESTION_ELEMENT.find_element_by_class_name(self._TITLE_CLASS_NAME).text)
        self.set_description(str(self._QUESTION_ELEMENT.find_element_by_class_name(self._DESCRIPTION_CLASS_NAME).text))
        try:
            self.set_required(bool(self._QUESTION_ELEMENT.find_element_by_class_name(self._REQUIRED_CLASS_NAME)))
            # Remove the ' *' that suffixes every required question header
            header = header[:len(header) - 2]
        except NoSuchElementException:
            self.set_required(False)
        finally:
            self._set_header(header)

        # Omit obtaining the answer element(s)
        return True

    def answer(self, *args, **kwargs) -> Tuple[WebElement, Optional[Union[str, WebElement]], Optional[str]]:
        """Provide instruction to answer the question.

        For BaseQuestion, answer_elements functions are not implemented.
        """
        pass


if __name__ == '__main__':
    pass
