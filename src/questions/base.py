#!/usr/bin/env python3
"""
Base classes for Google Form questions.

This script standardises the initialisation and base functionality of a question class.

Usage:
    This script should not be used directly, other than its base class functionalities.

TODO include dependencies
"""

import logging
import re
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.remote.webelement import WebElement
from src import Browser, utils
from src.questions import AbstractQuestion, AbstractOptionQuestion
from typing import Any, Optional, Tuple

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


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
        self._QUESTION_ELEMENT = question_element
        self._BROWSER = browser
        self._HEADER = None
        self._DESCRIPTION = None
        self._REQUIRED = None
        self._ANSWER_ELEMENTS = None

    def __repr__(self) -> str:
        """Overriden __repr__ of BaseQuestion class.

        :return: The __repr__ string.
        """

        return super().__repr__() + \
            ": header={}, description={}, required={}, question_element={}, answer_elements={}, browser={}" \
            .format(self._HEADER, self._DESCRIPTION, self._REQUIRED, repr(self._QUESTION_ELEMENT),
                    repr(self._ANSWER_ELEMENTS), repr(self._BROWSER))

    def __str__(self) -> str:
        """Overriden __str__ of BaseQuestion class.

        :return: The __str__ string.
        """

        return "{} object with header: {}".format(self.__class__.__name__, self._HEADER)

    def __eq__(self, other: "BaseQuestion") -> bool:
        """Overriden __eq__ of BaseQuestion class.

        Two BaseQuestion classes are equal if their Browser objects are equal
        and their relevant metadata (namely, header, description and required flag) are equal.

        :param other: The other instance of the BaseQuestion class.
        :return: Whether the two instances are equal.
        """

        return self._BROWSER == other._BROWSER and self._HEADER == other._HEADER \
            and self._DESCRIPTION == other._DESCRIPTION and self._REQUIRED == other._REQUIRED

    # endregion Constructors

    # region Getter methods

    def _get_question_element(self) -> Optional[WebElement]:
        """Gets the web element which represents the entire question.

        :return: The web element which represents the entire question, if it has been successfully set.
        """

        if not self._QUESTION_ELEMENT:
            _logger.warning("%s trying to get question element that has not been set yet", self.__class__.__name__)
        return self._QUESTION_ELEMENT

    def get_browser(self) -> Browser:
        """Gets the Browser object.

        :return: The Browser object.
        """

        return self._BROWSER

    def get_header(self) -> Optional[str]:
        """Gets the question header.

        :return: The question header, if it has been successfully set.
        """

        if not isinstance(self._HEADER, str):
            _logger.warning("%s trying to get header that has not been set yet", self.__class__.__name__)
        return self._HEADER

    def get_description(self) -> Optional[str]:
        """Gets the question description.

        :return: The question description, if it has been successfully set.
        """

        if not isinstance(self._DESCRIPTION, str):
            _logger.warning("%s trying to get description that has not been set yet", self.__class__.__name__)
        return self._DESCRIPTION

    def is_required(self) -> Optional[bool]:
        """Checks if the question is required.

        :return: The _REQUIRED flag, if it has been successfully set.
        """

        if not isinstance(self._REQUIRED, bool):
            _logger.warning("%s trying to get required flag that has not been set yet", self.__class__.__name__)
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

    def set_question_element(self, element: WebElement) -> None:
        """Sets the web element representing the entire question if it has changed.

        :param element: The new web element representing the entire question if it has changed.
        """

        self._QUESTION_ELEMENT = element

    def set_answer_elements(self, *args, **kwargs) -> None:
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

    def _is_valid(self, *elements: WebElement) -> bool:
        """Check if the web element(s) is/are still valid.

        :param elements: The web element(s) to validate.
        :return: True if the web element(s) can be found, False otherwise.
        """

        # Sanity check for elements
        if len(elements) == 0:
            _logger.warning("%s checking if elements are valid without specifying elements", self.__class__.__name__)
            return True

        # Sanity check for browser
        browser = self._BROWSER.get_browser()
        if not browser:
            return False

        try:
            # NOTE: Any method call from WebElement will perform a 'freshness check'
            #       Failure of the 'freshness check' will throw a StaleElementReferenceException
            # https://www.selenium.dev/selenium/docs/api/py/webdriver_remote/selenium.webdriver.remote.webelement.html
            for element in elements:
                _ = element.is_displayed()
            return True
        except StaleElementReferenceException:
            return False

    """
    @Browser.monitor_browser
    def _perform_submission(self, *instructions: Tuple[WebElement, Optional[Union[str, WebElement]], Optional[str]],
                            to_pause: Optional[bool] = False) -> Optional[bool]:
        Simulates realistic submission of answers to Google Form.

        The function makes use of ActionChains actions to emulate a more realistic user-like interaction
        with the Google Forms, while automating the submission of answers to specified elements.

        :param instructions: Tuples of instructions to chain together and perform.
                             Each instruction follows the specified format: (ELEMENT, (ELEMENT OR STR), STR),
                             where ELEMENT is/are element(s) to autoclick and STR is/are answer texts to submit.
        :param to_pause: Flag to indicate if each action should be performed with appropriate buffer time.
        :return: True if the action is performed and None if an exception was caught.
        

        def _click(element: WebElement, to_pause: bool) -> None:
            Helper function to autoclick a web element.

            :param element: The web element to click.
            :param to_pause: Flag to indicate if each action should be performed with appropriate buffer time.
            

            action.move_to_element_with_offset(element, 0, 0).click()
            if to_pause:
                # action.pause(self._BROWSER.get_action_buffer())
                action.pause(5)  # TODO DEBUG

        def _type(text: str, to_pause: bool) -> None:
            Helper function to autofill text into a web element.
            
            Assumes web element has already been selected in the browser.

            :param text: The text to autofill.
            :param to_pause: Flag to indicate if each action should be performed with appropriate buffer time.
            

            action.send_keys(text).pause(self._BROWSER.get_action_buffer())
            if to_pause:
                action.pause(self._BROWSER.get_action_buffer() + int(len(text) >> 3))

        # Sanity check for instructions
        if len(instructions) == 0:
            _logger.warning("%s performing submission with no specified instructions", self.__class__.__name__)
            return True  # Technically no exception caught

        # Obtain ActionChains
        action = self._BROWSER.get_action_chains()
        while not action:
            if not self._BROWSER.retry_browser():
                return
            action = self._BROWSER.get_action_chains()

        print("Instruction received:", instructions)  # TODO DEBUG

        for element, element_or_str, other_str in instructions:
            _click(element, to_pause)
            if element_or_str:
                _click(element_or_str, to_pause) if isinstance(element_or_str, WebElement) else \
                    _type(element_or_str, to_pause)
            if other_str:
                # If other_str is defined, the instruction is to perform the following:
                # Select 'Other' radio/checkbox option, select 'Other' input field, type in 'Other' input field
                _type(other_str, to_pause)
        action.perform()
        return True
    """

    @Browser.monitor_browser
    def get_info(self) -> Optional[bool]:
        """Obtains question metadata from Google Form.

        For BaseQuestion, answer_elements functions are not implemented.

        :return: True if the question metadata has been successfully cached, False otherwise.
                 Returns None only if Browser.monitor_browser returns None.
        """

        # Sanity check for question element
        if not (self._get_question_element() and self._is_valid(self._QUESTION_ELEMENT)):
            # Refresh the question element before retrying
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

    def answer(self, *args, **kwargs) -> Optional[bool]:
        """Provide instruction to answer the question.

        For BaseQuestion, answer_elements functions are not implemented.
        """
        pass


