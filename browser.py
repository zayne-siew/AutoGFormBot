#!/usr/bin/env python3
"""
Handler for Selenium ChromeDriver object.

This script provides a selenium-based Chrome browser for hosting websites and crawling needs.
Control of the browser is maintained and monitored by this script.

For more details of the functionality of this script, please read the documentation of the Browser class.

Usage:
    Getter methods are documented in the Browser class.
    Decorate functions that use selenium-based functions with @Browser.monitor_browser.
    To close the browser: browser.close_browser()

TODO include dependencies
"""

from fake_useragent import UserAgent
from functools import wraps
import logging
from selenium import webdriver
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException
)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
import time
import traceback
from typing import Any, Callable, Optional, TypeVar, cast

# region Define constants

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)

# Type-hinting for decorator functions
_F = TypeVar('_F', bound=Callable[..., Any])

# Define chromedriver path
# _CHROMEDRIVER_PATH = os.environ["CHROMEDRIVER_PATH"]
_CHROMEDRIVER_PATH = "D:/software/chromedriver.exe"  # TODO push to server?

# Browser-based constants
_NUM_MAX_RETRIES = 5
_TIMEOUT_SECONDS = 8  # NOTE: some multiple of 8
_ACTION_BUFFER_SECONDS = 1

# endregion Define constants


