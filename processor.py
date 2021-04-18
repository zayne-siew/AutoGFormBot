from collections import deque
from datetime import datetime
import logging
# import os
import re
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
import time
from typing import Mapping, Optional, Sequence, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)

# Define chromedriver path
# _CHROMEDRIVER_PATH = os.environ["CHROMEDRIVER_PATH"]
_CHROMEDRIVER_PATH = "D:/software/chromedriver.exe"  # TODO push to server?


class FormProcessor:
    # TODO include dependencies
    """FormProcessor Class to handle the processing of Google Forms.

    This class takes the link to a Google Form and can perform the following capabilities:
    1. Automatic web scraping of each section of the Google Form.
    2. Automatic retrieval of each question, along with its provided metadata and options.
    3. Autofill of answers via simulating realistic user input.
    4. Auto-submission of form.

    Each FormProcessor object consists of a WebDriver to host the Google Form and two storage variables:
        _questions: A FIFO queue that stores questions scraped in every section of the Google Form.
        _cache: A hash of relevant web elements determined by the answering mode of each question.

    The format of relevant web elements stored in the _cache is listed as follows:
        SHORT-ANSWER TEXTBOXES / PARAGRAPHS: {single_text_element_key: <single_text_web_element>}
        DATES (WITHOUT TIME): {date_element_key: <date_web_element>}
        TIME: {hour_element_key: <hour_web_element>,
               minute_element_key: <minute_web_element>}
        DATES (WITH TIME): {date_element_key: <date_web_element>,
                            hour_element_key: <hour_web_element>,
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
        _link           The link to the Google Form to be processed.
        _browser        The selenium-based Google browser to host the Google Form.
        _questions      Storage for questions in the current section of the Google Form yet to be processed.
        _cache          Storage for relevant web elements for the current question of the Google Form being processed.
    """

    # region Define constants

    # Constants dealing with self._cache
    _TEXT_KEY = "text_element_key"
    _DATE_KEY = "date_element_key"
    _HOUR_KEY = "hour_element_key"
    _MINUTE_KEY = "minute_element_key"
    _SECOND_KEY = "second_element_key"
    _PLACEHOLDER_KEY = "placeholder_key"
    _DROPDOWN_MENU_KEY = "dropdown_menu_key"
    _OTHER_KEY = "other_option_key"
    _OTHER_SELECT_KEY = "other_option_select_key"
    _OTHER_INPUT_KEY = "other_option_text_key"
    _BLANK_KEY = "blank_value_key"

    # Constants dealing with Selenium browser
    _NUM_MAX_RETRIES = 5
    _TIMEOUT_SECONDS = 8
    _REFRESH_WAIT_SECONDS = 5
    _ACTION_BUFFER_SECONDS = 1

    # endregion Define constants

    # region Constructors

    def __init__(self, link: str) -> None:
        """Initalisation of the FormProcessor object.

        :param link: The Google form link used by the FormProcessor.
        """

        self._link = link
        self._questions = deque()
        self._cache = None
        self._set_browser()

    def __repr__(self) -> str:
        """Unambiguous representation of the FormProcesor object.

        :return: The repr representation.
        """

        return "FormProcessor link={}, browser={}, questions={}, cache={}" \
            .format(repr(self._link), repr(self._browser), repr(self._questions), repr(self._cache))

    def __str__(self) -> str:
        """String representation of the FormProcessor object.

        :return: The string representation.
        """

        return "FormProcessor object to process the Google Form: {}".format(self._link)

    # endregion Constructors

    # region Handler functions for self._questions

    def _add_questions(self, *questions: WebElement) -> None:
        """Stores questions for futher processing.

        The function assumes the order in which the questions are parsed is the order in which they should be processed
        (i.e. the question order obeys the FIFO implementation).

        :param questions: Questions for storing.
        """

        for question in questions:
            if question in self._questions:
                # There should not be a duplicate, log for debugging
                _logger.warning("%s\nAppending duplicate element into self._questions: %s", self, question)
            self._questions.append(question)

    def _get_next_question(self) -> Optional[WebElement]:
        """Get the next question stored in self._questions.

        If self._questions is not defined, it is first initialised in self._set_questions.

        :return: The next question stored, else returns None.
        """

        return self._questions.popleft() if len(self._questions) > 0 else None

    # endregion Handler functions for self._questions

    # region Handler functions for self._browser

    def _set_browser(self, *, headless: Optional[bool] = False, num_max_retries: Optional[int] = _NUM_MAX_RETRIES,
                     timeout_seconds: Optional[int] = _TIMEOUT_SECONDS, counter: Optional[int] = 1) -> None:
        """Initialises the selenium browser.

        If the browser fails, the function tries to initialise a new browser for a certain amount of tries.
        Each initialisation takes incrementally longer to complete to try avoiding bot detection.
        Otherwise, the function fails and stops the browser.

        :param headless: Flag to indicate if the browser should run headless.
        :param num_max_retries: The maximum number of retries before the function fails.
        :param timeout_seconds: The timeout (in seconds) before retrying.
        :param counter: The number of browsers instantiated.
        """

        # Initialise ChromeOptions
        options = webdriver.ChromeOptions()
        options.add_argument("-incognito")
        options.add_argument("start-maximized")
        options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
        if headless:
            options.add_argument("--headless")
            options.add_argument("disable-gpu")

        try:
            # Initialise browser with link
            self._browser = webdriver.Chrome(executable_path=_CHROMEDRIVER_PATH, options=options)
            # self._browser = webdriver.Chrome(options=options)  # webdriver will search for chromedriver by itself
            self._browser.implicitly_wait(self._ACTION_BUFFER_SECONDS)
            self._browser.get(self._link)
        except NoSuchElementException:
            # If such an error occurs, the page is most likely unavailable
            # either due to page removal or due to bot detection
            self._close_browser()
            if counter == num_max_retries:
                _logger.error("%s\nCompletely unable to access form after %d retries", self, num_max_retries)
            else:
                _logger.warning("%s\nUnable to access form, retry counter: %d", self, counter)
                time.sleep(timeout_seconds)
                self._set_browser(headless=headless, num_max_retries=num_max_retries,
                                  timeout_seconds=int(timeout_seconds * 1.5), counter=counter + 1)

    def _close_browser(self) -> None:
        """Closes any open browser for clean exit."""
        if self._browser:
            self._browser.close()
            self._browser = None
        else:
            # Sanity check
            _logger.warning("%s\n_close_browser() called but no browser to be closed", self)

    # endregion Handler functions for self._browser

    def _get_question_info(self, question: WebElement) \
            -> Tuple[str, bool, Optional[str], Optional[Sequence[str]], Optional[Sequence[str]]]:
        """Obtains the information of the question asked in the current section of the Google form.

        The script obtains each element involved in answering the question and caches them for auto-filling.
        It then returns all useful metadata of the question passed, with the format specified below:
        (
            QUESTION HEADER,  # The title of the question
            REQUIRED QUESTION FLAG,  # Whether the question requires an answer
            QUESTION DESCRIPTION (OPTIONAL),  # The description of the question provided, if any
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
              should be handled by the _get_browser() function exception handling.

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
        answer_class_names = [radio_linear_grid_class_name, checkbox_grid_class_name, dropdown_class_name,
                              para_class_name, saq_date_time_class_name]

        # endregion Define constants

        # Obtain the easier-to-obtain question metadata
        question_header = str(question.find_element_by_class_name(title_class_name).text)
        question_description = str(question.find_element_by_class_name(description_class_name).text)
        try:
            is_required = bool(question.find_element_by_class_name(required_question_class_name))
            # Remove the ' *' that suffixes every required question header
            question_header = question_header[:len(question_header) - 2]
        except NoSuchElementException:
            # Non-required questions will inevitably throw this exception
            # Hence, we need to handle it separately from the _get_browser() exception handler
            is_required = False

        # Determine the answering mode of the question
        element_found, options, sub_questions = False, None, None
        for class_name in answer_class_names:
            elements = question.find_elements_by_class_name(class_name)
            if elements:

                # region Recording drop-down questions

                if class_name == dropdown_class_name:

                    # Display drop-down menu
                    # Assume first element is placeholder element
                    self._perform_submission((elements[0], None, None))

                    # With drop-down menu displayed, crawl for options
                    menu = question.find_element_by_class_name(dropdown_menu_class_name)
                    menu_elements = menu.find_elements_by_class_name(dropdown_class_name)
                    options = list(map(lambda element: element.text, menu_elements[1:]))

                    # Populate cache
                    # NOTE: Options are NOT stored in cache since the drop-down menu is to be closed
                    #       Upon re-opening, the identifiers of the menu elements will change
                    self._cache = {self._PLACEHOLDER_KEY: elements[0], self._DROPDOWN_MENU_KEY: menu}

                    # Close drop-down menu
                    self._perform_submission((menu_elements[0], None, None))

                # endregion Recording drop-down questions

                # region Recording checkbox / radio questions (grid / non-grid)

                elif class_name == checkbox_grid_class_name or class_name == radio_linear_grid_class_name:
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
                                _logger.warning("%s\nMultiple options with the same value %s in non-grid radio/text",
                                                self, labels[i])
                            elif not labels[i] or labels[i] == "Other:":

                                # Check if there is an 'Other' option specified
                                if elements[i].get_attribute("data-value") == "__other_option__" or \
                                        elements[i].get_attribute("data-answer-value") == "__other_option__":

                                    # Sanity check
                                    if self._cache.get(self._OTHER_KEY):
                                        _logger.warning("%s\nMultiple 'Other' options detected: %s",
                                                        self, self._cache.get(self._OTHER_KEY))
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
                                        # Raise an additional error before triggering _get_browser() exception handling
                                        _logger.error("%s\n'Other' option defined but no input field found", self)
                                        raise NoSuchElementException

                                # Blank option detected
                                else:
                                    _logger.warning("%s\nBlank option in non-grid radio/text detected, please debug",
                                                    self)
                                    self._cache[self._BLANK_KEY + "_" + str(labels.index(labels[i]))] = elements[i]

                            else:
                                self._cache[labels[i]] = elements[i]

                        options = labels

                    # endregion Non-grid-based answering mode

                # endregion Recording checkbox / radio questions (grid / non-grid)

                # region Recording time

                elif len(elements) == 2:
                    hour, minute = None, None
                    for element in elements:

                        # Assign element based on its label
                        label = element.get_attribute("aria-label")
                        if label == time_hour_aria_label:
                            if hour:
                                _logger.error("%s\nMultiple time hour element detected", self)
                                break
                            hour = element
                        elif label == time_minute_aria_label:
                            if minute:
                                _logger.error("%s\nMultiple time minute element detected", self)
                                break
                            minute = element
                        else:
                            _logger.error("%s\nUnknown time element detected with aria-label=%s", self, label)
                            break

                    # Sanity check
                    if not (hour and minute):
                        _logger.error("%s\nTime elements not initialised.\nhour=%s, minute=%s", self, hour, minute)
                        raise NoSuchElementException

                    # Populate cache
                    self._cache = {
                        self._HOUR_KEY: hour,
                        self._MINUTE_KEY: minute
                    }

                # endregion Recording time

                # TODO check if date consists of year

                # region Recording duration / date (with time)

                elif len(elements) == 3:
                    hour, minute, second, date = None, None, None, None
                    for element in elements:

                        # Assign element based on its label / type
                        label = element.get_attribute("aria-label")
                        if label == duration_hours_aria_label or label == time_hour_aria_label:
                            if hour:
                                _logger.error("%s\nMultiple time/duration hour element detected", self)
                                break
                            hour = element
                        elif label == duration_minutes_aria_label or label == time_minute_aria_label:
                            if minute:
                                _logger.error("%s\nMultiple time/duration minute element detected", self)
                                break
                            minute = element
                        elif label == duration_seconds_aria_label:
                            if second:
                                _logger.error("%s\nMultiple duration second element detected", self)
                                break
                            second = element
                        elif element.get_attribute("type") == date_type:
                            if date:
                                _logger.error("%s\nMultiple date element detected", self)
                                break
                            date = element
                        else:
                            _logger.error("%s\nUnknown duration element detected with aria-label=%s", self, label)
                            break

                    # Sanity check
                    if not (hour and minute and (second or date)):
                        _logger.error("%s\nElements not initialised.\nhour=%s, minute=%s, second=%s, date=%s",
                                      self, hour, minute, second, date)
                        raise NoSuchElementException
                    elif second and date:
                        _logger.error("%s\nSecond and date element both defined, please debug\n"
                                      "second=%s, date=%s", self, second, date)
                        raise NoSuchElementException

                    # Populate cache
                    self._cache = {
                        self._HOUR_KEY: hour,
                        self._MINUTE_KEY: minute
                    }
                    if second:
                        self._cache[self._SECOND_KEY] = second
                    else:
                        self._cache[self._DATE_KEY] = date

                # endregion Recording duration / date (with time)

                # region Recording textbox / paragraph / date (without time)

                elif len(elements) == 1:
                    # Assume element is correct, will throw error in answer_question otherwise
                    if elements[0].get_attribute("type") == date_type:
                        self._cache = {self._DATE_KEY: elements[0]}
                    else:
                        self._cache = {self._TEXT_KEY: elements[0]}

                # endregion Recording textbox / paragraph / date (without time)

                # Sanity check
                else:
                    _logger.error("%s\nUnknown element(s) found: %s", self, elements)
                    raise NoSuchElementException

                element_found = True
                break

        # Final sanity check
        if question_header == "":
            # The header element was found but no text was obtained
            # Possibility of question header being blank
            _logger.warning("%s\nUnable to find question header, it might be blank", self)
        if not element_found:
            _logger.error("%s\nUnable to find any Google Form elements", self)

        return question_header, is_required, question_description, options, sub_questions

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

        button, to_submit, questions = None, False, None

        # Try obtaining the 'Next' button
        try:
            next_button = self._browser.find_element_by_xpath(
                "//span[contains(@class, '{}')]"
                "[contains(., 'Next')]".format(submit_button_class_name))
            button = next_button
        except NoSuchElementException:
            # If there is no 'Next' button, hopefully there is a 'Submit' button
            _logger.info("%s\n'Next' button element could not be found, maybe 'Submit' button found instead", self)

        # Try obtaining the 'Submit' button
        if not button:
            try:
                submit_button = self._browser.find_element_by_xpath(
                    "//span[contains(@class, '{}')]"
                    "[contains(., 'Submit')]".format(submit_button_class_name))
                button = submit_button
                to_submit = True
            except NoSuchElementException:
                # Neither 'Next' nor 'Submit' buttons were found, flag as an error
                _logger.error("%s\n'Submit' button element could not be found also, please debug", self)
                return

        # Handle autoclicking
        if to_click:
            button.click()
            _logger.info("%s\n_get_next_section() has automatically clicked the '%s' button element!",
                         self, "Submit" if to_submit else "Next")
            time.sleep(self._REFRESH_WAIT_SECONDS)

        # Handle scraping of next section
        if not to_submit:
            _logger.info("%s\n_get_next_section() is scraping the next section of the Google Form", self)
            questions = self._browser.find_elements_by_class_name(question_class_name)

        return questions

    def _perform_submission(self, *instructions: Tuple[WebElement, Optional[Union[str, WebElement]], Optional[str]]) \
            -> None:
        """Simulates realistic submission of answers to Google Form.

        The function makes use of ActionChains actions to emulate a more realistic user-like interaction
        with the Google Forms, while automating the submission of answers to specified elements.

        The two answering types supported are clicking and typing:
            CLICKING is used to select radio buttons, checkboxes and drop-downs.
            TYPING is used to autofill textboxes, paragraphs and the 'Other' input field.

        :param instructions: Tuples of instructions to chain together and perform.
                             Each instruction follows the specified format: (ELEMENT, (ELEMENT OR STR), STR),
                             where ELEMENT is/are element(s) to autoclick and STR is/are answer texts to submit.
        """

        def _click(element: WebElement) -> None:
            """Helper function to autoclick a web element.

            :param element: The web element to click.
            """

            action.move_to_element_with_offset(element, 0, 0).click()
            # action.pause(self._ACTION_BUFFER_SECONDS)

        def _type(text: str) -> None:
            """Helper function to autofill text into a web element.

            Assumes web element has already been selected in the browser.

            :param text: The text to autofill.
            """

            action.send_keys(text).pause(self._ACTION_BUFFER_SECONDS)
            # action.pause(self._ACTION_BUFFER_SECONDS + len(text) >> 2) takes too long

        action = ActionChains(self._browser)
        for element, element_or_str, other_str in instructions:
            _click(element)
            if element_or_str:
                _click(element_or_str) if isinstance(element_or_str, WebElement) else _type(element_or_str)
            if other_str:
                # If other_str is defined, the instruction is to perform the following:
                # Select 'Other' radio/checkbox option, select 'Other' input field, type in 'Other' input field
                _type(other_str)
        action.perform()

    def get_next_question(self, start: Optional[bool] = False) \
            -> Optional[Tuple[str, bool, Optional[str], Optional[Sequence[str]], Optional[Sequence[str]]]]:
        """Obtains the next question in the Google Form.

        This function retrieves the next unanswered question in the Google Form, with all its metadata.
        See self._get_question_info() for the metadata format.

        :param start: Flag to indicate if the Google Form has just begun processing.
        :return: The information of the next unanswered question.
        """

        question = self._get_next_question()
        if start or not question:
            # Try getting more questions from the next section of the Google Form
            questions = self._get_next_section(not start)
            if questions:
                self._add_questions(*questions)
                question = self._get_next_question()

        return self._get_question_info(question) if question else None

    def answer_question(self, *,
                        answer: Optional[Union[str, Sequence[str], Mapping[str, Union[str, Sequence[str]]]]] = None,
                        skip: Optional[bool] = False) -> None:
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
        """

        def _submit_time(hour_element: WebElement, minute_element: WebElement, hour: str, minute: str) -> None:
            """Helper function to submit time-based questions.

            :param hour_element: The element to submit the hour of the time answer to.
            :param minute_element: The element to submit the minute of the time answer to.
            :param hour: The hour of the time answer, which should satisfy 0 <= hour <= 23.
            :param minute: The minute of the time answer, which should satisfy 0 <= minute <= 59.
            """

            # Sanity check
            if not (hour_element and minute_element and hour and minute):
                _logger.error("_submit_time trying to submit time with hour_element=%s, minute_element=%s, hour=%s, "
                              "minute=%s", hour_element, minute_element, hour, minute)
                return

            # Ensure time is valid
            try:
                hour_int, minute_int = int(hour), int(minute)
                if not (0 <= hour_int <= 23 and 0 <= minute_int <= 59):
                    raise ValueError
            except ValueError:
                _logger.error("_submit_time trying to answer a time with hour=%s, minute=%s", hour, minute)
                return

            # Perform submission
            self._perform_submission((hour_element, hour, None), (minute_element, minute, None))

        # Sanity check for self._cache
        if not self._cache:
            _logger.error("%s\nNo submission elements cached", self)
            return

        # Handle auto-submission of answer
        if not skip:

            # Sanity check
            if not answer:
                _logger.error("%s\nTrying to submit answer with no answer provided", self)
                return

            # region Submitting date

            if self._DATE_KEY in self._cache.keys():

                # Date with time specified
                if isinstance(answer, Mapping):
                    # Sanity check
                    if not ("date" in answer.keys() and "hour" in answer.keys() and "minute" in answer.keys()):
                        _logger.error("%s\nTrying to answer a date without date/hour/minute, answer=%s", self, answer)
                        return
                    elif not (self._HOUR_KEY in self._cache.keys() and self._MINUTE_KEY in self._cache.keys()):
                        _logger.error("%s\nTrying to answer a time without hour/minute elements, "
                                      "hour_element=%s, minute_element=%s",
                                      self, self._cache.get(self._HOUR_KEY), self._cache.get(self._MINUTE_KEY))
                        return
                    date = answer.get("date")
                    _submit_time(self._cache.get(self._HOUR_KEY), self._cache.get(self._MINUTE_KEY),
                                 answer.get("hour"), answer.get("minute"))

                # Date without time specified
                elif isinstance(answer, str):
                    if not answer:
                        _logger.error("%s\nTrying to answer a date without date, answer=%s", self, answer)
                        return
                    date = answer

                else:
                    _logger.error("%s\nTrying to answer a date with answer=%s", self, answer)
                    return

                # Ensure date is of correct format
                try:
                    date_time = datetime.strptime(date, "%Y-%m-%d")
                    if date_time > datetime.strptime("2071-01-01", "%Y-%m-%d"):
                        raise ValueError
                    date = date_time.strftime("%d%m%Y")
                except ValueError:
                    _logger.error("%s\nTrying to answer a date with date=%s", self, date)
                    return

                self._perform_submission((self._cache.get(self._DATE_KEY), date, None))

            # endregion Submitting date

            # region Submitting time / duration

            elif self._HOUR_KEY in self._cache.keys() and self._MINUTE_KEY in self._cache.keys():

                # Sanity check
                if not isinstance(answer, Mapping):
                    _logger.error("%s\nTrying to answer a time/duration with answer=%s", self, answer)
                    return
                elif not ("hour" in answer.keys() and "minute" in answer.keys()):
                    _logger.error("%s\nTrying to answer a time/duration without hour and/or minute, answer=%s",
                                  self, answer)
                    return

                hour, minute = answer.get("hour"), answer.get("minute")
                if not (isinstance(hour, str) and isinstance(minute, str)):
                    _logger.error("%s\nTrying to answer a time/duration with hour=%s, minute=%s", self, hour, minute)
                    return

                # region Submitting duration

                if self._SECOND_KEY in self._cache.keys():

                    # Sanity check
                    if "second" not in answer.keys():
                        _logger.error("%s\nTrying to answer a duration without second, answer=%s", self, answer)
                        return

                    second = answer.get("second")
                    if not isinstance(second, str):
                        _logger.error("%s\nTrying to answer a duration with second=%s", self, second)
                        return

                    # Ensure duration is valid
                    try:
                        hour_int, minute_int, second_int = int(hour), int(minute), int(second)
                        if not (0 <= hour_int <= 72 and 0 <= minute_int <= 59 and 0 <= second_int <= 59):
                            raise ValueError
                    except ValueError:
                        _logger.error("%s\nTrying to answer a time with hour=%s, minute=%s, second=%s",
                                      self, hour, minute, second)
                        return

                    self._perform_submission((self._cache.get(self._HOUR_KEY), hour, None),
                                             (self._cache.get(self._MINUTE_KEY), minute, None),
                                             (self._cache.get(self._SECOND_KEY), second, None))

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
                    _logger.error("%s\nTrying to answer a dropdown with answer=%s", self, answer)
                    return

                # Open drop-down menu and crawl for answer element
                self._perform_submission((self._cache.get(self._PLACEHOLDER_KEY), None, None))
                menu_elements = self._cache.get(self._DROPDOWN_MENU_KEY).find_elements_by_class_name(
                    dropdown_class_name)[1:]

                # Find element to submit
                has_submitted = False
                for element in menu_elements:
                    if element.text == answer:
                        self._perform_submission((element, None, None))
                        has_submitted = True
                        break

                # Error catcher
                if not has_submitted:
                    _logger.error("%s\nUnable to find %s option in drop-down menu", self, answer)
                    return

            # endregion Submitting drop-down

            # region Submitting non-grid radio button / checkbox / linear scale

            elif self._OTHER_KEY in self._cache.keys():

                def _submit(selection: str) -> None:
                    """Helper function to perform submission.

                    :param selection: The user selection to submit.
                    """

                    if selection in self._cache.keys() and selection != self._OTHER_KEY:
                        self._perform_submission((self._cache.get(selection), None, None))

                    # Handle 'Other' input
                    else:
                        if not self._cache.get(self._OTHER_KEY):
                            _logger.error("%s\nNo 'Other' elements initialised", self)
                            return
                        self._perform_submission((
                            self._cache.get(self._OTHER_KEY).get(self._OTHER_SELECT_KEY),
                            self._cache.get(self._OTHER_KEY).get(self._OTHER_INPUT_KEY),
                            selection
                        ))

                # Sanity check
                if isinstance(answer, Mapping):
                    _logger.error("%s\nTrying to answer non-grid based question with answer=%s", self, answer)
                    return

                elif isinstance(answer, str):
                    _submit(answer)
                else:
                    for selection in answer:
                        _submit(selection)

            # endregion Submitting non-grid radio button / checkbox / linear scale

            # region Submitting textbox / paragraph

            elif self._TEXT_KEY in self._cache.keys():

                # Sanity check
                if not isinstance(answer, str):
                    _logger.error("%s\nTrying to answer a textbox/paragraph with answer=%s", self, answer)
                    return

                self._perform_submission((self._cache.get(self._TEXT_KEY), answer, None))

            # endregion Submitting textbox / paragraph

            # region Submitting grid-based radio button / checkbox

            else:

                # Sanity check
                if not isinstance(answer, Mapping):
                    _logger.error("%s\nTrying to answer a grid-based question with answer=%s", self, answer)
                    return
                elif not set(answer.keys()).issubset(set(self._cache.keys())):
                    _logger.error("%s\nTrying to answer a grid-based question with answer=%s, questions=%s",
                                  self, answer, self._cache.keys())
                    return

                for sub_question in answer.keys():
                    selections = answer.get(sub_question)
                    if isinstance(selections, str):
                        self._perform_submission((self._cache.get(sub_question).get(selections), None, None))
                    elif isinstance(selections, Sequence):
                        self._perform_submission(*((self._cache.get(sub_question).get(selection), None, None)
                                                   for selection in selections))
                    else:
                        # This should never trigger
                        _logger.error("%s\nSubmitting grid-based answer with unsupported answer type\n"
                                      "answer=%s, instance=%s", self, selections, type(selections))
                        return

            # endregion Submitting grid-based radio button / checkbox

            _logger.info("%s\nQuestion has been successfully answered!\nanswer: %s", self, answer)

        else:
            _logger.info("%s\nQuestion has been successfully skipped!", self)

        # Clear self._cache if the question has been processed successfully
        self._cache.clear()


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
    question = processor.get_next_question(True)
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
            processor.answer_question(answer=answer)
        else:
            processor.answer_question(skip=True)
        question = processor.get_next_question()
