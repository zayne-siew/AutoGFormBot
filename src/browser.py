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
import os
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
import time
from typing import Any, Callable, Optional, TypeVar, cast
# from webdriver_manager.chrome import ChromeDriverManager  # Uncomment this line for local testing only

# region Define constants

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)

# Type-hinting for decorator functions
_F = TypeVar('_F', bound=Callable[..., Any])

# Browser-based constants
_NUM_MAX_RETRIES = 5
_TIMEOUT_SECONDS = 8  # NOTE: some multiple of 8

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
        _IMPLICIT_WAIT  The time (in seconds) to wait implicitly.
        _COUNTER        The number of browsers instantiated.
    """

    # region Constructors

    def __init__(self, link: str, *, headless: Optional[bool] = False, max_retries: Optional[int] = _NUM_MAX_RETRIES,
                 timeout: Optional[int] = _TIMEOUT_SECONDS, implicit_wait: Optional[int] = 0) -> None:
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
        self._IMPLICIT_WAIT = implicit_wait
        self._BROWSER = None

        # Instantiate browser
        self._set_browser()

    def __repr__(self) -> str:
        """Overriden __repr__ of Browser class.

        :return: The __repr__ string.
        """

        return super().__repr__() + ": link={}, browser={}, counter={}, headless={}, max_retries={}, timeout={}, " \
                                    "implicit_wait={}".format(self._LINK, repr(self._BROWSER), self._COUNTER,
                                                              self._HEADLESS, self._MAX_RETRIES, self._TIMEOUT,
                                                              self._IMPLICIT_WAIT)

    def __str__(self) -> str:
        """Overriden __str__ of Browser class.

        :return: The __str__ string.
        """

        return "Selenium Chrome browser for {}, attempt {}{}" \
            .format(self._LINK, self._COUNTER, ", running headless" if self._HEADLESS else "")

    def __eq__(self, other: "Browser") -> bool:
        """Overriden __eq__ of Browser class.

        Two Browser class instances are equal if their attributes are equal.

        :param other: The other Browser instance to compare.
        :return: Whether the two instances are equal.
        """

        return self._LINK == other._LINK and self._HEADLESS == other._HEADLESS and self._COUNTER == other._COUNTER \
            and self._MAX_RETRIES == other._MAX_RETRIES and self._TIMEOUT == other._TIMEOUT \
            and self._IMPLICIT_WAIT == other._IMPLICIT_WAIT

    # endregion Constructors

    # region Helper functions

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
                    # The actual function, hopefully this executes once and passes
                    result = function(*args, **kwargs)
                    passed = True

                except WebDriverException:
                    _logger.warning("An exception while using selenium library functions has been detected")

                    # Case 1: args[0] is the current Browser object
                    if isinstance(args[0], Browser):
                        if not args[0].retry_browser():
                            break

                    # Case 2: assert that args[0] is either a FormProcessor or BaseQuestion instance
                    # assert that args[0] is the 'self' variable
                    # NOTE: DO NOT IMPORT FORMPROCESSOR OR BASEQUESTION; WILL RESULT IN CIRCULAR IMPORT
                    else:
                        # Utilise the get_browser() function written in both
                        # FormProcessor and BaseQuestion instances
                        if not args[0].get_browser().retry_browser():
                            break

            # Finally, return the function result if it passed
            # Or if the loop had to end due to retry_browser() failing, return None
            return result
        return cast(_F, _wrapper)

    def get_link(self) -> str:
        """Gets the link that the browser is hosting.

        :return: The link that the browser is hosting.
        """

        return self._LINK

    # endregion Helper functions

    # region Browser functions

    def get_browser(self) -> Optional[WebDriver]:
        """Gets the selenium browser.

        :return: The selenium browser, if it has been successfully initialised.
        """

        # Sanity check
        if not self._BROWSER:
            _logger.warning("Browser trying to get browser that has not been initialised")
        return self._BROWSER

    def close_browser(self) -> None:
        """Closes any open browser for clean exit."""
        if self.get_browser():
            self._BROWSER.close()
            self._BROWSER = None

    @monitor_browser
    def _set_browser(self) -> None:
        """Initialises the selenium browser."""

        # Initialise ChromeOptions
        options = webdriver.ChromeOptions()
        options.add_argument("-incognito")
        options.add_argument("start-maximized")
        options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
        options.add_argument("user-agent={}".format(UserAgent().random))
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        if self._HEADLESS:
            options.add_argument("--headless")

        # Comment out this section for local testing only
        options.binary_location = os.environ.get("GOOGLE_CHROME_BIN", "/app/.apt/usr/bin/google_chrome")
        if "GOOGLE_CHROME_BIN" not in os.environ.keys():
            _logger.warning("GOOGLE_CHROME_BIN PATH variable not set!")
        executable_path = os.environ.get("CHROMEDRIVER_PATH", "/app/.chromedriver/bin/chromedriver")
        if "CHROMEDRIVER_PATH" not in os.environ.keys():
            _logger.warning("CHROMEDRIVER_PATH PATH variable not set!")

        # Initialise browser with link
        # self._BROWSER = webdriver.Chrome(executable_path=ChromeDriverManager(print_first_line=False).install(),
        #                                  options=options)  # Uncomment for local testing only
        self._BROWSER = webdriver.Chrome(executable_path=executable_path, options=options)
        self._BROWSER.get(self._LINK)
        self._BROWSER.implicitly_wait(self._IMPLICIT_WAIT)

    def retry_browser(self) -> bool:
        """Instantiates a new browser should the current one run into an error.

        Each initialisation takes incrementally longer to complete to try avoiding bot detection (if there is).
        If all else fails, the script is stopped and the browser is closed.

        :return True if a new browser was instantiated, False if the max_retries counter is hit.
        """

        # Reset all variables
        self.close_browser()

        if self._COUNTER == self._MAX_RETRIES:
            _logger.error("Browser unable to access form after %d retries", self._MAX_RETRIES)
            return False
        else:
            _logger.warning("Browser unable to access form, retry counter: %d", self._COUNTER)
            time.sleep(self._TIMEOUT)
            self._TIMEOUT *= 1.5
            self._COUNTER += 1
            self._set_browser()
            return True

    # endregion Browser functions

    # Declaring decorator as static method
    # Needs to be done here
    monitor_browser = staticmethod(monitor_browser)


if __name__ == '__main__':
    pass