class BaseOptionQuestion(AbstractOptionQuestion, BaseQuestion):
    """
    BaseOptionQuestion class as a generic Google Form question wrapper for questions with options provided.

    This script caches the options provided by the question for easy retrieval and answer-checking.

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

    # region Constructors

    def __init__(self, question_element: WebElement, browser: Browser) -> None:
        """Initialisation of BaseOptionQuestion class.

        :param question_element: The web element which represents the entire question.
        :param browser: The selenium browser instance used to host the Google Form.
        """

        BaseQuestion.__init__(self, question_element, browser)
        self._OPTIONS = None
        self._OTHER_OPTION_ELEMENT = None
        self._OTHER_OPTION_LABEL = utils.generate_random_signatures(1)

    def __repr__(self) -> str:
        """Overriden __repr__ of BaseOptionQuestion class.

        :return: The __repr__ string.
        """

        return BaseQuestion.__repr__(self) + ": options={}, other_option_element={}, other_option_label={}" \
            .format(self._OPTIONS, repr(self._OTHER_OPTION_ELEMENT), self._OTHER_OPTION_LABEL)

    def __str__(self) -> str:
        """Overriden __str__ of BaseOptionQuestion class.

        :return: The __str__ string.
        """

        return "{} object with options: {}".format(self.__class__.__name__, self._OPTIONS)

    def __eq__(self, other: "BaseOptionQuestion") -> bool:
        """Overriden __eq__ of BaseOptionQuestion class.

        Two BaseOptionQuestion classes are equal if their BaseQuestion superclasses are equal
        and their options are equal.

        :param other: The other instance of the BaseOptionQuestion class.
        :return: Whether the two instances are equal.
        """

        return super().__eq__(other) and self._OPTIONS == other._OPTIONS

    # endregion Constructors

    # region Getter methods

    def get_options(self) -> Optional[Tuple[str, ...]]:
        """Gets a list of all possible options.

        :return: The list of all possible options, if it has been successfully set.
        """

        if not isinstance(self._OPTIONS, Tuple):
            _logger.warning("%s trying to get list of options that has not been initialised", self.__class__.__name__)
        return self._OPTIONS

    def get_other_option_element(self) -> Optional[WebElement]:
        """Gets the web element for the other option input field.

        :return: The web element for the other option input field, if it has been successfully set.
        """

        if not self._OTHER_OPTION_ELEMENT:
            _logger.warning("%s trying to get the web element for the 'Other' option field that has not been set",
                            self.__class__.__name__)
        return self._OTHER_OPTION_ELEMENT

    # endregion Getter methods

    # region Setter methods

    def _set_options(self, *options: str, other_option_label: Optional[str] = None) -> None:
        """Sets the list of options provided if it has changed.

        :param options: The options provided.
        :param other_option_label: The label used to denote the 'Other' option.
        """

        # Sanity check
        if len(options) == 0:
            _logger.warning("%s setting options with no options specified", self.__class__.__name__)
            return

        result = []
        for option in options:
            if isinstance(other_option_label, str) and option == other_option_label:
                result.append(self._OTHER_OPTION_LABEL)
            else:
                result.append(option)
        self._OPTIONS = tuple(result)

    def set_other_option_element(self, element: WebElement) -> None:
        """Sets the other option element if it has changed.

        :param element: The web element for the 'Other' option input field.
        """

        self._OTHER_OPTION_ELEMENT = element

    # endregion Setter methods

    def _is_option(self, option: str) -> bool:
        """Check if the option is specified.

        :param option: To option to check if specified.
        :return: Flag to indicate if the option is specified.
        """

        return option in self.get_options()

    def _has_other_option(self) -> bool:
        """Check if there is an 'Other' option specified.

        Checks if self._OPTIONS has the 'Other' options and self._OTHER_OPTION_ELEMENT has been defined.

        :return: Flag to indicate if there is an 'Other' option specified.
        """

        return self._is_option(self._OTHER_OPTION_LABEL) and bool(self.get_other_option_element())


class BaseOptionGridQuestion(BaseOptionQuestion):
    """
    BaseOptionGridQuestion class as a generic Google Form question wrapper for grid-based questions.

    This script caches the options provided by the question according to the grid format
    for easy retrieval and answer-checking.

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
    _DELIMITER = ", response for "
    _REGEX = "^([\\w|\\s]+)(, response for )([\\w|\\s]+)$"
    _CONTAINER = "freebirdFormviewerComponentsQuestionGridScrollContainer"  # To obtain options from

    # region Getter methods

    @classmethod
    def get_container_class(cls) -> str:
        """Helper function to obtain the class name for the grid options container.

        :return: The class name for the grid options container.
        """

        return cls._CONTAINER

    def _get_from_formatted_options(self, get_sub_questions: bool) -> Optional[Tuple[str, ...]]:
        """Helper function to get options or sub-questions from the formatted aria labels.

        :param get_sub_questions: True if sub-questions are to be obtained, False if options are to be obtained.
        :return: The required list of either options or sub-questions.
        """

        formatted_options = super().get_options()
        if not formatted_options:
            # Cascade unwanted result
            return formatted_options
        elif not self.is_grid_option(*formatted_options):
            # Log error and reset
            _logger.error("%s trying to set grid options which are not properly formatted, options=%s",
                          self.__class__.__name__, formatted_options)
            self._OPTIONS = None
            return

        # Obtain either options or sub-questions from the formatted aria label
        options, sub_questions = zip(*[re.split(self._DELIMITER, option) for option in formatted_options])
        seen, lst = set(), sub_questions if get_sub_questions else options
        return tuple(value for value in lst if not (value in seen or seen.add(value)))

    def get_options(self) -> Optional[Tuple[str, ...]]:
        """Gets a list of all possible options.

        Obtains the options from the formatted aria labels.

        :return: The list of all possible options, if it has been successfully set.
        """

        return self._get_from_formatted_options(False)

    def get_sub_questions(self) -> Optional[Tuple[str, ...]]:
        """Get the list of defined sub-questions.

        Obtains the sub-questions from the formatted aria labels.

        :return: The sub-questions defined, if it has been successfully set.
        """

        return self._get_from_formatted_options(True)

    # endregion Getter methods

    def _is_option(self, option: str) -> bool:
        """Check if the option is specified.

        :param option: To option to check if specified.
        :return: Flag to indicate if the option is specified.
        """

        # Sanity check
        sub_questions = self.get_sub_questions()
        if not sub_questions:
            return False
        elif not self.is_grid_option(option):
            _logger.error("%s trying to check non-grid option using grid method", self.__class__.__name__)
            return super()._is_option(option)

        option, sub_question = option.split(self._DELIMITER)
        return super()._is_option(option) and sub_question in sub_questions

    @classmethod
    def is_grid_option(cls, *options: str) -> bool:
        """Check if the option aria label(s) match(es) the grid regex.

        :param options: The option aria label(s) to check.
        :return: Flag to indicate if the option aria label(s) match(es) the grid regex.
        """

        # Sanity check
        if len(options) == 0:
            _logger.warning("%s trying to check grid options but not specifying any", cls.__name__)
            return True

        for option in options:
            if not re.match(cls._REGEX, option):
                return False
        return True


if __name__ == '__main__':
    pass
