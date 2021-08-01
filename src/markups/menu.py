#!/usr/bin/env python3
"""
Handler for custom options menu as Telegram inline keyboard markup.

This script standardises the initialisation of a custom options menu.

Usage:
    To obtain the pattern regex for CallbackQueryHandlers: markup.get_pattern()
    To initialise a menu keyboard markup: markup.get_markup()
    To process the callback data obtained: markup.perform_action(option)

TODO include dependencies
"""

import logging
from telegram import InlineKeyboardMarkup
from src.markups import BaseOptionMarkup
from typing import Optional, Tuple, Union

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


class MenuMarkup(BaseOptionMarkup):
    """MenuMarkup class for custom option menus as Telegram inline keyboards.

    Attributes
        _OPTIONS        Defined options available in the options menu.
        _REQUIRED       Flag to indicate if a response is required.
        _MULTI_SELECT   Flag to indicate if more than one option can be selected.
        _SELECTED       Selected options.
    """

    # Define constants
    _CLEAR = "CLEAR"
    _FINALISE = "FINALISE"

    # region Constructors

    def __init__(self, required: bool, multi_select: bool, *options: str) -> None:
        """Initialisation of MenuMarkup class.

        :param question: The question instance to obtain the menu markup from.
        """

        super().__init__(required, *options)
        self._MULTI_SELECT = multi_select
        self._SELECTED = []

    def __repr__(self) -> str:
        """Overriden __repr__ of MenuMarkup.

        :return: The __repr__ string.
        """

        return super().__repr__() + ", multi_select={}, selected={}".format(self._MULTI_SELECT, self._SELECTED)

    def __str__(self) -> str:
        """Overriden __str__ of MenuMarkup.

        :return: The __str__ string.
        """

        return super().__str__() + "\nSelected options: {}\nMultiple selection is{} allowed" \
            .format(self._SELECTED, " not" * (not self._MULTI_SELECT))

    # endregion Constructors

    # region Selected options handling

    def _clear_selected(self) -> None:
        """Helper function to clear all selected options."""

        if len(self._SELECTED) == 0:
            _logger.warning("MenuMarkup trying to clear selected options but no options have been selected")
        self._SELECTED.clear()

    def _is_selected(self, option: str) -> bool:
        """Helper function to determine if an option is selected.

        :param option: The option to determine if selected.
        :return: Flag to indicate if the option is selected.
        """

        return option in self._SELECTED

    def _toggle_selected(self, option: str) -> None:
        """Helper function to toggle an option as selected/unselected.

        If the option is currently unselected, the option is selected, and the other selected option
        is automatically unselected if multi-select is not enabled.

        If the option is currently selected, the option remains selected if there is only one option selected
        and an answer is required. Else, it is unselected.

        :param option: The option to toggle between selected/unselected.
        """

        # Sanity check
        if option not in self._OPTIONS:
            _logger.error("MenuMarkup trying to save invalid option '%s' as selected", option)
            return

        # Handle if option is currently selected
        elif option in self._SELECTED and (len(self._SELECTED) > 1 or not self._REQUIRED):
            self._SELECTED.remove(option)

        # Handle if option is currently unselected
        elif option not in self._SELECTED:
            if not self._MULTI_SELECT and len(self._SELECTED) == 1:
                self._SELECTED.clear()
            self._SELECTED.append(option)

    # endregion Selected options handling

    # region Getters

    def get_pattern(self, *_) -> str:
        """Gets the pattern regex for matching in ConversationHandler.

        :return: The pattern regex.
        """

        pattern = super().get_pattern()
        return pattern[:-2] + "|".join((self._CLEAR, self._FINALISE, self._SKIP)) + ")$"

    def get_markup(self, *_) -> InlineKeyboardMarkup:
        """Initialises the markup with parsed options.

        :return: The inline keyboard markup.
        """

        options = tuple(zip("✔ " * self._is_selected(option) + option for option in self.get_options()))
        buttons = ("Skip",) * (not self._REQUIRED) + ("Clear", "OK")
        return super().get_markup(*(options + (buttons,)),
                                  option_datas={"Clear": self._CLEAR, "OK": self._FINALISE, "Skip": self._SKIP})

    # endregion Getters

    # TODO update_other_option()

    def _is_option(self, option: str) -> bool:
        """Verify if the option parsed is defined.

        :param option: The option to verify.
        :return: Flag to indicate if the option is defined.
        """

        return super()._is_option(option) or option in (self._CLEAR, self._FINALISE)

    def perform_action(self, option: str) -> Optional[Union[InlineKeyboardMarkup, str, Tuple[str, ...]]]:
        """Perform action according to the callback data.

        :param option: The option received from the callback data.
        :return: The relevant action as determined by the callback data.
        """

        result = None
        if not self._is_option(option):
            # Assert that this will never trigger
            _logger.error("MenuMarkup perform_action received invalid option: %s", option)
        elif option == self._SKIP:
            result = self.get_required_warning() if self._REQUIRED else self._SKIP
        elif option == self._CLEAR:
            self._clear_selected()
            result = self.get_markup()
        elif option == self._FINALISE:
            if len(self._SELECTED) > 0:
                result = tuple(self._SELECTED) if len(self._SELECTED) > 1 else self._SELECTED[0]
            else:
                result = self.get_required_warning() if self._REQUIRED else self._SKIP
        else:
            self._toggle_selected(option)
            result = self.get_markup()
        return result


if __name__ == '__main__':
    pass
