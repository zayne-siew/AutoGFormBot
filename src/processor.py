#!/usr/bin/env python3
"""
Google Form processor script for hosting and scraping of Google Forms.

This script provides a processor object to handle the auto-processing of Google Forms.
The FormProcessor object simulates the Google Form website to perform scraping and auto-submission capabilities.

For more details on the functionality of this script, please view the documentation of the FormProcessor class.

This script works in tandem with handler.py to provide a user interface for users to submit Google Forms.
This script uses custom classes as representations of Google Form questions under the ./questions directory.

TODO include dependencies
"""

# region Imports

# External imports
from collections import deque
import logging
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.remote.webelement import WebElement
import time
from typing import Optional, Sequence, Tuple, Union

# Local imports
from browser import Browser
from questions import (
    BaseQuestion,
    BaseOptionGridQuestion,
    CheckboxQuestion,
    CheckboxGridQuestion,
    DateQuestion,
    DatetimeQuestion,
    DropdownQuestion,
    DurationQuestion,
    LAQuestion,
    RadioQuestion,
    RadioGridQuestion,
    SAQuestion,
    TimeQuestion
)

# endregion Imports

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class FormProcessor(object):
    """FormProcessor Class to handle the processing of Google Forms.

    This class takes the link to a Google Form and can perform the following capabilities:
    1. Automatic web scraping of each section of the Google Form.
    2. Automatic retrieval of each question, along with its provided metadata and options.
    3. Autofill of answers via simulating realistic user input.
    4. Auto-submission of form.

    Each FormProcessor object consists of a Browser object to host the Google Form for crawling
    and a FIFO list of stored questions scraped in the current section of the Google Form.
    Based on the question type, a questions class object is instantiated with the question metadata for later use.

    Attributes:
        _BROWSER        The Browser object to host the Google Form.
        _CURRENT        The current question instance processed and waiting to be answered.
        _QUESTIONS      Storage for questions in the current section of the Google Form awaiting processing.
    """

    # region Constructors

    def __init__(self, link: str, headless: Optional[bool] = False) -> None:
        """Initalisation of the FormProcessor object.

        :param link: The Google form link used by the FormProcessor.
        :param headless: Flag to indicate if the browser should run headless.
        """

        # Initialise all variables
        # self._BROWSER = Browser(link, headless=headless, implicit_wait=2)
        self._BROWSER = Browser(link, headless=headless)
        self._CURRENT = None
        self._QUESTIONS = deque()

    def __repr__(self) -> str:
        """Overriden __repr__ of FormProcessor class.

        :return: The __repr__ string.
        """

        return super().__repr__() + ": browser={}, current={}, questions={}" \
            .format(repr(self._BROWSER), repr(self._CURRENT), repr(self._QUESTIONS))

    def __str__(self) -> str:
        """Overriden __str__ of FormProcessor class.

        :return: The __str__ string.
        """

        return "FormProcessor with browser: {}".format(self._BROWSER)

    # endregion Constructors

    # region Handler functions for self._QUESTIONS

    def _add_questions(self, *questions: WebElement) -> None:
        """Stores web elements representing Google Form questions for futher processing.

        The function assumes the order in which the questions are parsed is the order in which they should be processed.
        For duplicate web elements (which should never trigger), the function removes them according to
        https://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-whilst-preserving-order

        :param questions: The web elements representating the questions obtained for storing.
        """

        # Sanity checks
        if len(questions) == 0:
            _logger.warning("FormProcessor trying to add questions but none specified")
            return
        elif len(set(questions)) != len(questions):
            # There should not be a duplicate, log for debugging
            _logger.warning("FormProcessor trying to append duplicate question web elements, questions=%s", questions)
            seen = set()
            questions = [question for question in questions if not (question in seen or seen.add(question))]

        self._QUESTIONS.extend(questions)

    def _clear_questions(self) -> None:
        """Clears all stored questions."""

        if len(self._QUESTIONS) == 0:
            _logger.info("FormProcessor clearing empty question cache")
        self._QUESTIONS.clear()

    def _get_next_question(self) -> Optional[WebElement]:
        """Obtains the next unprocessed question.

        :return: The next unprocessed question.
        """

        return self._QUESTIONS.popleft() if len(self._QUESTIONS) > 0 else None

    def _replace_questions(self, *questions: WebElement) -> bool:
        """Replaces outdated web elements stored with fresh ones.

        :param questions: The fresh question web elements as the replacement.
        :return: Whether the replacement performed was successful.
        """

        # Sanity check
        if len(questions) == 0:
            _logger.warning("FormProcessor trying to replace web elements with no replacement specified")
            return True
        elif len(questions) != len(self._QUESTIONS):
            _logger.error("FormProcessor trying to replace %d web elements with %d new ones",
                          len(self._QUESTIONS), len(questions))
            return False

        # Perform the replacement
        self._clear_questions()
        self._add_questions(*questions)
        return True

    @Browser.monitor_browser
    def _get_question_info(self, question: WebElement) -> Optional[BaseQuestion]:
        """Obtains the information of the Google Form question.

        Based on the web elements present in the question, the question is assigned to a question class instance
        where the relevant metadata is scraped and cached for later use.

        :param question: The element containing the Google form question.
        :return: A question class instance, depending on the web elements present.
        """

        # Sanity check for question
        result = False
        while not result:
            try:
                # Check freshness of question element
                _ = question.is_displayed()
                result = True
            except StaleElementReferenceException:
                # Try to get a new fresh web element instance of the question
                question = self.refresh_section()
                if not question:
                    break
        if not result:
            return

        # region Date and time questions, check for composite date-time questions

        result = None
        if question.find_elements_by_xpath(".//div[@data-supportsdate='true']"):
            result = DateQuestion(question, self._BROWSER)
        if question.find_elements_by_xpath(
                ".//input[@aria-label='{}']".format(TimeQuestion.get_hour_label())) and \
                question.find_elements_by_xpath(
                    ".//input[@aria-label='{}']".format(TimeQuestion.get_minute_label())):
            time_question = TimeQuestion(question, self._BROWSER)
            result = DatetimeQuestion(result, time_question) if result else time_question
        if result:
            return result

        # endregion Date and time questions, check for composite date-time questions

        # region Drop-down questions

        if question.find_elements_by_class_name(DropdownQuestion.get_class_name()):
            return DropdownQuestion(question, self._BROWSER)

        # endregion Drop-down questions

        # region Checkbox questions

        elif question.find_elements_by_class_name(CheckboxQuestion.get_class_name()):
            options = list(filter(lambda label: label,
                                  map(lambda element: element.get_attribute("aria-label"),
                                      question.find_elements_by_class_name(CheckboxQuestion.get_class_name()))))
            if BaseOptionGridQuestion.is_grid_option(*options):
                return CheckboxGridQuestion(question, self._BROWSER)
            else:
                return CheckboxQuestion(question, self._BROWSER)

        # endregion Checkbox questions

        # region Radio button questions

        elif question.find_elements_by_class_name(RadioQuestion.get_class_name()):
            options = list(filter(lambda label: label,
                                  map(lambda element: element.get_attribute("aria-label"),
                                      question.find_elements_by_class_name(RadioQuestion.get_class_name()))))
            if BaseOptionGridQuestion.is_grid_option(*options):
                return RadioGridQuestion(question, self._BROWSER)
            else:
                return RadioQuestion(question, self._BROWSER)

        # endregion Radio button questions

        # region Paragraph questions

        elif question.find_elements_by_class_name(LAQuestion.get_class_name()):
            return LAQuestion(question, self._BROWSER)

        # endregion Paragraph questions

        # region Duration questions

        elif question.find_elements_by_xpath(
                ".//input[@aria-label='{}']".format(DurationQuestion.get_hour_label())) and \
                question.find_elements_by_xpath(
                    ".//input[@aria-label='{}']".format(DurationQuestion.get_minute_label())) and \
                question.find_elements_by_xpath(
                    ".//input[@aria-label='{}']".format(DurationQuestion.get_second_label())):
            return DurationQuestion(question, self._BROWSER)

        # endregion Duration questions

        # region Textbox questions

        elif question.find_elements_by_class_name(SAQuestion.get_class_name()):
            return SAQuestion(question, self._BROWSER)

        # endregion Textbox questions

        # No recognised element(s) found
        else:
            _logger.error("FormProcessor _get_question_info no recognised elements found, please debug")
            return

    # endregion Handler functions for self._QUESTIONS

    # region Helper functions

    def get_browser(self) -> Browser:
        """Gets the Browser object.

        :return: The Browser object.
        """

        return self._BROWSER

    def get_current(self) -> Optional[BaseQuestion]:
        """Gets the current question instance.

        :return: The current question instance, if it has been set.
        """

        return self._CURRENT

    def reset(self) -> None:
        """Resets all variables."""

        self._BROWSER.close_browser()
        self._CURRENT = None
        self._clear_questions()

    # endregion Helper functions

    @Browser.monitor_browser
    def _get_next_section(self, to_click: Optional[bool] = True) -> Optional[Sequence[WebElement]]:
        """Obtains the next section of the form, if any, and returns all questions.

        The script autoclicks the 'Next' or 'Submit' button (whichever is present in the current section)
        and obtains the list of questions in the next section (if any).

        :param to_click: Whether the function should autoclick the 'Next' or 'Submit' button.
        :return: The list of questions in the next section if the 'Next' button was selected.
                 If None is returned, the form was either submitted automatically,
                                      or an exception was caught in Browser.monitor_browser.
        """

        # Define constants for web scraping
        submit_button_class_name = "appsMaterialWizButtonPaperbuttonLabel"
        question_class_name = "freebirdFormviewerComponentsQuestionBaseRoot"

        button, to_submit, questions = None, False, []

        # region Try obtaining the 'Next' button

        try:
            next_button = self._BROWSER.get_browser().find_element_by_xpath(
                "//span[contains(@class, '{}')]"
                "[contains(., 'Next')]".format(submit_button_class_name))
            button = next_button
        except NoSuchElementException:
            # If there is no 'Next' button, hopefully there is a 'Submit' button
            _logger.info("FormProcessor 'Next' button element could not be found, maybe 'Submit' button found instead")

        # endregion Try obtaining the 'Next' button

        # region Try obtaining the 'Submit' button

        if not button:
            try:
                submit_button = self._BROWSER.get_browser().find_element_by_xpath(
                    "//span[contains(@class, '{}')]"
                    "[contains(., 'Submit')]".format(submit_button_class_name))
                button = submit_button
                to_submit = True
            except NoSuchElementException:
                # Neither 'Next' nor 'Submit' buttons were found, flag as an error
                _logger.error("FormProcessor 'Submit' button element could not be found also")
                raise NoSuchElementException

        # endregion Try obtaining the 'Submit' button

        # Handle autoclicking
        if to_click:
            button.click()
            _logger.info("FormProcessor has automatically clicked the '%s' button element!",
                         "Submit" if to_submit else "Next")

        # Handle scraping of next section
        if not to_submit:
            _logger.info("FormProcessor is scraping the next section of the Google Form")
            time.sleep(2)  # Allow browser to finish loading the page, in case
            questions = self._BROWSER.get_browser().find_elements_by_class_name(question_class_name)

        return questions

    def refresh_section(self) -> Optional[WebElement]:
        """Re-crawl the Google Form section to refresh the web elements stored.

        :return: The refreshed web element for the current question if the refresh action was performed successfully,
                 None if an exception was caught.
        """

        # Re-obtain the questions from the current section
        questions = self._get_next_section(False)
        if not questions:
            return

        # Sanity check
        if len(questions) < len(self._QUESTIONS) + int(bool(self._CURRENT)):
            _logger.error("FormProcessor re-crawled %d questions but %d questions stored",
                          len(questions), len(self._QUESTIONS) + int(bool(self._CURRENT)))
            return

        # Refresh
        result = self._replace_questions(*questions[len(questions)-len(self._QUESTIONS):])
        if result:
            return questions[len(questions)-len(self._QUESTIONS)-1]

    def get_question(self, start: Optional[bool] = False) -> Union[bool, BaseQuestion]:
        """Obtains the next question in the Google Form.

        This function retrieves the next unanswered question in the Google Form as a question instance.

        :param start: Flag to indicate if the Google Form has just begun processing.
        :return: The question instance of the next unanswered question if all has been processed successfully,
                 True if the form has been successfully submitted,
                 and False if an error was encountered during _get_next_section or refresh_section.
        """

        def _try_next_section() -> Union[bool, WebElement]:
            """Helper function to obtain the next question of the next section of the Google Form.

            :return: The next question obtained if a question element is obtained,
                     True if the form has been successfully submitted,
                     and False if an error was encountered during _get_next_section.
            """

            # Sanity check for questions
            questions = self._get_next_section(not start)
            if not questions:
                # questions = [] if form has been submitted, else questions = None
                return isinstance(questions, Sequence)

            # Cache questions
            self._add_questions(*questions)
            result = self._get_next_question()
            return False if not result else result

        # Get the next question
        # If no questions found, crawl for more questions
        question = None
        if not start:
            question = self._get_next_question()
        if not question:
            question = _try_next_section()
            if isinstance(question, bool):
                return question

        # Create question instance from obtained question web element
        self._CURRENT = self._get_question_info(question)
        while not self._CURRENT:
            # Something went wrong, refresh and try again
            question = self.refresh_section()
            if not question:
                return False
            self._CURRENT = self._get_question_info(question)
        return self._CURRENT

    def answer_question(self, *answers: Union[str, Tuple[str, ...]], skip: Optional[bool] = False) -> Optional[bool]:
        """Submits the chosen answer for the current question in the Google Form.

        :param answers: The selected answer(s) to submit.
        :param skip: Flag to indicate if the question was skipped.
        :return: True if the submission was performed successfully, False otherwise.
                 Returns None if a sanity check failed or an exception was caught.
        """

        # Sanity check for current question
        if not self._CURRENT:
            _logger.error("FormProcessor trying to answer an unprocessed question.")
            return

        # Handle question skip
        elif skip:
            if self._CURRENT.is_required():
                _logger.error("FormProcessor trying to skip a required question, question=%s", self._CURRENT)
                return False
            # Question successfully skipped
            _logger.info("FormProcessor skipping question")

        # Handle submission of answer
        # Assume answers are parsed correctly
        else:

            # region Sanity checks

            # Basic sanity check for answers
            if len(answers) == 0:
                _logger.error("FormProcessor answer_question trying to submit answer with no answer provided")
                return

            # Sanity check for answer type
            elif not isinstance(self._CURRENT, CheckboxGridQuestion):
                for answer in answers:
                    if not isinstance(answer, str):
                        _logger.error("FormProcessor trying to answer question %s with answers %s",
                                      self._CURRENT, answers)
                        return

            # endregion Sanity checks

            # Answer question
            result = self._CURRENT.answer(*answers)
            if not result:
                return result
            _logger.info("FormProcessor question has been successfully answered")

        # Question has been processed successfully
        self._CURRENT = None
        return True


