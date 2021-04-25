#!/usr/bin/env python3
"""
Google Form processor script for hosting and scraping of Google Forms.

This script provides a processor object to handle the auto-processing of Google Forms.
The FormProcessor object simulates the Google Form website to perform scraping and auto-submission capabilities.

For more details on the functionality of this script, please view the documentation of the FormProcessor class.

This script works in tandem with handler.py to provide a user interface for users to submit Google Forms.
TODO This script uses custom classes as representations of Google Form questions under the ./questions directory.

TODO include dependencies
"""

from browser import Browser
from collections import deque
from datetime import datetime
import logging
import re
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
import time
from typing import Mapping, Optional, Sequence, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


# TODO Overhaul FormProcessor
class FormProcessor(object):
    """FormProcessor Class to handle the processing of Google Forms.

    This class takes the link to a Google Form and can perform the following capabilities:
    1. Automatic web scraping of each section of the Google Form.
    2. Automatic retrieval of each question, along with its provided metadata and options.
    3. Autofill of answers via simulating realistic user input.
    4. Auto-submission of form.

    Each FormProcessor object consists of a Browser object to host the Google Form and two storage variables:
        _questions: A FIFO queue that stores questions scraped in every section of the Google Form.
        _cache: A hash of relevant web elements determined by the answering mode of each question.

    The format of relevant web elements stored in the _cache is listed as follows:
        SHORT-ANSWER TEXTBOXES / PARAGRAPHS: {single_text_element_key: <single_text_web_element>}
        DATES: EITHER {date_picker_key: <date_picker_web_element>}
               OR {date_key: <date_web_element>, month_key: <month_web_element>}
        TIMES: {hour_element_key: <hour_web_element>,
               minute_element_key: <minute_web_element>}
        DURATION: {hour_element_key: <hour_web_element>,
                   minute_element_key: <minute_web_element>,
                   second_element_key: <second_web_element>}
        DROP-DOWNS: {placeholder_key: <placeholder_web_element>}
        NON-GRID-BASED RADIO BUTTONS / CHECKBOXES / LINEAR SCALES: {
            option_1: <option_1_web_element>,
            ...
            option_N: <option_N_web_element>,
            other_option_key: {other_option_select_key: <other_option_radio_checkbox_web_element>,
                               other_option_text_key: <other_option_input_field_web_element>}}
        GRID-BASED RADIO BUTTONS / CHECKBOXES: {
            sub_question_1: {option_1: <question_1_option_1_web_element>,
                             ...
                             option_M: <question_1_option_M_web_element>},
            ...
            sub_question_N: {option_1: <question_N_option_1_web_element>,
                             ...
                             option_M: <question_N_option_M_web_element>}}

    Attributes:
        _BROWSER        The selenium-based Google browser to host the Google Form.
        _QUESTIONS      Storage for questions in the current section of the Google Form yet to be processed.
        _cache          Storage for relevant web elements for the current question of the Google Form being processed.
    """

    # region Define constants

    # Constants dealing with self._cache
    _TEXT_KEY = "text_element_key"
    _DATE_KEY = "date_element_key"
    _MONTH_KEY = "month_element_key"
    _DATE_PICKER_KEY = "date_picker_element_key"
    _HOUR_KEY = "hour_element_key"
    _MINUTE_KEY = "minute_element_key"
    _SECOND_KEY = "second_element_key"
    _PLACEHOLDER_KEY = "placeholder_key"
    _DROPDOWN_MENU_KEY = "dropdown_menu_key"
    _OTHER_KEY = "other_option_key"
    _OTHER_SELECT_KEY = "other_option_select_key"
    _OTHER_INPUT_KEY = "other_option_text_key"
    _BLANK_KEY = "blank_value_key"

    # endregion Define constants

    # region Constructors

    def __init__(self, link: str) -> None:
        """Initalisation of the FormProcessor object.

        :param link: The Google form link used by the FormProcessor.
        """

        # Initialise all variables
        # self._BROWSER = Browser(link, headless=True)
        self._BROWSER = Browser(link)
        self._QUESTIONS = deque()
        self._cache = None

    def __repr__(self) -> str:
        """Overriden __repr__ of FormProcessor class.

        :return: The __repr__ string.
        """

        return super().__repr__() + ": browser={}, questions={}, cache={}" \
            .format(repr(self._BROWSER), repr(self._QUESTIONS), repr(self._cache))

    def __str__(self) -> str:
        """Overriden __str__ of FormProcessor class.

        :return: The __str__ string.
        """

        return "FormProcessor with browser: {}".format(self._BROWSER)

    # endregion Constructors

    # region Handler functions for self._QUESTIONS

    def _add_questions(self, *questions: WebElement) -> None:
        """Stores questions for futher processing.

        The function assumes the order in which the questions are parsed is the order in which they should be processed
        (i.e. the question order obeys the FIFO implementation).

        :param questions: Questions for storing.
        """

        for question in questions:
            if question in self._QUESTIONS:
                # There should not be a duplicate, log for debugging
                _logger.warning("FormProcessor _add_questions appending duplicate element: %s", question)
            self._QUESTIONS.append(question)

    def _clear_questions(self) -> None:
        """Clears all stored questions."""

        if self._QUESTIONS:
            self._QUESTIONS.clear()
        else:
            # Sanity check
            _logger.warning("FormProcessor _clear_questions() called but no questions to be cleared")

    def _get_next_question(self) -> Optional[WebElement]:
        """Get the next question stored in self._QUESTIONS.

        :return: The next question stored, else returns None.
        """

        return self._QUESTIONS.popleft() if len(self._QUESTIONS) > 0 else None

    # endregion Handler functions for self._QUESTIONS

    def reset(self) -> None:
        """Resets all variables."""

        self._BROWSER.close_browser()
        if self._cache:
            self._cache.clear()
        self._clear_questions()

    @Browser.monitor_browser
    def _get_question_info(self, question: WebElement) \
            -> Optional[Tuple[str, bool, str, Optional[Sequence[str]], Optional[Sequence[str]]]]:
        """Obtains the information of the question asked in the current section of the Google form.

        The script obtains each element involved in answering the question and caches them for auto-filling.
        It then returns all useful metadata of the question passed, with the format specified below:
        (
            QUESTION HEADER,  # The title of the question
            REQUIRED QUESTION FLAG,  # Whether the question requires an answer
            QUESTION DESCRIPTION,  # The description of the question provided
            [
                PROVIDED OPTION 1,
                PROVIDED OPTION 2,
                ...
                PROVIDED OPTION N
            ] (OPTIONAL),  # Answers provided for questions with drop-downs, checkboxes or radio buttons
            [
                GRID ROW 1 SUB-QUESTION,
                GRID ROW 2 SUB-QUESTION,
                ...
                GRID ROW N SUB-QUESTION
            ] (OPTIONAL)  # The values given in the rows of grid-type questions
        )

        NOTE: Unless otherwise specified, any exception caught during the execution of this function
              should be handled by the Browser.monitor_browser exception handling.

        :param question: The element containing the Google form question.
        :return: The abovementioned question metadata format.
        """

        # region Define constants

        radio_linear_grid_class_name = "appsMaterialWizToggleRadiogroupEl"  # Radio Buttons / Linear Scale / Radio Grid
        checkbox_grid_class_name = "quantumWizTogglePapercheckboxEl"  # Checkboxes / Checkbox Grid
        dropdown_class_name = "quantumWizMenuPaperselectOption"  # Drop-down Options
        dropdown_menu_class_name = "quantumWizMenuPaperselectPopup"  # Drop-down Menu
        # Short-answer Textboxes / Date / Time / Duration
        saq_date_time_class_name = "quantumWizTextinputPaperinputInput"
        para_class_name = "quantumWizTextinputPapertextareaInput"  # Long-answer Textboxes (Paragraphs)
        other_class_name = "quantumWizTextinputSimpleinputInput"  # 'Other' Input Field

        date_type = "date"
        time_hour_aria_label = "Hour"
        time_minute_aria_label = "Minute"
        duration_hours_aria_label = "Hours"
        duration_minutes_aria_label = "Minutes"
        duration_seconds_aria_label = "Seconds"

        title_class_name = "freebirdFormviewerComponentsQuestionBaseTitle"  # Question Title
        description_class_name = "freebirdFormviewerComponentsQuestionBaseDescription"  # Question Description
        required_question_class_name = "freebirdFormviewerComponentsQuestionBaseRequiredAsterisk"  # Required Asterisk

        # endregion Define constants

        # Obtain the easier-to-obtain question metadata
        question_header = str(question.find_element_by_class_name(title_class_name).text)
        question_description = str(question.find_element_by_class_name(description_class_name).text)
        try:
            is_required = bool(question.find_element_by_class_name(required_question_class_name))
            # Remove the ' *' that suffixes every required question header
            question_header = question_header[:len(question_header) - 2]
        except NoSuchElementException:
            is_required = False

        # Determine the answering mode of the question
        options, sub_questions = None, None

        # region Recording drop-down questions

        # Obtain relevant elements
        elements = question.find_elements_by_class_name(dropdown_class_name)
        if elements:

            # Display drop-down menu
            # Assume first element is placeholder element
            if not self._perform_submission((elements[0], None, None)):
                return

            # With drop-down menu displayed, crawl for options
            menu = question.find_element_by_class_name(dropdown_menu_class_name)
            menu_elements = menu.find_elements_by_class_name(dropdown_class_name)
            options = list(map(lambda element: element.text, menu_elements[1:]))

            # Populate cache
            # NOTE: Options are NOT stored in cache since the drop-down menu is to be closed
            #       Upon re-opening, the identifiers of the menu elements will change
            self._cache = {self._PLACEHOLDER_KEY: elements[0], self._DROPDOWN_MENU_KEY: menu}

            # Close drop-down menu
            if not self._perform_submission((menu_elements[0], None, None)):
                return

        # endregion Recording drop-down questions

        # region Recording checkbox / radio questions (grid / non-grid)

        # Obtain relevant elements
        elements = question.find_elements_by_class_name(checkbox_grid_class_name) \
            + question.find_elements_by_class_name(radio_linear_grid_class_name)
        if elements:

            # To differentiate between grid and non-grid, check the aria-label attribute value
            # For grids, the value should be in the following format:
            # CCC, response for RRR (CCC: column header, RRR: row header)
            labels = list(map(lambda element: element.get_attribute("aria-label"), elements))
            defined_labels = list(filter(lambda label: label, labels))

            # region Grid-based answering mode

            if re.match(r"^([\w|\s]+)(, response for )([\w|\s]+)$", defined_labels[0]):

                # Obtain defined elements
                elements = list(filter(
                    lambda element: element.get_attribute("aria-label") and re.match(
                        r"^([\w|\s]+)(, response for )([\w|\s]+)$",
                        element.get_attribute("aria-label")
                    ), elements))
                labels = [re.split(", response for ", element.get_attribute("aria-label"))
                          for element in elements]

                # Assumes no duplicate options or sub-questions
                # Google Forms does not support duplicate or blanks anyways
                options, sub_questions = [], []
                for option, sub_question in labels:
                    if option not in options:
                        options.append(option)
                    if sub_question not in sub_questions:
                        sub_questions.append(sub_question)

                # Populate cache
                self._cache = {
                    sub_question: {option: None for option in options} for sub_question in sub_questions
                }
                for element in elements:
                    option, sub_question = re.split(", response for ", element.get_attribute("aria-label"))
                    self._cache.get(sub_question)[option] = element

            # endregion Grid-based answering mode

            # region Non-grid-based answering mode

            else:
                self._cache = {self._OTHER_KEY: None}
                for i in range(len(elements)):
                    if labels[i] in self._cache.keys():
                        _logger.warning("FormProcessor _get_question_info multiple options with the same value %s "
                                        "in non-grid radio/text", labels[i])
                    elif not labels[i] or labels[i] == "Other:":

                        # Check if there is an 'Other' option specified
                        if elements[i].get_attribute("data-value") == "__other_option__" or \
                                elements[i].get_attribute("data-answer-value") == "__other_option__":

                            # Sanity check
                            if self._cache.get(self._OTHER_KEY):
                                _logger.warning("FormProcessor _get_question_info multiple 'Other' options detected: "
                                                "%s", self._cache.get(self._OTHER_KEY))
                                continue

                            # Store the 'Other' input field
                            try:
                                input_field = question.find_element_by_class_name(other_class_name)
                                self._cache[self._OTHER_KEY] = {
                                    self._OTHER_SELECT_KEY: elements[i],
                                    self._OTHER_INPUT_KEY: input_field
                                }
                                if labels[i] != "Other:":
                                    labels[i] = "Other:"
                            except NoSuchElementException:
                                # There is an 'Other' option specified, but the input field cannot be found
                                # Raise an additional error before triggering Browser.monitor_browser exception handling
                                _logger.error("FormProcessor _get_question_info 'Other' option defined "
                                              "but no input field found")
                                raise NoSuchElementException

                        # Blank option detected
                        else:
                            _logger.warning("FormProcessor _get_question_info Blank option in non-grid "
                                            "radio/text detected, please debug")
                            self._cache[self._BLANK_KEY + "_" + str(labels.index(labels[i]))] = elements[i]

                    else:
                        self._cache[labels[i]] = elements[i]

                options = labels

            # endregion Non-grid-based answering mode

        # endregion Recording checkbox / radio questions (grid / non-grid)

        # region Recording paragraphs

        elements = question.find_elements_by_class_name(para_class_name)
        if elements:
            assert len(elements) == 1
            self._cache = {self._TEXT_KEY: elements[0]}

        # endregion Recording paragraphs

        # region Recording date

        # Obtain the relevant elements
        date_elements = question.find_elements_by_xpath(".//div[contains(@data-supportsdate, 'true')]")
        if date_elements:

            assert len(date_elements) == 1
            date_element = date_elements[0]
            # has_year = date_element.get_attribute("data-includesyear") == "true"
            # has_time = date_element.get_attribute("data-includestime") == "true"

            # Find the input fields for the date section
            date_pickers = date_element.find_elements_by_xpath(".//input[contains(@type, '{}')]".format(date_type))
            if date_pickers:
                assert len(date_pickers) == 1
                date_picker = date_pickers[0]
                self._cache = {self._DATE_PICKER_KEY: date_picker}
            else:
                dates = date_element.find_elements_by_xpath(".//input[contains(@aria-label, 'Day of the month')]")
                months = date_element.find_elements_by_xpath(".//input[contains(@aria-label, 'Month')]")
                if not (dates or months):
                    _logger.error("FormProcessor _get_question_info cannot find any date elements")
                    return
                assert len(dates) == 1 and len(months) == 1
                self._cache = {self._DATE_KEY: dates[0], self._MONTH_KEY: months[0]}

        # endregion Recording date

        # region Recording time

        time_hour_elements = question.find_elements_by_xpath(
            ".//input[contains(@aria-label, '{}')]".format(time_hour_aria_label))
        time_minute_elements = question.find_elements_by_xpath(
            ".//input[contains(@aria-label, '{}')]".format(time_minute_aria_label))
        if time_hour_elements and time_minute_elements:

            assert len(time_minute_elements) == 1 and len(time_hour_elements) == 1

            # Populate cache
            if self._cache:
                self._cache[self._HOUR_KEY] = time_hour_elements[0]
                self._cache[self._MINUTE_KEY] = time_minute_elements[0]
            else:
                self._cache = {self._HOUR_KEY: time_hour_elements[0], self._MINUTE_KEY: time_minute_elements[0]}

        # endregion Recording time

        # region Recording duration

        duration_hour_elements = question.find_elements_by_xpath(
            ".//input[contains(@aria-label, '{}')]".format(duration_hours_aria_label))
        duration_minute_elements = question.find_elements_by_xpath(
            ".//input[contains(@aria-label, '{}')]".format(duration_minutes_aria_label))
        duration_second_elements = question.find_elements_by_xpath(
            ".//input[contains(@aria-label, '{}')]".format(duration_seconds_aria_label))
        if duration_hour_elements and duration_minute_elements and duration_second_elements:

            assert len(duration_hour_elements) == 1 and len(duration_minute_elements) == 1 and \
                   len(duration_second_elements) == 1

            # Populate cache
            self._cache = {self._HOUR_KEY: duration_hour_elements[0], self._MINUTE_KEY: duration_minute_elements[0],
                           self._SECOND_KEY: duration_second_elements[0]}

        # endregion Recording duration

        # region Recording textbox

        elements = question.find_elements_by_class_name(saq_date_time_class_name)
        if elements and not self._cache:
            assert len(elements) == 1  # TODO Sanity check
            self._cache = {self._TEXT_KEY: elements[0]}

        # endregion Recording textbox

        # Sanity check
        if not self._cache:
            _logger.error("FormProcessor _get_question_info no form elements found, please debug")
            return
        elif question_header == "":
            # The header element was found but no text was obtained
            # Possibility of question header being blank
            _logger.warning("FormProcessor _get_question_info unable to find question header, it might be blank")

        return question_header, is_required, question_description, options, sub_questions

    @Browser.monitor_browser
    def _get_next_section(self, to_click: Optional[bool] = True) -> Optional[Sequence[WebElement]]:
        """Obtains the next section of the form, if any, and returns all questions.

        The script autoclicks the 'Next' or 'Submit' button (whichever is present in the current section)
        and obtains the list of questions in the next section (if any).

        :param to_click: Whether the function should autoclick the 'Next' or 'Submit' button.
        :return: The list of questions in the next section if the 'Next' button was selected.
                 Otherwise, the form was submitted automatically, hence return None.
        """

        # Define constants for web scraping
        submit_button_class_name = "appsMaterialWizButtonPaperbuttonLabel"
        question_class_name = "freebirdFormviewerComponentsQuestionBaseRoot"

        button, to_submit, questions = None, False, []

        # Try obtaining the 'Next' button
        try:
            next_button = self._BROWSER.get_browser().find_element_by_xpath(
                "//span[contains(@class, '{}')]"
                "[contains(., 'Next')]".format(submit_button_class_name))
            button = next_button
        except NoSuchElementException:
            # If there is no 'Next' button, hopefully there is a 'Submit' button
            _logger.info("FormProcessor _get_next_section 'Next' button element could not be found, "
                         "maybe 'Submit' button found instead")

        # Try obtaining the 'Submit' button
        if not button:
            try:
                submit_button = self._BROWSER.get_browser().find_element_by_xpath(
                    "//span[contains(@class, '{}')]"
                    "[contains(., 'Submit')]".format(submit_button_class_name))
                button = submit_button
                to_submit = True
            except NoSuchElementException:
                # Neither 'Next' nor 'Submit' buttons were found, flag as an error
                _logger.error("FormProcessor _get_next_section 'Submit' button element could not be found also")
                raise NoSuchElementException

        # Handle autoclicking
        if to_click:
            button.click()
            _logger.info("FormProcessor _get_next_section() has automatically clicked the '%s' button element!",
                         "Submit" if to_submit else "Next")
            time.sleep(self._BROWSER.get_action_buffer())

        # Handle scraping of next section
        if not to_submit:
            _logger.info("FormProcessor _get_next_section() is scraping the next section of the Google Form")
            questions = self._BROWSER.get_browser().find_elements_by_class_name(question_class_name)

        return questions

    @Browser.monitor_browser
    def _perform_submission(self, *instructions: Tuple[WebElement, Optional[Union[str, WebElement]], Optional[str]]) \
            -> Optional[bool]:
        """Simulates realistic submission of answers to Google Form.

        The function makes use of ActionChains actions to emulate a more realistic user-like interaction
        with the Google Forms, while automating the submission of answers to specified elements.

        The two answering types supported are clicking and typing:
            CLICKING is used to select radio buttons, checkboxes and drop-downs.
            TYPING is used to autofill textboxes, paragraphs and the 'Other' input field.

        :param instructions: Tuples of instructions to chain together and perform.
                             Each instruction follows the specified format: (ELEMENT, (ELEMENT OR STR), STR),
                             where ELEMENT is/are element(s) to autoclick and STR is/are answer texts to submit.
        :return: True if the action is performed, None if an exception was caught.
        """

        def _click(element: WebElement) -> None:
            """Helper function to autoclick a web element.

            :param element: The web element to click.
            """

            action.move_to_element_with_offset(element, 0, 0).click()
            # action.pause(self._BROWSER.get_action_buffer())

        def _type(text: str) -> None:
            """Helper function to autofill text into a web element.

            Assumes web element has already been selected in the browser.

            :param text: The text to autofill.
            """

            action.send_keys(text).pause(self._BROWSER.get_action_buffer())
            # action.pause(self._BROWSER.get_action_buffer() + len(text) >> 2) takes too long

        action = self._BROWSER.get_action_chains()
        for element, element_or_str, other_str in instructions:
            _click(element)
            if element_or_str:
                _click(element_or_str) if isinstance(element_or_str, WebElement) else _type(element_or_str)
            if other_str:
                # If other_str is defined, the instruction is to perform the following:
                # Select 'Other' radio/checkbox option, select 'Other' input field, type in 'Other' input field
                _type(other_str)
        action.perform()
        return True

    def get_question(self, start: Optional[bool] = False) \
            -> Optional[Tuple[str, bool, Optional[str], Optional[Sequence[str]], Optional[Sequence[str]]]]:
        """Obtains the next question in the Google Form.

        This function retrieves the next unanswered question in the Google Form, with all its metadata.
        See self._get_question_info() for the metadata format.

        :param start: Flag to indicate if the Google Form has just begun processing.
        :return: The information of the next unanswered question.
        """

        def _try_next_section() -> Optional[WebElement]:
            """Helper function to obtain the next question of the next section of the Google Form.

            :return: The next question obtained.
            """

            questions = self._get_next_section(not start)
            while not isinstance(questions, Sequence):
                # If get_next_section returns None, an error must have occurred along the way
                # that has been caught by the _selenium_try_except_decorator.
                # With a new browser, try again.
                if self._counter >= self._max_retries:
                    return
                questions = self._get_next_section(not start)
            self._add_questions(*questions)
            return self._get_next_question()

        # Get the next question
        question = self._get_next_question()
        if start or not question:
            question = _try_next_section()

        return self._get_question_info(question) if question else None

    def answer_question(self, *,
                        answer: Optional[Union[str, Sequence[str], Mapping[str, Union[str, Sequence[str]]]]] = None,
                        skip: Optional[bool] = False) -> Optional[bool]:
        """Auto-submits the chosen answer for the current question in the Google Form.

        Based on the configurations of self._cache, the function takes the answers provided for each question
        (and/or sub-question, if any) and auto-submits them to the Google Form.

        The answers parsed into the function are expected to be of the following format:
        SHORT-ANSWER TEXTBOXES / PARAGRAPHS / DATES (WITHOUT TIME) / DROP-DOWNS / NON-GRID-BASED RADIO BUTTONS /
            LINEAR SCALES: answer_question(single_answer, skip)
        NON-GRID-BASED CHECKBOXES: answer_question([answer_1, ..., answer_N], skip)
        DATE (WITH TIME): answer_question({"date": answer_date, "hour": answer_hour, "minute": answer_minute}, skip)
        TIME: answer_question({"hour": answer_hour, "minute": answer_minute}, skip)
        DURATION: answer_question({"hour": answer_hour, "minute": answer_minute, "second": answer_second}, skip)
        GRID-BASED RADIO BUTTONS: answer_question({sub_question_1: answer_1, ... sub_question_N: answer_N}, skip)
        GRID-BASED CHECKBOXES: answer_question({sub_question_1: [answer_1, ..., answer_M], ...}, skip)

        :param answer: The selected answer to submit, in the abovementioned format.
        :param skip: Flag to indicate if the question was skipped.
                     NOTE: The flag is not indicative of whether the question is required on the Google Form.
        :return: True if the submission was performed successfully, False if a sanity check failed,
                 None if an excecption was caught.
        """

        def _submit_time(hour_element: WebElement, minute_element: WebElement, hour: str, minute: str) \
                -> Optional[bool]:
            """Helper function to submit time-based questions.

            :param hour_element: The element to submit the hour of the time answer to.
            :param minute_element: The element to submit the minute of the time answer to.
            :param hour: The hour of the time answer, which should satisfy 0 <= hour <= 23.
            :param minute: The minute of the time answer, which should satisfy 0 <= minute <= 59.
            :return: True if the submission was performed successfully, False if a sanity check failed,
                     None if an excecption was caught.
            """

            # Sanity check
            if not (hour_element and minute_element and hour and minute):
                _logger.error("FormProcessor _submit_time trying to submit time with "
                              "hour_element=%s, minute_element=%s, hour=%s, minute=%s",
                              hour_element, minute_element, hour, minute)
                return False

            # Ensure time is valid
            try:
                hour_int, minute_int = int(hour), int(minute)
                if not (0 <= hour_int <= 23 and 0 <= minute_int <= 59):
                    raise ValueError
            except ValueError:
                _logger.error("FormProcessor _submit_time trying to answer a time with hour=%s, minute=%s",
                              hour, minute)
                return False

            # Perform submission
            return self._perform_submission((hour_element, hour, None), (minute_element, minute, None))

        # Sanity check for self._cache
        if not self._cache:
            _logger.error("FormProcessor answer_question No submission elements cached")
            return False

        # Handle auto-submission of answer
        if not skip:

            # Sanity check
            if not answer:
                _logger.error("FormProcessor answer_question trying to submit answer with no answer provided")
                return False

            # region Submitting date

            if self._DATE_PICKER_KEY in self._cache.keys() or \
                    (self._DATE_KEY in self._cache.keys() and self._MONTH_KEY in self._cache.keys()):

                # Date with time specified
                if isinstance(answer, Mapping):
                    # Sanity check
                    if not ("date" in answer.keys() and "hour" in answer.keys() and "minute" in answer.keys()):
                        _logger.error("FormProcessor answer_question trying to answer a date without date/hour/minute, "
                                      "answer=%s", answer)
                        return False
                    elif not (self._HOUR_KEY in self._cache.keys() and self._MINUTE_KEY in self._cache.keys()):
                        _logger.error("FormProcessor answer_question trying to answer a time without "
                                      "hour/minute elements, hour_element=%s, minute_element=%s",
                                      self._cache.get(self._HOUR_KEY), self._cache.get(self._MINUTE_KEY))
                        return False
                    date = answer.get("date")
                    _submit_time(self._cache.get(self._HOUR_KEY), self._cache.get(self._MINUTE_KEY),
                                 answer.get("hour"), answer.get("minute"))

                # Date without time specified
                elif isinstance(answer, str):
                    if not answer:
                        _logger.error("FormProcessor answer_question trying to answer a date without date, "
                                      "answer=%s", answer)
                        return False
                    date = answer

                else:
                    _logger.error("FormProcessor answer_question trying to answer a date with answer=%s", answer)
                    return False

                if self._DATE_PICKER_KEY in self._cache.keys():

                    # Ensure date is of correct format
                    try:
                        date_time = datetime.strptime(date, "%Y-%m-%d")
                        if date_time > datetime.strptime("2071-01-01", "%Y-%m-%d"):
                            raise ValueError
                        date = date_time.strftime("%d%m%Y")
                    except ValueError:
                        _logger.error("FormProcessor answer_question trying to answer a date with date=%s", date)
                        return False

                    if not self._perform_submission((self._cache.get(self._DATE_PICKER_KEY), date, None)):
                        return

                else:

                    # Ensure date is of correct format
                    try:
                        date_time = datetime.strptime(date, "%m-%d")
                        if not self._perform_submission((self._cache.get(self._DATE_KEY), str(date_time.day), None),
                                                        (self._cache.get(self._MONTH_KEY), str(date_time.month), None)):
                            return
                    except ValueError:
                        _logger.error("FormProcessor answer_question trying to answer a date with date=%s", date)
                        return False

            # endregion Submitting date

            # region Submitting time / duration

            elif self._HOUR_KEY in self._cache.keys() and self._MINUTE_KEY in self._cache.keys():

                # Sanity check
                if not isinstance(answer, Mapping):
                    _logger.error("FormProcessor answer_question trying to answer a time/duration with answer=%s",
                                  answer)
                    return False
                elif not ("hour" in answer.keys() and "minute" in answer.keys()):
                    _logger.error("FormProcessor answer_question trying to answer a time/duration without hour "
                                  "and/or minute, answer=%s", answer)
                    return False

                hour, minute = answer.get("hour"), answer.get("minute")
                if not (isinstance(hour, str) and isinstance(minute, str)):
                    _logger.error("FormProcessor answer_question trying to answer a time/duration with hour=%s, "
                                  "minute=%s", hour, minute)
                    return False

                # region Submitting duration

                if self._SECOND_KEY in self._cache.keys():

                    # Sanity check
                    if "second" not in answer.keys():
                        _logger.error("FormProcessor answer_question trying to answer a duration without second, "
                                      "answer=%s", answer)
                        return False

                    second = answer.get("second")
                    if not isinstance(second, str):
                        _logger.error("FormProcessor answer_question trying to answer a duration with second=%s",
                                      second)
                        return False

                    # Ensure duration is valid
                    try:
                        hour_int, minute_int, second_int = int(hour), int(minute), int(second)
                        if not (0 <= hour_int <= 72 and 0 <= minute_int <= 59 and 0 <= second_int <= 59):
                            raise ValueError
                    except ValueError:
                        _logger.error("FormProcessor answer_question trying to answer a time with hour=%s, minute=%s, "
                                      "second=%s", hour, minute, second)
                        return False

                    if not self._perform_submission((self._cache.get(self._HOUR_KEY), hour, None),
                                                    (self._cache.get(self._MINUTE_KEY), minute, None),
                                                    (self._cache.get(self._SECOND_KEY), second, None)):
                        return

                # endregion Submitting duration

                # Submitting time
                else:
                    _submit_time(self._cache.get(self._HOUR_KEY), self._cache.get(self._MINUTE_KEY), hour, minute)

            # endregion Submitting time / duration

            # region Submitting drop-down

            elif self._PLACEHOLDER_KEY in self._cache.keys() and self._DROPDOWN_MENU_KEY in self._cache.keys():

                # Constants from _get_question_info()
                dropdown_class_name = "quantumWizMenuPaperselectOption"  # Drop-down Options

                # Sanity check
                if not isinstance(answer, str):
                    _logger.error("FormProcessor answer_question trying to answer a dropdown with answer=%s", answer)
                    return False

                # Open drop-down menu and crawl for answer element
                if not self._perform_submission((self._cache.get(self._PLACEHOLDER_KEY), None, None)):
                    return
                menu_elements = self._cache.get(self._DROPDOWN_MENU_KEY).find_elements_by_class_name(
                    dropdown_class_name)[1:]

                # Find element to submit
                has_submitted = False
                for element in menu_elements:
                    if element.text == answer:
                        has_submitted = self._perform_submission((element, None, None))
                        break

                # Error catcher
                if not has_submitted:
                    if isinstance(has_submitted, bool):
                        _logger.error("FormProcessor answer_question unable to find %s option in drop-down menu",
                                      answer)
                    return has_submitted

            # endregion Submitting drop-down

            # region Submitting non-grid radio button / checkbox / linear scale

            elif self._OTHER_KEY in self._cache.keys():

                def _submit(selection: str) -> Optional[bool]:
                    """Helper function to perform submission.

                    :param selection: The user selection to submit.
                    :return: True if the submission was performed successfully, False if a sanity check failed,
                             None if an exception was caught.
                    """

                    if selection in self._cache.keys() and selection != self._OTHER_KEY:
                        return self._perform_submission((self._cache.get(selection), None, None))

                    # Handle 'Other' input
                    else:
                        if not self._cache.get(self._OTHER_KEY):
                            _logger.error("FormProcessor answer_question no 'Other' elements initialised")
                            return False
                        return self._perform_submission((
                            self._cache.get(self._OTHER_KEY).get(self._OTHER_SELECT_KEY),
                            self._cache.get(self._OTHER_KEY).get(self._OTHER_INPUT_KEY),
                            selection
                        ))

                # Sanity check
                if isinstance(answer, Mapping):
                    _logger.error("FormProcessor answer_question trying to answer non-grid based question with "
                                  "answer=%s", answer)
                    return False

                elif isinstance(answer, str):
                    if not _submit(answer):
                        return
                else:
                    for selection in answer:
                        if not bool(_submit(selection)):
                            return

            # endregion Submitting non-grid radio button / checkbox / linear scale

            # region Submitting textbox / paragraph

            elif self._TEXT_KEY in self._cache.keys():

                # Sanity check
                if not isinstance(answer, str):
                    _logger.error("FormProcessor answer_question trying to answer a textbox/paragraph with answer=%s",
                                  answer)
                    return False

                if not self._perform_submission((self._cache.get(self._TEXT_KEY), answer, None)):
                    return

            # endregion Submitting textbox / paragraph

            # region Submitting grid-based radio button / checkbox

            else:

                # Sanity check
                if not isinstance(answer, Mapping):
                    _logger.error("FormProcessor answer_question trying to answer a grid-based question with answer=%s",
                                  answer)
                    return False
                elif not set(answer.keys()).issubset(set(self._cache.keys())):
                    _logger.error("FormProcessor answer_question trying to answer a grid-based question with "
                                  "answer=%s, questions=%s", answer, self._cache.keys())
                    return False

                for sub_question in answer.keys():
                    selections = answer.get(sub_question)
                    if isinstance(selections, str):
                        if not bool(self._perform_submission((
                                self._cache.get(sub_question).get(selections), None, None))):
                            return
                    elif isinstance(selections, Sequence):
                        if not bool(self._perform_submission(*((
                                self._cache.get(sub_question).get(selection), None, None)
                                for selection in selections))):
                            return
                    else:
                        # This should never trigger
                        _logger.error("FormProcessor answer_question submitting grid-based answer with unsupported "
                                      "answer type\nanswer=%s, instance=%s", selections, type(selections))
                        return False

            # endregion Submitting grid-based radio button / checkbox

            _logger.info("FormProcessor answer_question question has been successfully answered!\n"
                         "answer: %s", answer)

        else:
            _logger.info("FormProcessor answer_question question has been successfully skipped!")

        # Question has been processed successfully
        self._cache.clear()
        return True


