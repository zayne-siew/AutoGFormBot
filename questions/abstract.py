#!/usr/bin/env python3
"""
Abstract base class (ABC) for Google Form questions.

This script serves as an interface for documenting function implementation.

Usage:
    This script should not be used directly, other than its ABC functionalities.

TODO include dependencies
"""

from abc import ABC, abstractmethod
from selenium.webdriver.remote.webelement import WebElement
from typing import Any, Optional, Tuple, Union


class AbstractQuestion(ABC):
    """AbstractQuestion class as ABC for custom Google Form question classes."""

    # region Getter methods

    @abstractmethod
    def _get_question_element(self) -> WebElement:
        """Gets the web element which represents the entire question."""
        pass

    @abstractmethod
    def get_header(self) -> str:
        """Gets the question header."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Gets the question description."""
        pass

    @abstractmethod
    def is_required(self) -> bool:
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
    def _set_question_element(self, element: WebElement) -> None:
        """Sets the web element representing the entire question if it has changed."""
        pass

    @abstractmethod
    def _set_answer_elements(self, *args, **kwargs) -> None:
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
    def _is_valid(self, element: WebElement) -> bool:
        """Check if the web element is still valid."""
        pass

    @abstractmethod
    def get_info(self) -> Optional[bool]:
        """Obtains question metadata from Google Form."""
        pass

    @abstractmethod
    def answer(self, *args, **kwargs) -> Tuple[WebElement, Optional[Union[str, WebElement]], Optional[str]]:
        """Provide instruction to answer the question."""
        pass


if __name__ == '__main__':
    pass