class Browser(object):
    """
    Browser class for handling of Selenium ChromeDriver.

    This script controls and monitors a selenium-based chrome browser with the following functionalities:
        - Hosting of Google Form site via provided Google Form link.
        - Opening and closing of browser on command.
        - Retry with incremental timeout policy in case of web scraping error.

    In the event that the web scraping encounters an error, a retry with incremental timeout policy is implemented.
    This policy controls how and when the next browser should be opened (and the scraping restarted) via the following:
        _MAX_RETRIES: The maximum number of retries before the script is terminated.
        _TIMEOUT: The timeout (in seconds) before opening a new browser.

    Attributes:
        _LINK           The link to the Google Form to be processed.
        _HEADLESS       Flag to indicate if the browser should run headless.
        _BROWSER        The selenium-based Google browser to host the Google Form.
        _MAX_RETRIES    The maximum number of retries before the script is terminated.
        _TIMEOUT        The timeout (in seconds) before opening a new browser.
        _COUNTER        The number of browsers instantiated.
    """

    # region Constructors

    def __init__(self, link: str, *, headless: Optional[bool] = False, max_retries: Optional[int] = _NUM_MAX_RETRIES,
                 timeout: Optional[int] = _TIMEOUT_SECONDS) -> None:
        """Initialisation of the Browser class.

        :param link: The Google form link used by the FormProcessor.
        :param headless: Flag to indicate if the browser should run headless.
        :param max_retries: The maximum number of retries before the script is terminated.
        :param timeout: The timeout (in seconds) before opening a new browser.
        """

        # Initialise all variables
        self._LINK = link
        self._HEADLESS = headless
        self._COUNTER = 1
        self._MAX_RETRIES = max_retries
        self._TIMEOUT = timeout
        self._BROWSER = None

        # Instantiate browser
        self._set_browser()

    def __repr__(self) -> str:
        """Overriden __repr__ of Browser class.

        :return: The __repr__ string.
        """

        return super().__repr__() + ": link={}, browser={}, counter={}, headless={}, max_retries={}, timeout={}" \
            .format(self._LINK, repr(self._BROWSER), self._COUNTER, self._HEADLESS, self._MAX_RETRIES, self._TIMEOUT)

    def __str__(self) -> str:
        """Overriden __str__ of Browser class.

        :return: The __str__ string.
        """

        return "Selenium Chrome browser for {}, attempt {}{}" \
            .format(self._LINK, self._COUNTER, ", running headless" if self._HEADLESS else "")

    # endregion Constructors

    def monitor_browser(function: _F) -> _F:
        """Custom decorator for local functions using selenium library functions.

        The decorator puts the function parsed into a try-except clause to catch any selenium errors
        thrown during the execution of the selenium library functions.

        :param function: The local function using selenium library functions.
        :return: The local function with the try-except decorator.
        """

        # NOTE: According to type-hinting documentation, inner wrapper functions are small enough
        # such that not type-checking them should not pose too big an issue
        # https://mypy.readthedocs.io/en/stable/generics.html#declaring-decorators
        @wraps(function)
        def _wrapper(*args, **kwargs):
            result, passed = None, False
            while not passed:
                try:
                    result = function(*args, **kwargs)
                    passed = True
                except (InvalidSessionIdException, NoSuchElementException, TimeoutException, WebDriverException):
                    _logger.warning("An exception while using selenium library functions has been detected.\n"
                                    "Printing traceback: %s", traceback.print_exc())
                    # Assert first argument parsed is the 'self' object
                    if not args[0].retry_browser():
                        break
            return result
        return cast(_F, _wrapper)

    # region Getters and Setters

    def get_browser(self) -> WebDriver:
        """Gets the selenium browser.

        :return: The selenium browser.
        """

        return self._BROWSER

    def get_action_chains(self) -> ActionChains:
        """Gets the ActionChains object from the selenium browser.

        The ActionChains object is used to simulate user interaction with the browser.

        :return: The ActionChains object.
        """

        return ActionChains(self._BROWSER)

    @staticmethod
    def get_action_buffer() -> int:
        """Gets the value of _ACTION_BUFFER_SECONDS.

        :return: The value of _ACTION_BUFFER_SECONDS.
        """

        return _ACTION_BUFFER_SECONDS

    def get_link(self) -> str:
        """Gets the link that the browser is hosting.

        :return: The link that the browser is hosting.
        """

        return self._LINK

    @monitor_browser
    def _set_browser(self) -> None:
        """Initialises the selenium browser."""

        # Initialise ChromeOptions
        options = webdriver.ChromeOptions()
        options.add_argument("-incognito")
        options.add_argument("start-maximized")
        options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
        options.add_argument("user-agent={}".format(UserAgent().random))
        if self._HEADLESS:
            options.add_argument("--headless")
            options.add_argument("disable-gpu")

        # Initialise browser with link
        self._BROWSER = webdriver.Chrome(executable_path=_CHROMEDRIVER_PATH, options=options)
        # self._browser = webdriver.Chrome(options=options)  # webdriver will search for chromedriver by itself
        self._BROWSER.get(self._LINK)
        self._BROWSER.implicitly_wait(_ACTION_BUFFER_SECONDS)

    # endregion Getters and Setters

    def _retry_browser(self) -> bool:
        """Instantiates a new browser should the current one run into an error.

        Each initialisation takes incrementally longer to complete to try avoiding bot detection (if there is).
        If all else fails, the script is stopped and the browser is closed.

        :return True if a new browser was instantiated, False if the max_retries counter is hit.
        """

        # Reset all variables
        self.close_browser()

        if self._COUNTER == self._MAX_RETRIES:
            _logger.error("Browser _retry_browser Completely unable to access form after %d retries",
                          self, self._MAX_RETRIES)
            return False
        else:
            _logger.warning("Browser _retry_browser Unable to access form, retry counter: %d", self, self._COUNTER)
            time.sleep(self._TIMEOUT)
            self._TIMEOUT *= 1.5
            self._COUNTER += 1
            self._set_browser()
            return True

    def close_browser(self) -> None:
        """Closes any open browser for clean exit."""
        if self._BROWSER:
            self._BROWSER.close()
            self._BROWSER = None
        else:
            # Sanity check
            _logger.warning("Browser _close_browser() called but no browser to be closed", self)

    # Declaring decorator as static method
    # Needs to be done here
    monitor_browser = staticmethod(monitor_browser)


if __name__ == '__main__':
    pass