if __name__ == '__main__':
    pass
    # from src.questions import BaseOptionQuestion
    # form_url = "https://forms.gle/DwmmfPHGhkNsAVBc9"  # Personal test form
    # processor = FormProcessor(form_url)
    # question = processor.get_question(True)
    # while isinstance(question, BaseQuestion):

    #     # Process each question
    #     result = question.get_info()
    #     while result is False:
    #         # Re-crawl the web page to obtain a new question element
    #         element = processor.refresh_section()
    #         if not element:
    #             result = None
    #             break
    #         question.set_question_element(element)
    #         result = question.get_info()
    #     if result is None:
    #         # Some error occurred; to debug
    #         break

    #     # Display the question metadata
    #     print("Question Header:", question.get_header())
    #     print("Question Description:", question.get_description())
    #     print("Is question required?", question.is_required())
    #     if isinstance(question, BaseOptionQuestion):
    #         print("Options:", question.get_options())
    #     if isinstance(question, BaseOptionGridQuestion):
    #         print("Sub questions:", question.get_sub_questions())

    #     result = -1
    #     while result is False or result == -1:

    #         if result is False:
    #             # Refresh question
    #             element = processor.refresh_section()
    #             if not element:
    #                 result = None
    #                 break
    #             question.set_question_element(element)
    #             # question.answer_question() will call get_info() to refresh the answer elements

    #          # Obtain user input
    #         # Use "skip=True" to skip a question,
    #         # and "<answer>;<answer>;..." to denote multiple answers
    #         answers = None
    #         if isinstance(question, BaseOptionGridQuestion):
    #             answers = []
    #             for sub_question in question.get_sub_questions():
    #                 answer = input("Input answer for {}: ".format(sub_question))
    #                 if ";" in answer:
    #                      answer = tuple(answer.split(";"))
    #                 answers.append(answer)
    #             answers = tuple(answers)
    #         elif isinstance(question, BaseQuestion):
    #             answers = input("Input answer for {}: ".format(question.get_header()))
    #             if ";" in answers:
    #                 answers = tuple(answers.split(";"))

    #         # Answer the question
    #         if "skip=True" in answers:
    #             result = processor.answer_question(skip=True)
    #         elif isinstance(answers, Tuple):
    #             result = processor.answer_question(*answers)
    #         else:
    #             result = processor.answer_question(answers)

    #     # Continue if question was answered successfully
    #     if not result:
    #         break
    #     question = processor.get_question()

    # processor.reset()
