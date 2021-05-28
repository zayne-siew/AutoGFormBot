#!/usr/bin/env python3
"""
Abstract base classes (ABCs) for Google Form questions.

This script serves as an interface for documenting function implementation.

Usage:
    This script should not be used directly, other than its ABC functionalities.

TODO include dependencies
"""

from abc import ABC, abstractmethod
from selenium.webdriver.remote.webelement import WebElement
from typing import Any, Optional, Tuple


class AbstractQuestion(ABC):
    """AbstractQuestion class as ABC for custom Google Form question classes."""

    # region Getter methods

    @abstractmethod
    def _get_question_element(self) -> Optional[WebElement]:
        """Gets the web element which represents the entire question."""
        pass

    @abstractmethod
    def get_header(self) -> Optional[str]:
        """Gets the question header."""
        pass

    @abstractmethod
    def get_description(self) -> Optional[str]:
        """Gets the question description."""
        pass

    @abstractmethod
    def is_required(self) -> Optional[bool]:
        """Checks if the question is required."""
        pass

    @abstractmethod
    def get_answer_elements(self) -> Any:
        """Gets the web elements related to answering of the question."""
        pass

    # endregion Getter methods

    # region Setter methods

    @abstractmethod
    def _set_header(self, header: str) -> None:
        """Sets the question header."""
        pass

    @abstractmethod
    def set_question_element(self, element: WebElement) -> None:
        """Sets the web element representing the entire question if it has changed."""
        pass

    @abstractmethod
    def set_answer_elements(self, *args, **kwargs) -> None:
        """Sets the web elements required for answering the question if it has changed."""
        pass

    @abstractmethod
    def set_description(self, description: str) -> None:
        """Sets the question description if it has changed."""
        pass

    @abstractmethod
    def set_required(self, required: bool) -> None:
        """Toggles the required flag if it has changed."""
        pass

    # endregion Setter methods

    @abstractmethod
    def _is_valid(self, *elements: WebElement) -> bool:
        """Check if the web element(s) is/are still valid."""
        pass

    @abstractmethod
    def get_info(self) -> Optional[bool]:
        """Obtains question metadata from Google Form."""
        pass

    @abstractmethod
    def answer(self, *args, **kwargs) -> Optional[bool]:
        """Provide instruction to answer the question."""
        pass


class AbstractOptionQuestion(ABC):
    """AbstractOptionQuestion class as ABC for custom Google Form question classes which offer options."""

    # region Getter methods

    @abstractmethod
    def get_options(self) -> Optional[Tuple[str, ...]]:
        """Gets a list of all possible options."""
        pass

    @abstractmethod
    def get_other_option_element(self) -> Optional[WebElement]:
        """Gets the web element for the other option input field."""
        pass

    # endregion Getter methods

    # region Setter methods

    @abstractmethod
    def _set_options(self, *options: str) -> None:
        """Sets the list of options provided if it has changed."""
        pass

    @abstractmethod
    def set_other_option_element(self, element: WebElement) -> None:
        """Sets the other option element if it has changed."""
        pass

    # endregion Setter methods

    @abstractmethod
    def _is_option(self, option: str) -> bool:
        """Check if the option is specified."""
        pass

    @abstractmethod
    def _has_other_option(self) -> bool:
        """Check if there is an 'Other' option specified."""
        pass


if __name__ == '__main__':
    pass
