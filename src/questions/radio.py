#!/usr/bin/env python3
"""
Handler for Google Form radio button questions (grid and non-grid based).

This script allows for the standardised handling of the Google Form radio button questions.

Usage:
    To get question metadata while checking for success/failure:
        if not RadioQuestion.get_info(): ...
        if not RadioGridQuestion.get_info(): ...
    To answer the question:
        RadioQuestion.answer(answer)
        RadioGridQuestion.answer(*answers)

TODO include dependencies
"""

import logging
from selenium.webdriver.remote.webelement import WebElement
from src import Browser
from src.questions import BaseOptionQuestion, BaseOptionGridQuestion
from typing import Optional, Tuple

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class RadioQuestion(BaseOptionQuestion):
    """
    RadioQuestion class as a Google Form non-grid radio button question wrapper.

    This script caches the radio button option elements used for answering along with the options specified
    and awaits user input to submit.

    Attributes
        _HEADER                 The Google Form question header (title); also serves as the UID for the question class.
        _DESCRIPTION            The Google Form question description.
        _REQUIRED               The required flag for the Google Form question.
        _QUESTION_ELEMENT       The web element in the Google Form which represents the entire Google Form question.
        _ANSWER_ELEMENTS        The web element(s) in the Google Form which are used to answer the Google Form question.
        _BROWSER                The selenium browser instance used to host the Google Form.
        _OPTIONS                The options defined by the Google Form question.
        _OTHER_OPTION_ELEMENT   The input field for the 'Other' option, if an 'Other' option is defined.
        _OTHER_OPTION_LABEL     The text to replace the blank aria label for any specified 'Other' options.
    """

    # Define constants
    _RADIO_CLASS_NAME = "appsMaterialWizToggleRadiogroupEl"  # Radio buttons
    _OTHER_CLASS_NAME = "quantumWizTextinputSimpleinputInput"  # 'Other' Input Field
    _OTHER_OPTION_DATA_VALUE = "__other_option__"

    # region Getters and Setters

    @classmethod
    def get_class_name(cls) -> str:
        """Helper function to get the radio button web element class name.

        :return: The radio button web element class name.
        """

        return cls._RADIO_CLASS_NAME

    def get_answer_elements(self) -> Optional[Tuple[WebElement, ...]]:
        """Gets the web elements for the radio button options.

        :return: The web element for the radio button options, if it has been successfully set.
        """

        if not self._ANSWER_ELEMENTS:
            _logger.warning("%s trying to get answer elements that have not been set", self.__class__.__name__)
        return self._ANSWER_ELEMENTS

    def set_answer_elements(self, *elements: WebElement) -> None:
        """Sets the web elements for the radio button options if it has changed.

        :param elements: The web elements for the radio button options.
        """

        # Sanity check
        if len(elements) == 0:
            _logger.warning("%s trying to set answer elements without any elements", self.__class__.__name__)
        self._ANSWER_ELEMENTS = tuple(element for element in elements)

    # endregion Getters and Setters

    @Browser.monitor_browser
    def get_info(self) -> Optional[bool]:
        """Obtains question metadata from Google Form.

        :return: True if the question metadata has been successfully cached, False otherwise.
                 Returns None only if Browser.monitor_browser returns None.
        """

        # Cascade unwanted result from super().get_info()
        result = super().get_info()
        if not result:
            return result

        # Obtain options and their corresponding elements
        container = self._QUESTION_ELEMENT.find_element_by_class_name(BaseOptionGridQuestion.get_container_class()) \
            if isinstance(self, BaseOptionGridQuestion) else self._QUESTION_ELEMENT
        elements = container.find_elements_by_class_name(self._RADIO_CLASS_NAME)
        option_elements, options = [], []
        for element in elements:
            option = element.get_attribute("aria-label")

            # Check for duplicate option
            if option in options:
                _logger.warning("%s get_info found duplicate option", self.__class__.__name__)

            elif not option:

                # Check if there is an 'Other' option specified
                if element.get_attribute("data-value") == self._OTHER_OPTION_DATA_VALUE:
                    if self._OTHER_OPTION_ELEMENT:
                        # Sanity check
                        _logger.warning("%s get_info found duplicate 'Other' option", self.__class__.__name__)
                        continue
                    option_elements.append(element)  # Radio button associated with the 'Other' option
                    self.set_other_option_element(self._QUESTION_ELEMENT.find_element_by_class_name(
                        self._OTHER_CLASS_NAME))  # Input field associated with the 'Other' option

                # Blank option detected
                else:
                    _logger.warning("%s get_info found blank option", self.__class__.__name__)

            # Append option
            else:
                options.append(option)
                option_elements.append(element)

        # Finally, cache options and option elements
        self._set_options(*options, has_other_option=bool(self._OTHER_OPTION_ELEMENT))
        self.set_answer_elements(*option_elements)
        return True

    def answer(self, text: str) -> Optional[bool]:
        """Answers the question with specified user input.

        :param text: The answer to the question.
        :return: True if the question is answered successfully, False if a sanity check fails,
                 and None if _perform_submission returns None.
        """

        # Sanity check
        if not (bool(self.get_answer_elements()) and self._is_valid(*self._ANSWER_ELEMENTS)):
            result = self.get_info()
            if not result:
                # Cascade unwanted result
                return result

        if self._is_option(text):

            # Find the option element that represents the correct option
            option_elements = list(filter(lambda element: element.get_attribute("aria-label") == text,
                                          self._ANSWER_ELEMENTS))
            assert len(option_elements) > 0  # since _is_option passed
            if len(option_elements) > 1:
                _logger.warning("%s specified option has duplicate web elements, text=%s, elements=%s",
                                self.__class__.__name__, text, option_elements)
                # Take the first option to be the selected one

            # Instruction: Click the radio button corresponding to the answer
            option_elements[0].click()

        elif self._has_other_option():

            # Sanity check for invalid 'Other' option input field
            if not self._is_valid(self.get_other_option_element()):
                _logger.error("%s 'Other' option is not specified", self.__class__.__name__)
                return

            # Find the option element that represents the 'Other' option
            option_elements = list(filter(
                lambda element: element.get_attribute("data-value") == self._OTHER_OPTION_DATA_VALUE,
                self._ANSWER_ELEMENTS))
            assert len(option_elements) > 0  # since _has_other_option passed
            if len(option_elements) > 1:
                _logger.warning("%s question has duplicate 'Other' web elements, please debug",
                                self.__class__.__name__)
                # Take the first option to be the selected one

            # Instruction: Click the radio button corresponding to the 'Other' option,
            #              then click the input field corresponding to the 'Other' option,
            #              then type the answer into the input field
            option_elements[0].click()
            self.get_other_option_element().click()
            self.get_other_option_element().send_keys(text)

        # Sanity check for unspecified option
        else:
            _logger.error("%s specified option is not defined, text=%s", self.__class__.__name__, text)
            return False

        return True