if __name__ == '__main__':

    # TODO DEBUG
    def get_answer(answer):
        result = None
        if "date" in answer:
            answer = answer.replace("date ", "")
            date = answer.split(" ")[0]
            answer = answer.replace(date + " ", "")
            result = {"date": date}
        if "time" in answer:
            hour, minute = answer.replace("time ", "").split(" ")
            if result:
                result["hour"] = hour
                result["minute"] = minute
            else:
                result = {"hour": hour, "minute": minute}
        elif "duration" in answer:
            hour, minute, second = answer.replace("duration ", "").split(" ")
            result = {"hour": hour, "minute": minute, "second": second}
        elif ";" in answer:
            result = answer.split(";")
        else:
            result = answer
        return result

    form_url = "https://forms.gle/DwmmfPHGhkNsAVBc9"
    processor = FormProcessor(form_url)

    # Get the first question
    # If None, the FormProcessor already tried <max_retries> times
    question = processor.get_question(True)

    # Process each question
    while question:
        question_header, is_required, question_description, options, sub_questions = question
        print("{} || {} || {} || {} || {}".format(*question))
        if is_required:
            answer = None
            if sub_questions:
                answer = {}
                for question in sub_questions:
                    answer[question] = get_answer(input("Input answer for {}: ".format(question)))
            else:
                answer = get_answer(input("Input answer: "))
            print("Answer: ", answer)

            # Try to answer question
            if not processor.answer_question(answer=answer):
                print("Answer did not submit successfully, please debug")
        else:
            if not processor.answer_question(skip=True):
                print("Answer did not skip successfully, please debug")
        # Get next question
        question = processor.get_question()
    processor.reset()

    # pass
