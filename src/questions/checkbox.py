#!/usr/bin/env python3
"""
Handler for Google Form checkbox questions (grid and non-grid based).

This script allows for the standardised handling of the Google Form checkbox questions.

Usage:
    To get question metadata while checking for success/failure:
        if not CheckboxQuestion.get_info(): ...
        if not CheckboxGridQuestion.get_info(): ...
    To answer the question:
        CheckboxQuestion.answer(*answers)
        CheckboxGridQuestion.answer(*answers)

TODO include dependencies
"""

import logging
from selenium.webdriver.remote.webelement import WebElement
from src import Browser
from src.questions import BaseOptionQuestion, BaseOptionGridQuestion
from typing import Optional, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class CheckboxQuestion(BaseOptionQuestion):
    """
    CheckboxQuestion class as a Google Form non-grid checkbox question wrapper.

    This script caches the checkbox elements used for answering along with the options specified
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
    _CHECKBOX_CLASS_NAME = "quantumWizTogglePapercheckboxEl"  # Checkboxes
    _OTHER_CLASS_NAME = "quantumWizTextinputSimpleinputInput"  # 'Other' Input Field
    _OTHER_OPTION_ARIA_LABEL = "Other:"
    _OTHER_OPTION_DATA_ANSWER_VALUE = "__other_option__"

    # region Getters and Setters

    @classmethod
    def get_class_name(cls) -> str:
        """Helper function to get the checkbox web element class name.

        :return: The checkbox web element class name.
        """

        return cls._CHECKBOX_CLASS_NAME

    def get_answer_elements(self) -> Optional[Tuple[WebElement, ...]]:
        """Gets the web elements for the checkbox options.

        :return: The web element for the checkbox options, if it has been successfully set.
        """

        if not self._ANSWER_ELEMENTS:
            _logger.warning("%s trying to get answer elements that have not been set", self.__class__.__name__)
        return self._ANSWER_ELEMENTS

    def set_answer_elements(self, *elements: WebElement) -> None:
        """Sets the web elements for the checkbox options if it has changed.

        :param elements: The web elements for the checkbox options.
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

        result = super().get_info()
        if not result:
            # Cascade the unwanted result
            return result

        # Obtain options and their corresponding elements
        container = self._QUESTION_ELEMENT.find_element_by_class_name(BaseOptionGridQuestion.get_container_class()) \
            if isinstance(self, BaseOptionGridQuestion) else self._QUESTION_ELEMENT
        elements = container.find_elements_by_class_name(self._CHECKBOX_CLASS_NAME)
        option_elements, options = [], []
        for element in elements:
            option = element.get_attribute("aria-label")

            # Sanity check for options
            if option in options:
                # Allow duplicate option but do not append
                _logger.warning("%s get_info found duplicate option", self.__class__.__name__)
            elif not option:
                # Allow blank option but do not append
                _logger.warning("%s get_info found blank option", self.__class__.__name__)

            # Check if there is an 'Other' option specified
            elif option == self._OTHER_OPTION_ARIA_LABEL and \
                    element.get_attribute("data-answer-value") == self._OTHER_OPTION_DATA_ANSWER_VALUE:
                if self._OTHER_OPTION_ELEMENT:  # Using self.get_other_option_element() will trigger a warning
                    # Sanity check
                    _logger.warning("%s get_info found duplicate 'Other' option", self.__class__.__name__)
                    continue
                option_elements.append(element)  # Checkbox associated with the 'Other' option
                self.set_other_option_element(self._QUESTION_ELEMENT.find_element_by_class_name(
                    self._OTHER_CLASS_NAME))  # Input field associated with the 'Other' option

            # Append option
            else:
                options.append(option)
                option_elements.append(element)

        # Finish initialising
        self._set_options(*options, has_other_option=bool(self._OTHER_OPTION_ELEMENT))
        self.set_answer_elements(*option_elements)
        return True

    def answer(self, *answers: str) -> Optional[bool]:
        """Answers the question with specified user input.

        :param answers: The answer(s) to the question.
        :return: True if the question is answered successfully, False if a sanity check fails,
                 and None if _perform_submission returns None.
        """

        # region Sanity checks

        # Sanity check for answers
        if len(answers) == 0:
            _logger.warning("%s trying to answer the question without specifying answers", self.__class__.__name__)
            return True

        # Sanity check for answer elements
        elif not (bool(self.get_answer_elements()) and self._is_valid(*self._ANSWER_ELEMENTS)):
            self._OTHER_OPTION_ELEMENT = None  # Uninitialise 'Other' option web element
            result = self.get_info()
            if not result:
                # Cascade unwanted result
                return result

        # endregion Sanity checks

        found_other_option = False
        for answer in answers:

            if self._is_option(answer):

                # Find the option element that represents the correct option
                option_elements = list(filter(lambda element: element.get_attribute("aria-label") == answer,
                                              self._ANSWER_ELEMENTS))
                assert len(option_elements) > 0  # since _is_option passed
                if len(option_elements) > 1:
                    _logger.warning("%s specified option has duplicate web elements, answer=%s, elements=%s",
                                    self.__class__.__name__, answer, option_elements)
                    # Take the first option to be the selected one

                # Instruction: Click the checkbox corresponding to the answer
                option_elements[0].click()

            elif self._has_other_option():

                # Another 'Other' option has already been recorded, reject current 'Other' option
                if found_other_option:
                    _logger.warning("%s mulitple 'Other' user inputs specified, please debug",
                                    self.__class__.__name__)

                elif self._is_valid(self.get_other_option_element()):

                    # Find the option element that represents the 'Other' option
                    option_elements = list(filter(
                        lambda element:
                        element.get_attribute("data-answer-value") == self._OTHER_OPTION_DATA_ANSWER_VALUE,
                        self._ANSWER_ELEMENTS))
                    assert len(option_elements) > 0  # since _has_other_option passed
                    if len(option_elements) > 1:
                        _logger.warning("%s question has duplicate 'Other' web elements, please debug",
                                        self.__class__.__name__)
                        # Take the first option to be the selected one

                    # Instruction: Click the checkbox corresponding to the 'Other' option,
                    #              then click the input field corresponding to the 'Other' option,
                    #              then type the answer into the input field
                    option_elements[0].click()
                    self.get_other_option_element().click()
                    self.get_other_option_element().send_keys(answer)
                    found_other_option = True

                # Sanity check for invalid 'Other' option input field
                else:
                    _logger.error("%s 'Other' option is not specified", self.__class__.__name__)
                    return

            # Sanity check for unspecified option
            else:
                _logger.error("%s specified option is not defined, answer=%s", self.__class__.__name__, answer)
                return False

        return True