class RadioGridQuestion(BaseOptionGridQuestion, RadioQuestion):
    """
    RadioGridQuestion class as a Google Form grid-based radio button question wrapper.

    This script caches the radio button option elements used for answering along with the options specified
    and awaits user input to submit.

    Attributes
        _HEADER                 The Google Form question header (title); also serves as the UID for the question class.
        _DESCRIPTION            The Google Form question description.
        _REQUIRED               The required flag for the Google Form question.
        _QUESTION_ELEMENT       The web element in the Google Form which represents the entire Google Form question.
        _ANSWER_ELEMENTS        The web element(s) in the Google Form which are used to answer the Google Form question.
        _BROWSER                The selenium browser instance used to host the Google Form.
        _OPTIONS                The options defined by the Google Form question.
        _OTHER_OPTION_ELEMENT   The input field for the 'Other' option, if an 'Other' option is defined.
        _OTHER_OPTION_LABEL     The text to replace the blank aria label for any specified 'Other' options.
        _SUB_QUESTIONS          The sub-questions defined in the grid.
    """

    # region Constructors

    def __init__(self, question_element: WebElement, browser: Browser) -> None:
        """Initialisation of RadioGridQuestion class.

        :param question_element: The web element which represents the entire question.
        :param browser: The selenium browser instance used to host the Google Form.
        """

        BaseOptionGridQuestion.__init__(self, question_element, browser)

    def __repr__(self) -> str:
        """Overriden __repr__ of RadioGridQuestion class.

        :return: The __repr__ string.
        """

        return BaseOptionGridQuestion.__repr__(self)

    def __str__(self) -> str:
        """Overriden __str__ of RadioGridQuestion class.

        :return: The __str__ string.
        """

        return BaseOptionGridQuestion.__str__(self)

    # endregion Constructors

    def get_info(self) -> Optional[bool]:
        """Obtains question metadata from Google Form.

        :return: True if the question metadata has been successfully cached, False otherwise.
                 Returns None only if Browser.monitor_browser returns None.
        """

        return RadioQuestion.get_info(self)

    def answer(self, *answers: str) -> Optional[bool]:
        """Answers the question with specified user input.

        :param answers: The answers to the question.
                        The function assumes that the answers are parsed in the same order that the
                        sub-questions are stored in.
        :return: True if the question is answered successfully, False if a sanity check fails,
                 and None if _perform_submission returns None.
        """

        # Sanity check
        sub_questions = self.get_sub_questions()
        if not len(answers) == len(sub_questions):
            _logger.error("RadioGridQuestion trying to answer %d sub-questions with %d answers\n"
                          "answers=%s, sub_questions=%s", len(sub_questions), len(answers), answers, sub_questions)
            return

        for answer, sub_question in zip(answers, sub_questions):
            # Format each answer back to the "CCC, response for RRR" format
            # Which is the format in which the options are stored as
            answer += self._DELIMITER + sub_question
            result = RadioQuestion.answer(self, answer)
            if not result:
                return result
        return True


if __name__ == '__main__':
    pass
