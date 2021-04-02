"""Google Form Handler

This script handles the interface for interacting with, crawling from and auto-filling of
the Google form used to submit the daily temperature(s).

Dependencies for this script include:
    - selenium
"""

import logging
import re
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
import time
from typing import Optional, Sequence, Tuple


def get_question_info(question: WebDriver) -> Tuple[str, Optional[Sequence[str]], Optional[Sequence[str]]]:
    """Obtains the information of the question asked in the current section of the Google form.

    Regardless of the answering mode of the question, the function obtains the question header,
    the options available for selection (if any) and the sub-questions in any grid-formatted checkbox / radio button
    answering mode (if any) and passes it on for futher processing.

    :param question: The element containing the Google form question.
    :return: The question header, along with all provided options (if any).
             The format of the return values is as follows:
             (QUESTION HEADER, [PROVIDED OPTIONS IF ANY], [GRID SUB-QUESTIONS IF ANY])
    """

    # region Define constants

    radio_linear_grid_class_name = "appsMaterialWizToggleRadiogroupEl"  # Radio Buttons / Linear Scale / Radio Grid
    checkbox_grid_class_name = "quantumWizTogglePapercheckboxEl"  # Checkboxes / Checkbox Grid
    dropdown_class_name = "quantumWizMenuPaperselectOption"  # Drop-down Options
    saq_date_time_class_name = "quantumWizTextinputPaperinputInput"  # Short-answer Textboxes / Date / Time / Duration
    para_class_name = "quantumWizTextinputPapertextareaInput "  # Long-answer Textboxes (Paragraphs)

    title_class_name = "freebirdFormviewerComponentsQuestionBaseTitle"  # Question Title
    answer_class_names = [radio_linear_grid_class_name, checkbox_grid_class_name, dropdown_class_name,
                          saq_date_time_class_name, para_class_name]

    # endregion Define constants

    # Obtain the question header
    header = question.find_element_by_class_name(title_class_name)
    header_text = str(header.text) if header else ""

    # Determine the answering mode of the question
    element_found, options, sub_questions = False, None, None
    for class_name in answer_class_names:
        elements = question.find_elements_by_class_name(class_name)
        if elements:
            element_found = True
            if class_name == dropdown_class_name:
                options = list(filter(lambda option: option,
                                      map(lambda element: element.get_attribute("data-value"), elements)))
            elif class_name == checkbox_grid_class_name or class_name == radio_linear_grid_class_name:
                # To differentiate between grid and non-grid, check the aria-label attribute value
                # For grids, the value should be in the following format:
                # CCC, response for RRR (CCC: column header, RRR: row header)
                labels = list(filter(lambda label: label,
                                     map(lambda element: element.get_attribute("aria-label"), elements)))
                if re.match(r"^([\w|\s]+)(, response for )([\w|\s]+)$", labels[0]):
                    labels = [re.split("(, response for )", label) for label in labels]
                    options = list(set([str(label[0]) for label in labels]))
                    sub_questions = list(set([str(label[2]) for label in labels]))
                else:
                    options = labels
            break

    # Final sanity check
    if not header_text:
        logging.log(logging.ERROR, "Unable to find question header")
    if not element_found:
        logging.log(logging.ERROR, "Unable to find any google form elements")
    return header_text, options, sub_questions


def main(options: webdriver.ChromeOptions):
    """Main function to crawl the Google form for further processing.

    A selenium browser is opened to attempt crawling for the form's inputs.

    :param options: ChromeOptions specified for the selenium browser.
    """

    # Define constants
    chromedriver_path = "D:/software/chromedriver.exe"
    form_url = "https://forms.gle/DwmmfPHGhkNsAVBc9"
    submit_button_class_name = "appsMaterialWizButtonPaperbuttonContent"
    question_class_name = "freebirdFormviewerComponentsQuestionBaseRoot"

    # Set up selenium browser
    browser = webdriver.Chrome(executable_path=chromedriver_path, options=options)
    browser.maximize_window()
    browser.get(form_url)

    # Crawl the form section by section, question by question
    while browser.find_element_by_class_name(submit_button_class_name):
        print("=====================================")
        print("             NEW SECTION             ")
        print("=====================================")
        questions = browser.find_elements_by_class_name(question_class_name)
        for question in questions:
            print("{} || {} || {}".format(*get_question_info(question)))
        print()
        # browser.find_element_by_class_name(submit_button_class_name).click()
        break  # TODO fill required questions with appropriate answers

    """
    # Differentiating between short-answer textboxes, date pickers, time pickers and duration pickers
    # Date pickers have attribute type="date" while the rest have attribute type="text"
    # The aria-label attribute values of the remaining answering modes are listed below
    # Short-answer textboxes have no aria-label attribute
    date_type = "date"
    time_hour_aria_label = "Hour"
    time_minute_aria_label = "Minute"
    duration_hours_aria_label = "Hours"
    duration_minutes_aria_label = "Minutes"
    duration_seconds_aria_label = "Seconds"
    """

    browser.close()


if __name__ == '__main__':

    # Configure ChromeOptions once before the main loop
    options = webdriver.ChromeOptions()
    options.add_argument("-incognito")
    options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
    # To run headless, disable the following:
    # options.add_argument("--headless")
    # options.add_argument("disable-gpu")

    # Set up retry counter in case the browser fails
    counter = 1
    max_retry = 5
    timeout = 8

    while True:
        try:
            main(options)
            break
        except NoSuchElementException:
            # If such an error occurs, the page is most likely unavailable
            # either due to page removal or due to bot detection
            if counter == max_retry:
                logging.log(logging.ERROR, "Completely unable to access form after {} retries".format(max_retry))
                break
            else:
                logging.log(logging.INFO, "Unable to access form, retry counter: {}".format(counter))
                time.sleep(timeout)
                counter += 1
                timeout *= 1.5