class CheckboxGridQuestion(BaseOptionGridQuestion, CheckboxQuestion):
    """
    CheckboxGridQuestion class as a Google Form grid-based checkbox question wrapper.

    This script caches the checkbox option elements used for answering along with the options specified
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
        """Initialisation of CheckboxGridQuestion class.

        :param question_element: The web element which represents the entire question.
        :param browser: The selenium browser instance used to host the Google Form.
        """

        BaseOptionGridQuestion.__init__(self, question_element, browser)

    def __repr__(self) -> str:
        """Overriden __repr__ of CheckboxGridQuestion class.

        :return: The __repr__ string.
        """

        return BaseOptionGridQuestion.__repr__(self)

    def __str__(self) -> str:
        """Overriden __str__ of CheckboxGridQuestion class.

        :return: The __str__ string.
        """

        return BaseOptionGridQuestion.__str__(self)

    # endregion Constructors

    def _format_and_answer(self, sub_question: str, *answers: str) -> Optional[bool]:
        """Helper function to format and submit answers to the format for grid-based options.

        The formatted answers should be of format "<answer>, response for <sub_question>"
        which is the same format that the options are stored as.

        :param sub_question: The sub_question to format.
        :param answers: The answers to format.
        :return: The result from super().answer()
        """

        # Sanity check
        if len(answers) == 0:
            _logger.warning("CheckboxGridQuestion trying to format answers that are not specified")
            return True

        return CheckboxQuestion.answer(self, *(answer + self._DELIMITER + sub_question for answer in answers))

    def get_info(self) -> Optional[bool]:
        """Obtains question metadata from Google Form.

        :return: True if the question metadata has been successfully cached, False otherwise.
                 Returns None only if Browser.monitor_browser returns None.
        """

        return CheckboxQuestion.get_info(self)

    def answer(self, *answers: Union[str, Tuple[str, ...]]) -> Optional[bool]:
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
            _logger.error("CheckboxGridQuestion trying to answer %d sub-questions with %d answers\n"
                          "answers=%s, sub_questions=%s", len(sub_questions), len(answers), answers, sub_questions)
            return

        for answer, sub_question in zip(answers, sub_questions):
            if not answer:
                continue
            elif isinstance(answer, Tuple):
                result = self._format_and_answer(sub_question, *answer)
            else:
                result = self._format_and_answer(sub_question, answer)
            if not result:
                # Cascade unwanted result
                return result
        return True


if __name__ == '__main__':
    pass
