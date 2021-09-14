#!/usr/bin/env python3
"""
Telegram bot script to handle all bot functionalities.

This script provides the mainframe to the Telegram bot interface.
The bot handles user-supervised auto-submission of Google Forms, along with other scheduling and customisation options.

Functionalities of the Telegram bot, in detail, include:
    - TODO Wrapper interface for Google Forms, for users to submit forms via the bot.
    - TODO Remembers answers for future auto-submission of forms.
    - TODO Scheduling of form auto-submission, up to 30-minute intervals.
    - TODO Backlogs past submissions for users to view and keep track.
    - TODO Allows users submitting the same form to keep track of one another's submissions.

This script works in tandem with processor.py to automate Google Form submissions.
This script uses custom-built inline keyboard markup templates under the ./markups directory.
This script uses custom classes as representations of Google Form questions under the ./questions directory.

TODO include dependencies
"""

# region Imports

# External imports
from collections import OrderedDict
from datetime import datetime
from functools import wraps
import logging
import os
import pytz
import random
import re
from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
    ParseMode,
    ReplyKeyboardRemove,
    Update
)
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    Job,
    MessageHandler,
    Updater
)
import traceback
from typing import Any, Callable, Optional, Tuple, TypeVar, Union, cast

# Local imports
from markups import (
    BaseMarkup,
    BaseOptionMarkup,
    DateMarkup,
    DatetimeMarkup,
    FreqCustomMarkup,
    FreqMarkup,
    MenuMarkup,
    SavePrefMarkup,
    TimeMarkup,
    TFMarkup
)
from processor import FormProcessor
from questions import (
    BaseQuestion,
    BaseOptionQuestion,
    BaseOptionGridQuestion,
    CheckboxQuestion,
    DateQuestion,
    DatetimeQuestion,
    DurationQuestion,
    TimeQuestion
)
import utils

# endregion Imports

# region Define constants

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)

# Type-hinting for decorator functions
_F = TypeVar('_F', bound=Callable[..., Any])

# region Telegram bot states

(
    # Main menu states
    _OBTAINING_LINK,  # Prompting user for Google Form link / main menu handling
    _SET_PREFERENCE,  # Set preference option in preference menu
    _SET_REMINDER,  # Schedule reminders in reminder menu
    _RESET,  # Reset option in main menu
    _CONFIRM_RESET,  # Prompting user to confirm reset

    # Submitting form states
    _OBTAIN_QUESTION,  # Processing of Google Form questions
    _SKIP_OR_ANSWER,  # Processing user input
    _ANSWER_OTHER,  # Processing user alternative selection via the 'Other' option
    _CONFIRM_SUBMIT,  # Confirmation and submission of answers to Google Form
    _SAVE_ANSWER,  # Determine user preference for saving answer

    # Preference menu states
    _EDIT_PREF_GLOBAL,  # User selection of global preference
    _EDIT_PREF_LOCAL,  # User selection of local preference
    _SELECT_QUESTION,  # User selection of question to set local preference for
    _CONFIRM_PREF_GLOBAL,  # User confirmation of global preference
    _CONFIRM_PREF_LOCAL,  # User confirmation of local preference

    # Reminder menu states
    _ADD_JOB,  # User selection to schedule new reminder
    _CHOOSE_FREQ,  # User selection of submission frequency
    _CUSTOM_FREQ,  # User customisation of submission frequency
    _SELECT_START,  # User selection of job starting date and time
    _CONFIRM_ADD,  # User confirmation to add job
    _REMOVE_JOB,  # User selection to remove job
    _SELECT_JOB,  # User selection of job to remove
    _CONFIRM_REMOVE,  # User confirmation to remove job

    # Miscellaneous
    _SELECTING_ACTION,  # Prompting user for action in main menu
    _STOPPING,  # Force stop in nested ConversationHandlers
    _CANCEL,  # Return to second-level menu in nested ConversationHandlers
    _RETURN  # Return to main menu from nested ConversationHandlers
) = utils.generate_random_signatures(27)

# endregion Telegram bot states

# region User data constants

(
    # For storing preference-related data
    _SAVE_PREFS,  # For storing of all save preferences
    _GLOBAL_SAVE_PREF,  # For storing of global save preference
    _LOCAL_SAVE_PREF,  # For storing of question save preferences and/or answers
    _PREF_KEY,  # For storing of individual question save preference
    _ANSWER_KEY,  # For storing of individual question answer

    # For Google Form processing
    _PROCESSOR,  # For storing of FormProcessor object
    _CURRENT_QUESTION,  # For storing of processed question
    _CURRENT_ANSWER,  # For storing of user-inputted answer(s)

    # For scheduling of jobs
    _CURRENT_JOB,  # For processing of scheduled/scheduling jobs
    _CURRENT_UPDATE,  # For storing of Google Form processing update instance

    # Miscellaneous
    _CURRENT_MARKUP,  # For storing of markup that is used to handle user input
    _CURRENT_PREF_KEY,  # For handling of local save preference
    _GARBAGE_INPUT_COUNTER  # For handling of unrecognised input
) = utils.generate_random_signatures(13)

# endregion User data constants

# region Garbage echoes

_ANTI_GARBAGE_PROMPT_AFTER = 5
_standard_replies = ("mmhmm", "...", "I'm boreddd", "zzz", "sigh", "😪", "😴", "{}", "'{}', {} said.", "'{}'\n\t- {}")
_rare_replies = (
    # Rare replies as easter eggs...?
    "🥚 Wow! An egg! 🥚\n"
    "It may or may not be Easter, but it's sure worth *something*",
    "🎂🎵 *Happy birthday to you;*\n"
    "🎵 *Happy birthday to you;*\n"
    "🎵 *Happy BIRTH-day to {};*\n"
    "🎵 *Happy birthday to youuuuuuuu!*",
    "Hi, yes, you're currently talking to the developer."
    "Please leave your message after the tone:"
)
_garbage_replies = _standard_replies * 9 + _rare_replies
_anti_garbage_replies = (
    "💡 AutoGFormBot Notification 💡\n"
    "Sorry to disturb your fun, but I'm not a conversation bot 😰.\n"
    "Can we go back to automating Google Forms, please? 🙏",
    "💡 AutoGFormBot Notification 💡\n"
    "Hi, I'd love to talk, but I'm not programmed to! 😔\n"
    "Did you know, my main purpose is actually to help you automate your Google Forms!\n"
    "How about we get started with that, hm? 😍",
    "💡 AutoGFormBot Notification 💡\n"
    "I'm feeling so useless... 😭\n"
    "I'm not being used for my intended purpose 😭.\n"
    "Could you... make me useful again? 😳👉👈"
)

# endregion Garbage echoes

# Telegram markup to return to main menu
_RETURN_CALLBACK_DATA = "RETURN"

# endregion Define constants

# region Helper functions


def _reset_garbage_counter(function: _F) -> _F:
    """Custom decorator to reset the _GARBAGE_INPUT_COUNTER.

    Entry into the parsed function indicates that the user has inputted recognised input.
    Hence, the garbage counter (unrecognised input counter) is reset before proceeding.

    :param function: The function that handles recognised input.
    :return: The decorated function.
    """

    @wraps(function)
    def _wrapper(update: Update, context: CallbackContext, *args: Any, **kwargs: Any) -> Any:
        """Custom wrapper function to reset the _GARBAGE_INPUT_COUNTER.

        Asserts that the functions that use this wrapper have the update and context parameters
        as the first two positional arguments, respectively.

        :param update: The Update instance to clear the counter from.
        :param context: The CallbackContext instance to clear the counter from.
        :return: The expected return value of the function.
        """

        if _GARBAGE_INPUT_COUNTER in context.user_data.keys() and context.user_data.get(_GARBAGE_INPUT_COUNTER) > 0:
            context.user_data[_GARBAGE_INPUT_COUNTER] = 0
        return function(update, context, *args, **kwargs)

    return cast(_F, _wrapper)


def _clear_cache(context: CallbackContext, keep_save_pref: Optional[bool] = True) -> None:
    """Helper function to clear the user data.

    :param context: The context containing the user data to clear.
    :param keep_save_pref: Flag to indicate whether to keep user preference for global answer save.
    """

    # Save global preferencec
    save_pref = None
    if keep_save_pref and _GLOBAL_SAVE_PREF in context.user_data.get(_SAVE_PREFS, {}).keys():
        save_pref = context.user_data.get(_SAVE_PREFS).get(_GLOBAL_SAVE_PREF)

    # Clear cache and stop all jobs
    if _PROCESSOR in context.user_data.keys() and isinstance(context.user_data.get(_PROCESSOR), FormProcessor):
        context.user_data.get(_PROCESSOR).reset()
    context.user_data.clear()
    for job in context.job_queue.jobs():
        job.schedule_removal()

    # Restore global save preference
    if save_pref:
        context.user_data[_SAVE_PREFS] = {_GLOBAL_SAVE_PREF: save_pref}


def _update_job_context(context: CallbackContext) -> None:
    """Helper function to update the CallbackContext instance of all scheduled jobs.

    :param context: The CallbackContext instance to use for updating.
    """

    for job in context.job_queue.jobs():
        try:
            update, job_context = job.context
            assert isinstance(update, Update)
            assert isinstance(context.user_data, dict)
        except ValueError:
            _logger.error("_update_job_context Job context not recognised: %s", job.context)
            return
        except AssertionError:
            _logger.error("_update_job_context AssertionError detected, please debug")
            return
        job.context = (update, context)

# endregion Helper functions

# region Start functions


@_reset_garbage_counter
def _start(update: Update, _: CallbackContext) -> str:
    """Handles the start and reset of the bot.

    Upon either /start command or reset, the bot obtains the link to the Google form for processing.

    :param update: The update instance that started / resetted the bot.
    :return: The _OBTAINING_LINK state for main menu handling.
    """

    # Prepare message
    text = "🎉 Welcome to AutoGFormBot! 🎉\n" \
           "Please give me a Google Form link to automate:"

    # Use normal message to prompt
    if update.message:
        update.message.reply_text(
            utils.text_to_markdownv2(text),
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=False,
            reply_markup=ReplyKeyboardRemove()
        )

    # Use callback query message to prompt
    elif update.callback_query:
        update.callback_query.edit_message_text(
            utils.text_to_markdownv2(text),
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=False
        )

    # Error occurred
    # Can't even utils.send_bug_message since no message instance is found
    else:
        _logger.error("Message class to send message not found: {}".format(update))
        return ConversationHandler.END

    return _OBTAINING_LINK


@_reset_garbage_counter
def _main_menu(update: Update, context: CallbackContext) -> str:
    """Handles the main menu.

    :param update: The update instance that submitted the link.
    :param context: The CallbackContext instance that submitted the link.
    :return: The _SELECTING_ACTION state for handling of menu options.
    """

    # region Initialise main menu

    reply_markup = BaseMarkup().get_markup(
        ("⚙️ Set preference", "⏰ Schedule jobs"),
        ("🔁 Reset", "👋 Exit"),
        "📡 Submit form now",
        option_datas={
            "⚙️ Set preference": _SET_PREFERENCE,
            "⏰ Schedule jobs": _SET_REMINDER,
            "🔁 Reset": _RESET,
            "👋 Exit": _STOPPING,
            "📡 Submit form now": _OBTAIN_QUESTION
        }
    )
    text = utils.text_to_markdownv2(
        "Welcome to the main menu! Here, you can:\n\n"
        "⚙️ Set save preferences for all questions.\n"
        "⏰ Select when and how often to automatically submit the form.\n"
        "🔁 Reset AutoGFormBot with a different Google Form.\n"
        "👋 Stop AutoGFormBot completely.\n"
        "📡 Submit the Google Form now.\n\n"
        "Please select an option:"
    )

    # endregion Initialise main menu

    # Check if CallbackQueryHandler called
    if update.callback_query:
        # Edit message to main menu
        update.callback_query.answer()
        update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)

    # region Check if MessageHandler called

    elif update.message:

        # There should not be a FormProcessor object already instantiated
        # If there is, the user input is a hack; treat as unrecognised noncommand
        if _PROCESSOR in context.user_data.keys():
            _echo(update, context)
            return _OBTAINING_LINK

        # Obtain link from user input
        entities = update.message.parse_entities([MessageEntity.URL, MessageEntity.TEXT_LINK])
        links = []
        for entity in entities:
            if entity == MessageEntity.TEXT_LINK:
                links.append(entities[entity].url)
            elif entity.type == MessageEntity.URL:
                links.append(entities[entity])

        # region Sanity check for links

        if len(links) == 0:
            update.message.reply_text(
                utils.text_to_markdownv2("‼️Sorry, I didn't get a link at all. ‼️\n"
                                         "Please give me a Google Form link to automate:"),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
                disable_web_page_preview=False
            )
            return _OBTAINING_LINK
        elif len(links) > 1:
            utils.send_potential_feature_message(update.message, "😰 I can only handle one link at a time! 😰")

        # endregion Sanity check for links

        # Save the link and initialise the main menu
        context.user_data[_PROCESSOR] = links[0]
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)

    # endregion Check if MessageHandler called

    # Error occurred
    # Can't use utils.send_bug_message since no message instance is found
    else:
        _logger.error("_main_menu message class to send message not found: %s", update)
        return ConversationHandler.END

    return _SELECTING_ACTION

# endregion Start functions

# region Setting preferences


@_reset_garbage_counter
def _pref_menu(update: Update, _: CallbackContext) -> str:
    """Handles the preference menu.

    :param update: The update instance that is handling the preference menu.
    :return: The _SELECTING_ACTION state for handling of menu options.
    """

    # region Initialisation

    try:
        assert update.callback_query
    except AssertionError as error:
        _logger.error("_pref_menu AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        return _STOPPING
    update.callback_query.answer()

    # endregion Initialisation

    # region Initialise preference menu

    reply_markup = BaseMarkup().get_markup(
        "🌎 Select general preference 🌎",
        "🔍 Edit preference per question 🔍",
        "🔙 Return to main menu 🔙",
        option_datas={
            "🌎 Select general preference 🌎": _EDIT_PREF_GLOBAL,
            "🔍 Edit preference per question 🔍": _EDIT_PREF_LOCAL,
            "🔙 Return to main menu 🔙": _RETURN_CALLBACK_DATA
        }
    )
    text = utils.text_to_markdownv2(
        "⚙️ PREFERENCE MENU ⚙️\n\n"
        "🌎 Select your general save preference.\n"
        "🔍 Edit your save preference for a specific question.\n"
        "🔙 Return to the main menu.\n\n"
        "Please select an option:"
    )

    # endregion Initialise preference menu

    update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    return _SELECTING_ACTION


@_reset_garbage_counter
def _select_global_pref(update: Update, context: CallbackContext) -> str:
    """Handles the selection of global preferences.

    :param update: The update instance to handle selecting the global preference.
    :param context: The CallbackContext instance to handle selecting the global preference.
    :return: The _CONFIRM_PREF_GLOBAL state to process global preference confirmation.
    """

    # region Initialisation

    try:
        assert update.callback_query
    except AssertionError as error:
        _logger.error("_select_global_pref AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        return _STOPPING
    update.callback_query.answer()

    # endregion Initialisation

    # Obtain previously-selected preference, if any
    text = ""
    if _GLOBAL_SAVE_PREF in context.user_data.get(_SAVE_PREFS, {}).keys():
        text += "Your current selected general preference is: {}\n\n".format(
            context.user_data.get(_SAVE_PREFS, {}).get(_GLOBAL_SAVE_PREF))

    # Format and output
    text += "Please select your general save preference:"
    update.callback_query.edit_message_text(utils.text_to_markdownv2(text),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=SavePrefMarkup.get_markup())
    return _CONFIRM_PREF_GLOBAL


@_reset_garbage_counter
def _confirm_global_pref(update: Update, context: CallbackContext) -> str:
    """Handles the confirmation of global preferences.

    :param update: The update instance to confirm the global preference.
    :param context: The CallbackContext instance to confirm the global preference.
    :return: The preference menu for further processing.
    """

    # region Initialisation

    try:
        assert update.callback_query.data
    except AssertionError as error:
        _logger.error("_confirm_global_pref AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    result = update.callback_query.data
    update.callback_query.answer()

    # endregion Initialisation

    # Ensure callback data is recognised
    if not SavePrefMarkup.is_option(result):
        _logger.error("_confirm_global_pref unrecognised preference received: %s", result)
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING

    # Save global preference
    if _GLOBAL_SAVE_PREF not in context.user_data.get(_SAVE_PREFS, {}).keys():
        context.user_data[_SAVE_PREFS] = {_GLOBAL_SAVE_PREF: None}
    context.user_data.get(_SAVE_PREFS)[_GLOBAL_SAVE_PREF] = result
    _update_job_context(context)
    return _pref_menu(update, context)


@_reset_garbage_counter
def _select_local_pref(update: Update, context: CallbackContext) -> str:
    """Handles the selection of local preferences.

    :param update: The update instance to handle selecting the local preference.
    :param context: The CallbackContext instance to handle selecting the local preference.
    :return: The _SELECT_QUESTION state to select a question.
    """

    # region Initialisation

    try:
        assert update.callback_query
    except AssertionError as error:
        _logger.error("_select_local_pref AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        return _STOPPING
    update.callback_query.answer()

    # endregion Initialisation

    # Check if Google Form has been processed before
    if _LOCAL_SAVE_PREF not in context.user_data.get(_SAVE_PREFS, {}).keys():
        update.callback_query.edit_message_text(
            utils.text_to_markdownv2("⚠️ NO QUESTIONS DETECTED ⚠️\n"
                                     "Please submit your Google Form at least once first!"),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data=_SET_PREFERENCE)]])
        )
        return _CANCEL

    # Format saved question preference keys for selection
    pref_keys = list(context.user_data.get(_SAVE_PREFS).get(_LOCAL_SAVE_PREF).keys())
    markup = [[InlineKeyboardButton(" | ".join((pref_key[0], pref_key[1] if pref_key[1] else "(no description)")),
                                    callback_data=str(pref_keys.index(pref_key)))] for pref_key in pref_keys]
    context.user_data[_CURRENT_PREF_KEY] = pref_keys
    update.callback_query.edit_message_text(utils.text_to_markdownv2("🔍 Please select a question:"),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=InlineKeyboardMarkup(markup))
    return _SELECT_QUESTION


@_reset_garbage_counter
def _question_pref(update: Update, context: CallbackContext) -> str:
    """Handles the selection of save preference for a specified question.

    :param update: The update instance to handle selection of save preference for a specified question.
    :param context: The CallbackContext instance to handle selection of save preference for a specified question.
    :return: The _CONFIRM_PREF_LOCAL state to confirm the selected preference.
    """

    # region Initialisation

    # Assertion check
    try:
        assert update.callback_query.data
        assert isinstance(context.user_data.get(_CURRENT_PREF_KEY), list)
        assert _LOCAL_SAVE_PREF in context.user_data.get(_SAVE_PREFS, {}).keys()
    except AssertionError as error:
        _logger.error("_question_pref AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING

    # Callback data check
    try:
        index = int(update.callback_query.data)
        result = context.user_data.get(_CURRENT_PREF_KEY)[index]
    except ValueError:
        _logger.error("_question_pref callback data is not valid: %s", update.callback_query.data)
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    update.callback_query.answer()

    # endregion Initialisation

    # Ensure question preference key is stored
    local_prefs = context.user_data.get(_SAVE_PREFS).get(_LOCAL_SAVE_PREF)
    if result not in local_prefs.keys():
        _logger.error("_question_pref unrecognised question preference key: %s", result)
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    context.user_data[_CURRENT_PREF_KEY] = result

    # region Formatting output

    # Format question preference key
    text = "{}\n" \
           "==============\n" \
           "{}{}\n\n".format(result[0], result[1] if result[1] else "(no description)",
                             "\n\nThis is a required question." if bool(result[2]) else "")

    # Obtain previously-selected preference, if any
    local_pref = local_prefs.get(result).get(_PREF_KEY)
    if SavePrefMarkup.is_option(local_pref):
        text += "Your current selected preference for this question is:\n{}\n".format(local_pref)
    elif local_pref:
        _logger.error("_question_pref unrecognised preference saved:\n"
                      "Question preference key: %s\n"
                      "Saved preference: %s", result, local_pref)
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING

    # Format and output
    text += "Please select your save preference for this question:"
    update.callback_query.edit_message_text(utils.text_to_markdownv2(text),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=SavePrefMarkup.get_markup())
    return _CONFIRM_PREF_LOCAL

    # endregion Formatting output


@_reset_garbage_counter
def _confirm_local_pref(update: Update, context: CallbackContext) -> str:
    """Handles the confirmation of local preferences.

    :param update: The update instance to confirm the local preference.
    :param context: The CallbackContext instance to confirm the local preference.
    :return: The preference menu for further processing.
    """

    # region Initialisation

    try:
        assert update.callback_query.data
        assert context.user_data.get(_CURRENT_PREF_KEY) in \
            context.user_data.get(_SAVE_PREFS, {}).get(_LOCAL_SAVE_PREF, {}).keys()
    except AssertionError as error:
        _logger.error("_confirm_local_pref AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    result = update.callback_query.data
    update.callback_query.answer()

    # endregion Initialisation

    # Ensure callback data is recognised
    if not SavePrefMarkup.is_option(result):
        _logger.error("_confirm_local_pref unrecognised preference received: %s", result)
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING

    # Save local preference
    context.user_data.get(_SAVE_PREFS).get(_LOCAL_SAVE_PREF).get(
        context.user_data.get(_CURRENT_PREF_KEY))[_PREF_KEY] = result
    _ = context.user_data.pop(_CURRENT_PREF_KEY)
    _update_job_context(context)
    return _pref_menu(update, context)


@_reset_garbage_counter
def _pref_return(update: Update, context: CallbackContext) -> str:
    """Handles returning from preference menu to main menu.

    :param update: The update instance to return to the main menu.
    :param context: The CallbackContext instance to return to the main menu.
    :return: The _RETURN state to return to the main menu.
    """

    _ = _main_menu(update, context)
    return _RETURN

# endregion Setting preferences

# region Creating reminders


@_reset_garbage_counter
def _remind_menu(update: Update, _: CallbackContext) -> str:
    """Handles the reminder menu.

    :param update: The update instance to handle the reminder menu.
    :return: The _SELECTING_ACTION state for handling of menu options.
    """

    # region Initialisation

    try:
        assert update.callback_query
    except AssertionError as error:
        _logger.error("_remind_menu AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        return _STOPPING
    update.callback_query.answer()

    # endregion Initialisation

    # region Initialise remind menu

    reply_markup = BaseMarkup().get_markup(
        "➕ Schedule new submission job ➕",
        "🗑️ Remove current submission job 🗑️",
        "🔙 Return to main menu 🔙",
        option_datas={
            "➕ Schedule new submission job ➕": _ADD_JOB,
            "🗑️ Remove current submission job 🗑️": _REMOVE_JOB,
            "🔙 Return to main menu 🔙": _RETURN_CALLBACK_DATA
        }
    )
    text = utils.text_to_markdownv2(
        "⏰ SCHEDULER MENU ⏰\n\n"
        "➕ Schedule a new submission job.\n"
        "🗑️ Remove a current submission job.\n"
        "🔙 Return to the main menu.\n\n"
        "Please select an option:"
    )

    # endregion Initialise remind menu

    update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    return _SELECTING_ACTION


@_reset_garbage_counter
def _remind_return(update: Update, context: CallbackContext) -> str:
    """Handles returning from reminder menu to main menu.

    :param update: The update instance to return to the main menu.
    :param context: The CallbackContext instance to return to the main menu.
    :return: The _RETURN state to return to the main menu.
    """

    _ = _main_menu(update, context)
    return _RETURN


def _auto_submit(context: CallbackContext) -> None:
    """Function to be called by each scheduled job to auto-submit Google Form.

    :param context: The CallbackContext instance to submit the Google Form.
    """

    # region Initialisation

    update = None
    try:
        update, job_context = context.job.context
        assert isinstance(update, Update)
        assert update.callback_query
        assert isinstance(job_context, CallbackContext)
        assert isinstance(job_context.user_data, dict)
    except AssertionError as error:
        _logger.error("_auto_submit AssertionError detected while trying to initialise:\n%s", error)
        if isinstance(update, Update):
            if update.message:
                utils.send_bug_message(update.message)
            elif update.callback_query:
                utils.send_bug_message(update.callback_query.message)
        return _STOPPING

    # endregion Initialisation

    # Check if another submission is currently being processed
    if isinstance(job_context.user_data.get(_PROCESSOR), FormProcessor):
        _logger.info("_auto_submit Scheduled job has been cancelled due to active submission attempt.")
        return

    # Attemot to auto-submit
    state = _obtain_question(update, job_context)
    if state == _STOPPING:
        try:
            update.callback_query.edit_message_text(utils.text_to_markdownv2("🚨 JOB ENCOUNTERED ERROR 🚨\n"
                                                                             "Please try again later."),
                                                    parse_mode=ParseMode.MARKDOWN_V2,
                                                    reply_markup=InlineKeyboardMarkup([[
                                                        InlineKeyboardButton("OK", callback_data=_SET_REMINDER)]]))
        except BadRequest:
            _logger.info("_auto_submit Error message already displayed.")

# region Adding job


@_reset_garbage_counter
def _select_frequency(update: Update, context: CallbackContext) -> str:
    """Handles selection of reminder frequency.

    :param update: The update instance to handle selection of reminder frequency.
    :param context: The CallbackContext instance to handle selection of reminder frequency.
    :return: The _CHOOSE_FREQ state for further processing.
    """

    # region Initialisation

    try:
        assert update.callback_query
    except AssertionError as error:
        _logger.error("_select_frequency AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        return _STOPPING
    update.callback_query.answer()

    # endregion Initialisation

    if _CURRENT_UPDATE not in context.user_data.keys():
        update.callback_query.edit_message_text(utils.text_to_markdownv2("⚠️ NO SUBMISSION DETECTED ⚠️\n"
                                                                         "Please submit the form at least once first!"),
                                                parse_mode=ParseMode.MARKDOWN_V2,
                                                reply_markup=InlineKeyboardMarkup(
                                                    [[InlineKeyboardButton("OK", callback_data=_SET_REMINDER)]]))
        return _CANCEL
    else:
        update.callback_query.edit_message_text(utils.text_to_markdownv2("How often should this job be run?"),
                                                parse_mode=ParseMode.MARKDOWN_V2,
                                                reply_markup=FreqMarkup.get_markup())
        return _CHOOSE_FREQ


@_reset_garbage_counter
def _fixed_frequency(update: Update, context: CallbackContext) -> str:
    """Displays menu to select start date.

    :param update: The update instance to display menu to select start date.
    :param context: The CallbackContext instance to display menu to select start date.
    :return: The _SELECT_START state to handle start date selection.
    """

    # region Initialisation

    try:
        assert update.callback_query
        assert _CURRENT_MARKUP not in context.user_data.keys()
        assert _CURRENT_JOB not in context.user_data.keys()
    except AssertionError as error:
        _logger.error("_fixed_frequency AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    context.user_data[_CURRENT_JOB] = update.callback_query.data
    update.callback_query.answer()

    # endregion Initialisation

    markup = DatetimeMarkup(True, from_date=datetime.now())
    context.user_data[_CURRENT_MARKUP] = markup
    update.callback_query.edit_message_text(utils.text_to_markdownv2("Please select your start date and time:"),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=markup.get_markup())
    return _SELECT_START


@_reset_garbage_counter
def _custom_frequency(update: Update, context: CallbackContext) -> str:
    """Displays menu to customise reminder frequency.

    :param update: The update instance to display menu to customise reminder frequency.
    :param context: The CallbackContext instance to display menu to customise reminder frequency.
    :return: The _CUSTOM_FREQ state to handle start date.
    """

    # region Initialisation

    try:
        assert update.callback_query
        assert _CURRENT_MARKUP not in context.user_data.keys()
    except AssertionError as error:
        _logger.error("_custom_frequency AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    update.callback_query.answer()

    # endregion Initialisation

    markup = FreqCustomMarkup()
    context.user_data[_CURRENT_MARKUP] = markup
    update.callback_query.edit_message_text(utils.text_to_markdownv2("Please select your frequency.\n"
                                                                     "(minimum frequency is 5 minutes)"),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=markup.get_markup())
    return _CUSTOM_FREQ


@_reset_garbage_counter
def _handle_custom(update: Update, context: CallbackContext) -> str:
    """Handles reminder frequency customisation.

    :param update: The update instance to handle reminder frequency customisation.
    ;param context: The CallbackContext instance to handle reminder frequency customisation.
    :return: THe relevant state for further processing.
    """

    # region Initialisation

    try:
        assert update.callback_query.data
        assert isinstance(context.user_data.get(_CURRENT_MARKUP), FreqCustomMarkup)
        assert _CURRENT_JOB not in context.user_data.keys()
    except AssertionError as error:
        _logger.error("_handle_custom AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    result = context.user_data.get(_CURRENT_MARKUP).perform_action(update.callback_query.data)
    if result == FreqCustomMarkup.get_invalid_message():
        update.callback_query.answer(result)
        return _CUSTOM_FREQ
    update.callback_query.answer()

    # endregion Initialisation

    # Handle result from FreqCustomMarkup
    if isinstance(result, InlineKeyboardMarkup):
        update.callback_query.edit_message_text(utils.text_to_markdownv2(update.callback_query.message.text),
                                                parse_mode=ParseMode.MARKDOWN_V2,
                                                reply_markup=result)
    elif isinstance(result, str):
        context.user_data[_CURRENT_JOB] = "Submit every " + result
        markup = DatetimeMarkup(True, from_date=datetime.now())
        context.user_data[_CURRENT_MARKUP] = markup
        update.callback_query.edit_message_text(utils.text_to_markdownv2("Please select your start date and time:"),
                                                parse_mode=ParseMode.MARKDOWN_V2,
                                                reply_markup=markup.get_markup())
        return _SELECT_START
    return _CUSTOM_FREQ


@_reset_garbage_counter
def _start_date(update: Update, context: CallbackContext) -> str:
    """Handles the selection of job start date.

    :param update: The update instance to handle the selection of job start date.
    :param context: The CallbackContext instance to handle the selection of job start date.
    :return: The relevant state for futher processing.
    """

    # region Initialisation

    try:
        assert update.callback_query.data
        assert isinstance(context.user_data.get(_CURRENT_MARKUP), DatetimeMarkup)
        assert isinstance(context.user_data.get(_CURRENT_JOB), str)
    except AssertionError as error:
        _logger.error("_start_date AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING

    # endregion Initialisation

    # Obtain result
    result = context.user_data.get(_CURRENT_MARKUP).perform_action(update.callback_query.data)
    if result == DatetimeMarkup.get_required_warning():
        update.callback_query.answer(result)
        return _SELECT_START

    # Handle result from DatetimeMarkup
    if isinstance(result, InlineKeyboardMarkup):
        update.callback_query.edit_message_text(utils.text_to_markdownv2(update.callback_query.message.text),
                                                parse_mode=ParseMode.MARKDOWN_V2,
                                                reply_markup=result)
    elif isinstance(result, str):
        job_name = "{}, starting from {}".format(context.user_data.get(_CURRENT_JOB), result)
        if context.job_queue.get_jobs_by_name(job_name):
            update.callback_query.answer("ALERT: An identical job already exists!")
            return _SELECT_START
        update.callback_query.answer()
        _ = context.user_data.pop(_CURRENT_MARKUP)
        context.user_data[_CURRENT_JOB] = job_name
        update.callback_query.edit_message_text(utils.text_to_markdownv2("Please confirm to schedule this job:\n"
                                                                         "{}".format(job_name)),
                                                parse_mode=ParseMode.MARKDOWN_V2,
                                                reply_markup=TFMarkup.get_markup())
        return _CONFIRM_ADD
    update.callback_query.answer()
    return _SELECT_START


@_reset_garbage_counter
def _confirm_add(update: Update, context: CallbackContext) -> str:
    """Handles confirmation of job to schedule.

    :param update: The update instance to confirm scheduled job.
    :param context: The CallbackContext instance to confirm scheduled job.
    :return: The _CANCEL state to go back to the reminder menu.
    """

    # region Initialisation

    try:
        assert update.callback_query.data
        assert isinstance(context.user_data.get(_CURRENT_UPDATE), Update)
        job_name = context.user_data.get(_CURRENT_JOB)
        assert isinstance(job_name, str)
        freq, start = job_name.split(", starting from ")
    except AssertionError as error:
        _logger.error("_confirm_add AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    except ValueError:
        _logger.error("_confirm_add Current job not recognised: %s", context.user_data.get(_CURRENT_JOB))
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    result = update.callback_query.data
    update.callback_query.answer()

    # endregion Initialisation

    # region Sanity check

    # Ensure callback data is valid
    if TFMarkup.confirm(result) is None:
        _logger.error("_confirm_add Invalid callback data received: %s", result)
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING

    # Ensure start date is valid
    try:
        start_datetime = datetime.strptime(start, "%Y-%m-%d %H:%M").astimezone(pytz.utc)
    except ValueError:
        _logger.error("_confirm_add Start date not recognised: %s", start)
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING

    # endregion Sanity check

    # Handle confirmation
    result = TFMarkup.confirm(result)
    if result:
        if freq == FreqMarkup.get_hourly():
            _ = context.job_queue.run_repeating(_auto_submit, 60 * 60, first=start_datetime, name=job_name,
                                                context=(context.user_data.get(_CURRENT_UPDATE), context))
        elif freq == FreqMarkup.get_daily():
            _ = context.job_queue.run_daily(_auto_submit, start_datetime.time(), name=job_name,
                                            context=(context.user_data.get(_CURRENT_UPDATE), context))
        elif freq == FreqMarkup.get_weekly():
            _ = context.job_queue.run_repeating(_auto_submit, 60 * 60 * 24 * 7, first=start_datetime, name=job_name,
                                                context=(context.user_data.get(_CURRENT_UPDATE), context))
        elif freq == FreqMarkup.get_monthly():
            _ = context.job_queue.run_monthly(_auto_submit, start_datetime.time(), start_datetime.day, name=job_name,
                                              context=(context.user_data.get(_CURRENT_UPDATE), context),
                                              day_is_strict=False)
        else:
            try:
                days, hours, minutes = re.findall(r"[0-9]+", freq)
                if not FreqCustomMarkup.valid_freq(int(days), int(hours), int(minutes)):
                    raise ValueError
            except ValueError:
                _logger.error("_confirm_add Frequency not recognised: %s", freq)
                utils.send_bug_message(update.callback_query.message)
                return _STOPPING
            _ = context.job_queue.run_repeating(_auto_submit, 60 * ((int(days) * 24 + int(hours)) * 60 + int(minutes)),
                                                first=start_datetime, name=job_name,
                                                context=(context.user_data.get(_CURRENT_UPDATE), context))

    # Final preparations
    _ = context.user_data.pop(_CURRENT_JOB)
    update.callback_query.edit_message_text(utils.text_to_markdownv2("🥳 Job successfully scheduled! 🥳" if result else
                                                                     "Scheduling of job aborted!"),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=InlineKeyboardMarkup([[
                                                InlineKeyboardButton("OK", callback_data=_SET_REMINDER)]]))
    return _CANCEL

# endregion Adding job

# region Removing job


@_reset_garbage_counter
def _confirm_removal(update: Update, context: CallbackContext) -> str:
    """Handles confirmation of removal of reminder.

    :param update: The update instance to handle confirmation of removal of reminder.
    :param context: The CallbackContext instance to handle confirmation of removal of reminder.
    :return: The _CONFIRM_REMOVE state to handle the confirmation input.
    """

    # region Initialisation

    try:
        assert update.callback_query.data
        assert _CURRENT_JOB not in context.user_data.keys()
    except AssertionError as error:
        _logger.error("_confirm_removal AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    result = update.callback_query.data
    update.callback_query.answer()

    # endregion Initialisation

    # Check if selected reminder exists
    jobs = context.job_queue.get_jobs_by_name(result)
    if len(jobs) == 0:
        _logger.error("_confirm_removal No jobs found with name: %s", result)
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    elif len(jobs) > 1:
        _logger.warning("_confirm removal Multiple jobs found with name %s, selecting first one. Please debug", result)

    # Display confirmation
    context.user_data[_CURRENT_JOB] = jobs[0]
    update.callback_query.edit_message_text(utils.text_to_markdownv2("⚠️ IRREVERSIBLE ACTION WARNING ⚠️\n"
                                                                     "Are you sure you want to remove this job?"),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=TFMarkup.get_markup())
    return _CONFIRM_REMOVE


# Dynamic callback handler
remind_handler = CallbackQueryHandler(_confirm_removal)


@_reset_garbage_counter
def _select_reminder(update: Update, context: CallbackContext) -> str:
    """Handles selection of scheduled reminder to remove.

    :param update: The update instance to handle selection of reminder.
    :param context: The CallbackContext instance to handle selection of reminder.
    :return: The _SELECTING_REMINDER state for removal confirmation.
    """

    # region Initialisation

    try:
        assert update.callback_query
    except AssertionError as error:
        _logger.error("_select_reminder AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        return _STOPPING
    update.callback_query.answer()

    # endregion Initialisation

    # Check if there are scheduled reminders
    jobs = context.job_queue.jobs()
    if len(jobs) == 0:
        update.callback_query.edit_message_text(
            utils.text_to_markdownv2("⚠️ NO REMINDERS DETECTED ⚠️\n"
                                     "There are no more reminders to remove!"),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("OK", callback_data=_SET_REMINDER)]])
        )
        return _CANCEL

    # Format and output all jobs
    remind_handler.pattern = re.compile("^(" + "|".join([job.name for job in jobs]) + ")$")
    markup = [[InlineKeyboardButton(job.name, callback_data=job.name) for job in jobs]]  # Maximum length of name is 59
    update.callback_query.edit_message_text(utils.text_to_markdownv2("🔍 Please select a job:"),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=InlineKeyboardMarkup(markup))
    return _SELECT_JOB


@_reset_garbage_counter
def _perform_removal(update: Update, context: CallbackContext) -> str:
    """Handles removal of reminder based on user input.

    :param update: The update instance to handle reminder removal.
    :param context: The CallbackContext instance to handle reminder removal.
    :return: The _CANCEL state to go back to the reminder menu.
    """

    # region Initialisation

    try:
        assert update.callback_query.data
        assert isinstance(context.user_data.get(_CURRENT_JOB), Job)
    except AssertionError as error:
        _logger.error("_perform_removal AssertionError detected while trying to initialise:\n%s", error)
        if update.message:
            utils.send_bug_message(update.message)
        elif update.callback_query:
            utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    result = update.callback_query.data
    update.callback_query.answer()

    # endregion Initialisation

    # Ensure callback data is valid
    if TFMarkup.confirm(result) is None:
        _logger.error("_perform_removal Invalid callback data received: %s", result)
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING

    # Handle confirmation
    result = TFMarkup.confirm(result)
    if result:
        context.user_data.get(_CURRENT_JOB).schedule_removal()

    # Final preparations
    _ = context.user_data.pop(_CURRENT_JOB)
    update.callback_query.edit_message_text(utils.text_to_markdownv2("Job successfully removed!" if result else
                                                                     "Removal successfully aborted!"),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=InlineKeyboardMarkup([[
                                                InlineKeyboardButton("OK", callback_data=_SET_REMINDER)]]))
    return _CANCEL

# endregion Removing job

# endregion Creating reminders

# region Processing form

# region Helper functions


def _submit_to_google_forms(processor: FormProcessor, *answers: Union[str, Tuple[str]]) -> Optional[bool]:
    """Parses the chosen answer(s) for submission via FormProcessor.

    This function assumes that multiple answers parsed into the function are in the order to be submitted.

    :param processor: The FormProcessor to submit the answer(s).
    :param answers: The selected answer(s) to submit.
    :return: True if the submission was performed successfully, False otherwise.
             Returns None if a sanity check failed or an exception was caught.
    """

    if len(answers) == 0:
        # Sanity check
        _logger.warning("_submit_to_google_forms No answers to parse")
        return True
    elif answers[0] == BaseOptionMarkup.get_skip() or answers[0] == "/skip":
        return processor.answer_question(skip=True)
    return processor.answer_question(*answers)


def _remove_current_pointers(context: CallbackContext) -> None:
    """Helper function to remove _CURRENT_QUESTION and _CURRENT_ANSWER from the context data.

    Assumes _CURRENT_QUESTION and _CURRENT_ANSWER have been processed.
    Note: _CURRENT_MARKUP is removed upon _submit_answer() initialisation.

    :param context: The CallbackContext instance to remove the data from.
    """

    keys_missing = ""
    if _CURRENT_QUESTION in context.user_data.keys():
        _ = context.user_data.pop(_CURRENT_QUESTION)
    else:
        keys_missing += "_CURRENT_QUESTION"
    if _CURRENT_ANSWER in context.user_data.keys():
        _ = context.user_data.pop(_CURRENT_ANSWER)
    else:
        keys_missing += " and " * bool(keys_missing) + "_CURRENT_ANSWER"
    if keys_missing:
        _logger.warning("_remove_current_pointers %s not found in context.user_data.keys()", keys_missing)


def _show_loading_screen(callback_query: CallbackQuery) -> None:
    """Helper function to show a loading screen while processing in the background.

    This method only works for CallbackQueryHandlers.

    :param callback_query: The CallbackQueryHandler instance to show the loading screen to.
    """

    try:
        callback_query.edit_message_text(utils.text_to_markdownv2("Please wait..."), parse_mode=ParseMode.MARKDOWN_V2)
    except BadRequest:
        _logger.info("_show_loading_screen already displayed")

# endregion Helper functions


@_reset_garbage_counter
def _process_answer(update: Update, context: CallbackContext) -> str:
    """Handler for processing user inputs.

    The function obtains user input from the relevant message / markup callback data
    and determines the appropriate follow-up action based on the input and the question metadata.

    :param update: The update instance to process the user input.
    :param context: The CallbackContext instance to process the user input.
    :return: The relevant state for further processing.
    """

    # region Handling handlers

    # Check if CallbackQueryHandler called
    if update.callback_query:
        markup = context.user_data.get(_CURRENT_MARKUP)
        try:
            assert update.callback_query.data is not None
            assert isinstance(markup, BaseOptionMarkup)
        except AssertionError as error:
            _logger.error("_process_answer AssertionError detected while processing CallbackQueryHandler:\n%s", error)
            if update.callback_query.message:
                utils.send_bug_message(update.callback_query.message)
            return _STOPPING
        result = markup.perform_action(update.callback_query.data)
        # Check if skip failed
        if result == BaseOptionMarkup.get_required_warning():
            update.callback_query.answer(result)
            return _SKIP_OR_ANSWER
        update.callback_query.answer()

    # Check if MessageHandler called
    elif update.message:
        result = update.message.text
        question = context.user_data.get(_CURRENT_QUESTION)
        try:
            assert isinstance(question, BaseQuestion)
        except AssertionError as error:
            _logger.error("_process_answer AssertionError detected while processing MessageHandler:\n%s", error)
            utils.send_bug_message(update.message)
            return _STOPPING

        # Check if skip failed
        if result == "/skip" and question.is_required():
            update.message.reply_text(
                utils.text_to_markdownv2("Sorry, I can't allow you to skip this question because it is required 😢"),
                parse_mode=ParseMode.MARKDOWN_V2)
            return _SKIP_OR_ANSWER

        # Check if user tried not to use the inline keyboard
        elif isinstance(context.user_data.get(_CURRENT_MARKUP), BaseOptionMarkup):
            utils.send_potential_feature_message(update.message,
                                                 "Sorry, please select your answer from the menu provided.")
            return _SKIP_OR_ANSWER

    # Error occurred
    # Can't use utils.send_bug_message since no message instance is found
    else:
        _logger.error("_process_answer message class to send message not found: {}".format(update))
        return _STOPPING

    # endregion Handling handlers

    # region Determine action according to result

    if isinstance(result, InlineKeyboardMarkup):
        update.callback_query.edit_message_text(utils.text_to_markdownv2(update.callback_query.message.text),
                                                parse_mode=ParseMode.MARKDOWN_V2,
                                                reply_markup=result)
    elif isinstance(result, str) or isinstance(result, Tuple):

        # Save answer into user data
        if isinstance(context.user_data.get(_CURRENT_ANSWER), OrderedDict):
            keys = list(context.user_data.get(_CURRENT_ANSWER).keys())
            for key in keys:
                if context.user_data.get(_CURRENT_ANSWER).get(key) is None:
                    context.user_data.get(_CURRENT_ANSWER)[key] = \
                        "" if result == BaseOptionMarkup.get_skip() or result == "/skip" else result
                    break
        else:
            context.user_data[_CURRENT_ANSWER] = result

        # Check if 'Other' option is selected
        if BaseOptionQuestion.get_other_option_label() in result:
            text = utils.text_to_markdownv2("Please specify your alternative option:")
            if update.message:
                update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=ReplyKeyboardRemove())
            else:
                update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2)
            return _ANSWER_OTHER

        # Prompt for user input
        text = utils.text_to_markdownv2("Are you sure you want to skip this question?"
                                        if result == BaseOptionMarkup.get_skip() or result == "/skip" else
                                        "Please confirm your answer:\n{}".format(result))
        tf_markup = TFMarkup.get_markup()
        if update.message:
            update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=tf_markup)
        else:
            update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=tf_markup)
        return _CONFIRM_SUBMIT

    return _SKIP_OR_ANSWER

    # endregion Determine action according to result


# Dynamic CallbackQueryHandler
answer_handler = CallbackQueryHandler(_process_answer)


@_reset_garbage_counter
def _process_other(update: Update, context: CallbackContext) -> str:
    """Handler for processing selection for specified 'Other' option.

    :param update: The update instance to process the 'Other' option selection.
    :param context: The CallbackContext instance to process the 'Other' option selection.
    :return: The relevant state for further processing.
    """

    # region Initialisation

    try:
        assert _CURRENT_MARKUP in context.user_data.keys()
        assert _CURRENT_ANSWER in context.user_data.keys()
    except AssertionError as error:
        _logger.error("_process_other AssertionError detected while trying to initialise:\n%s", error)
        utils.send_bug_message(update.message)
        return _STOPPING

    # endregion Initialisation

    # region Save answer

    result = context.user_data.get(_CURRENT_ANSWER)
    curr_key = None
    if isinstance(result, OrderedDict):
        for key in list(result.keys()):
            if BaseOptionQuestion.get_other_option_label() in result.get(key):
                curr_key = key
                result = result.get(key)
                break

    if isinstance(result, str):
        result = update.message.text
    else:
        result = list(context.user_data.get(_CURRENT_ANSWER))
        result[result.index(BaseOptionQuestion.get_other_option_label())] = update.message.text
        result = tuple(result)
    if curr_key:
        context.user_data.get(_CURRENT_ANSWER)[curr_key] = result
    else:
        context.user_data[_CURRENT_ANSWER] = result

    # endregion Save answer

    # Prompt for user input
    text = utils.text_to_markdownv2("Please confirm your answer:\n{}".format(result))
    tf_markup = TFMarkup.get_markup()
    if update.message:
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=tf_markup)
    else:
        update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=tf_markup)
    return _CONFIRM_SUBMIT


@_reset_garbage_counter
def _obtain_question(update: Update, context: CallbackContext, *, to_process: Optional[bool] = True) -> str:
    """Handler for obtaining Google Form questions.

    The function obtains the next question to be processed (or remains at the current question instance,
    if the user rejects any answer recommendations) and displays relevant question metadata awaiting user input.

    :param update: The update instance to obtain the Google Form question.
    :param context: The CallbackContext instance to obtain the Google Form question.
    :param to_process: Flag to indicate if the question should be processed.
    :return: The relevant state for further processing.
    """

    # region Initialisation

    try:
        assert update.callback_query
        assert _PROCESSOR in context.user_data.keys()
    except AssertionError as error:
        _logger.error("_obtain_question AssertionError detected while trying to initialise:\n%s", error)
        if update.callback_query.message:
            utils.send_bug_message(update.callback_query.message)
        elif update.message:
            utils.send_bug_message(update.message)
        return _STOPPING
    _show_loading_screen(update.callback_query)

    # endregion Initialisation

    # region Obtain the next Google Form question

    # Obtain FormProcessor
    processor = context.user_data.get(_PROCESSOR)
    start = False
    if not isinstance(processor, FormProcessor):
        assert isinstance(processor, str)
        processor = FormProcessor(processor, headless=True)
        context.user_data[_PROCESSOR] = processor
        start = True
        # Check if callback query (from main menu or scheduled job) is still valid
        try:
            update.callback_query.answer()
        except BadRequest:
            _logger.info("_obtain_question update.callback_query has expired, no need to answer")

    # Initialise new question instance based on Google Form question
    if _CURRENT_QUESTION not in context.user_data.keys():
        question = processor.get_question(start)
        if question is True:
            # No more questions, exit back to main menu
            update.callback_query.edit_message_text(
                utils.text_to_markdownv2("🥳 The form has submitted successfully! 🥳"),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                    utils.text_to_markdownv2("Return to main menu"), callback_data=_RETURN_CALLBACK_DATA)]])
            )
            processor.get_browser().close_browser()
            context.user_data[_PROCESSOR] = processor.get_browser().get_link()
            context.user_data[_CURRENT_UPDATE] = update
            _update_job_context(context)
            return _RETURN
        elif question is False or not isinstance(question, BaseQuestion):
            # Some error occurred
            _logger.error("_obtain_question error occurred while trying to obtain the next question")
            utils.send_bug_message(update.callback_query.message)
            return _STOPPING

        # Process the question
        context.user_data[_CURRENT_QUESTION] = question
        result = question.get_info()
        while result is False:
            # Re-crawl the web page to obtain a new question element
            element = processor.refresh_section()
            if not element:
                result = None
                break
            question.set_question_element(element)
            result = question.get_info()
        if not result:
            _logger.error("_obtain_question error occurred while trying to obtain the question information")
            utils.send_bug_message(update.callback_query.message)
            return _STOPPING

    # Retrieve question instance if it has been stored previously
    else:
        question = context.user_data.get(_CURRENT_QUESTION)
        if not isinstance(question, BaseQuestion):
            _logger.error("_obtain_question retrieving question that is not a question instance: %s", question)
            question = None
        if not question:
            utils.send_bug_message(update.callback_query.message)
            return _STOPPING

    # endregion Obtain the next Google Form question

    # region Obtain previously-stored answer, if any

    # Only process preferences if its a new question being processed and there are preferences stored
    answer, preference = None, None
    if to_process and _SAVE_PREFS in context.user_data.keys():

        # Check local preference first; it takes precedence over global preference
        if _LOCAL_SAVE_PREF in context.user_data.get(_SAVE_PREFS, {}).keys():
            prefs = context.user_data.get(_SAVE_PREFS, {}).get(_LOCAL_SAVE_PREF, {})

            # Check if there is a direct match
            # If so, operate on the answer and the corresponding preference
            if question.get_pref_key() in prefs.keys():

                # Obtain answer and preference
                try:
                    assert _PREF_KEY in prefs.get(question.get_pref_key(), {}).keys()
                    preference = prefs.get(question.get_pref_key(), {}).get(_PREF_KEY)
                    answer = prefs.get(question.get_pref_key(), {}).get(_ANSWER_KEY)
                except AssertionError:
                    _logger.error("AssertionError in _obtain_question while obtaining preference, please debug")
                    utils.send_bug_message(update.callback_query.message)
                    return _STOPPING

                # Determine action based on answer and preference
                if not SavePrefMarkup.is_option(preference):
                    _logger.error("_obtain_question obtained preference which is not defined: %s", preference)
                    utils.send_bug_message(update.callback_query.message)
                    return _STOPPING
                if answer:
                    if preference == SavePrefMarkup.get_save_always():
                        if isinstance(answer, OrderedDict):
                            result = _submit_to_google_forms(processor, *answer.values())
                        elif isinstance(answer, tuple):
                            result = _submit_to_google_forms(processor, *answer)
                        else:
                            result = _submit_to_google_forms(processor, str(answer))
                        if result:
                            _remove_current_pointers(context)
                            return _obtain_question(update, context)  # Process the next question
                        else:
                            _logger.error("_obtain_question failed to submit to google forms, please debug")
                            return _STOPPING
                    elif preference == SavePrefMarkup.get_never_save():
                        # There should not be any saved answers
                        _logger.warning("_obtain_question obtained preference of never save but answer is recorded, "
                                        "please debug: key=%s, answer=%s", question.get_pref_key(), answer)

            # Else, check if there is a close match
            # A close match is defined as a question header match,
            # with either the description or the required flag mismatch (but not both)
            else:
                for pref_key in prefs.keys():
                    try:
                        assert isinstance(pref_key, tuple) and len(pref_key) == 3
                        header, description, required = question.get_pref_key()
                        if header == pref_key[0] and (description == pref_key[1] or required == pref_key[2]):
                            answer = prefs.get(pref_key, {}).get(_ANSWER_KEY)
                            # Discard preference; answer will be recommended to user
                            break
                    except AssertionError as error:
                        _logger.error("_obtain_question AssertionError detected while obtaining preference, "
                                      "please debug:\n%s", error)
                        utils.send_bug_message(update.callback_query.message)
                        return _STOPPING

    # endregion Obtain previously-stored answer, if any

    # region Display the question metadata

    text = "{}\n" \
           "==============\n" \
           "{}{}".format(question.get_header(),
                         question.get_description() if question.get_description() else "(no description)",
                         "\n\nThis is a required question." if question.is_required() else "")

    # Format sub-question for grid-based questions
    sub_question = None
    if isinstance(question, BaseOptionGridQuestion):
        if _CURRENT_ANSWER not in context.user_data.keys():
            context.user_data[_CURRENT_ANSWER] = OrderedDict((q, None) for q in question.get_sub_questions())

        # Obtain the next sub-question to process
        for key, value in context.user_data.get(_CURRENT_ANSWER, OrderedDict()).items():
            if value is None:
                sub_question = key
                break
        if sub_question is None:
            _logger.error("_obtain_question unable to find next sub-question to process\n"
                          "sub_questions: %s", context.user_data.get(_CURRENT_ANSWER, OrderedDict()))
            utils.send_bug_message(update.callback_query.message)
            return _STOPPING
        text += "\n\nProcessing answer for {}.".format(sub_question)

        # Obtain relevant saved answer, if any
        if answer and not isinstance(answer, OrderedDict):
            _logger.warning("_obtain_question unexpected saved answer for %s\n"
                            "question=%s, answer=%s", question.__class__.__name__, question, answer)
            _ = context.user_data.get(_SAVE_PREFS, {}).get(_LOCAL_SAVE_PREF, {}).pop(question.get_pref_key())
            answer = None

    # Format saved answers
    if to_process and bool(answer):
        if _CURRENT_ANSWER not in context.user_data.keys():
            context.user_data[_CURRENT_ANSWER] = answer

        # Obtain relevant saved answer from grid-based question, if any
        if isinstance(question, BaseOptionGridQuestion):
            assert isinstance(answer, OrderedDict) and isinstance(context.user_data.get(_CURRENT_ANSWER), OrderedDict)
            answer = answer.get(sub_question)
            context.user_data.get(_CURRENT_ANSWER)[sub_question] = answer

        # Format answer
        if answer == BaseOptionMarkup.get_skip() or not answer:
            answer_text = "Skipping the question"
        elif isinstance(answer, str):
            answer_text = answer
        else:
            # Expecting isinstance(answer, Tuple)
            answer_text = " | ".join(answer)

        if preference == SavePrefMarkup.get_ask_again():
            # Based on user preference, ask to use saved answer
            text += "\n\n💡 SAVED ANSWER DETECTED 💡\n" \
                    "I've previously saved the following answer:\n" \
                    "{}\n" \
                    "Would you like to submit this answer?".format(answer_text)
        else:
            # Found close match; recommend answer to user
            text += "\n\n💡 ANSWER RECOMMENDATION 💡\n" \
                    "Based on the question, I recommend:\n" \
                    "{}\n" \
                    "Would you like to accept my recommendation?".format(answer_text)

        # Prompt user for confirmation
        update.callback_query.edit_message_text(utils.text_to_markdownv2(text),
                                                parse_mode=ParseMode.MARKDOWN_V2,
                                                reply_markup=TFMarkup.get_markup())
        return _CONFIRM_SUBMIT

    # Obtain appropriate markup
    markup = None
    if _CURRENT_MARKUP in context.user_data.keys():
        markup = context.user_data.get(_CURRENT_MARKUP)
        if not isinstance(markup, BaseOptionMarkup):
            _logger.error("_obtain_question markup obtained is invalid: %s", markup)
            return _STOPPING
    else:
        if isinstance(question, DatetimeQuestion):
            markup = DatetimeMarkup(question.is_required())
        elif isinstance(question, DateQuestion):
            markup = DateMarkup(question.is_required())
        elif isinstance(question, TimeQuestion):
            markup = TimeMarkup(question.is_required())
        elif isinstance(question, DurationQuestion):
            markup = TimeMarkup(question.is_required(), second=0)
        elif isinstance(question, BaseOptionQuestion):
            markup = MenuMarkup(question.is_required(), isinstance(question, CheckboxQuestion), *question.get_options())
        context.user_data[_CURRENT_MARKUP] = markup
    if markup:
        answer_handler.pattern = re.compile(markup.get_pattern())
        markup = markup.get_markup()

    # Prompt user for selection / input
    text += "\n\nPlease {} your answer.".format("select" if isinstance(question, BaseOptionQuestion) else "input")
    if not question.is_required():
        text += "\nTo skip the question,{} type '/skip'.".format(" select the 'Skip' option or"
                                                                 if isinstance(question, BaseOptionQuestion) else "")
    update.callback_query.edit_message_text(utils.text_to_markdownv2(text),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=markup)
    return _SKIP_OR_ANSWER

    # endregion Display the question metadata


@_reset_garbage_counter
def _submit_answer(update: Update, context: CallbackContext) -> str:
    """Handler for submitting answers.

    After the user confirms the input, the function submits it to the Google Form
    and determines whether the answer should be saved based on user preference and/or input.

    :param update: The update instance to submit the answer.
    :param context: The CallbackContext instance to submit the answer.
    :return: The relevant state for further processing.
    """

    # region Initialisation

    try:
        assert update.callback_query.data is not None
        assert _CURRENT_ANSWER in context.user_data.keys()
        assert isinstance(context.user_data.get(_CURRENT_QUESTION), BaseQuestion)
        assert isinstance(context.user_data.get(_PROCESSOR), FormProcessor)
    except AssertionError as error:
        _logger.error("_submit_answer AssertionError detected while trying to initialise:\n%s", error)
        if update.callback_query.message:
            utils.send_bug_message(update.callback_query.message)
        elif update.message:
            utils.send_bug_message(update.message)
        return _STOPPING
    update.callback_query.answer()
    if _CURRENT_MARKUP in context.user_data.keys():
        _ = context.user_data.pop(_CURRENT_MARKUP)

    # endregion Initialisation

    # region Confirm submission

    result = TFMarkup.confirm(update.callback_query.data)
    if result is None:
        _logger.error("_submit_answer obtained unrecognised callback data: %s", update.callback_query.data)
        return _STOPPING
    elif result:
        if isinstance(context.user_data.get(_CURRENT_ANSWER), OrderedDict) and \
                None in context.user_data.get(_CURRENT_ANSWER).values():
            return _obtain_question(update, context)  # Process next sub-question in _CURRENT_QUESTION
        else:
            _show_loading_screen(update.callback_query)
            if isinstance(context.user_data.get(_CURRENT_ANSWER), OrderedDict):
                result = _submit_to_google_forms(context.user_data.get(_PROCESSOR),
                                                 *context.user_data.get(_CURRENT_ANSWER).values())
            elif isinstance(context.user_data.get(_CURRENT_ANSWER), tuple):
                result = _submit_to_google_forms(context.user_data.get(_PROCESSOR),
                                                 *context.user_data.get(_CURRENT_ANSWER))
            else:
                result = _submit_to_google_forms(context.user_data.get(_PROCESSOR),
                                                 str(context.user_data.get(_CURRENT_ANSWER)))
            if not result:
                _logger.error("_submit_answer failed to submit answer to Google forms, please debug")
                return _STOPPING
    else:
        if isinstance(context.user_data.get(_CURRENT_ANSWER), OrderedDict):
            for key in list(context.user_data.get(_CURRENT_ANSWER).keys())[::-1]:
                if context.user_data.get(_CURRENT_ANSWER).get(key) is not None:
                    # Reset answer back to None
                    context.user_data.get(_CURRENT_ANSWER)[key] = None
                    break
        return _obtain_question(update, context, to_process=False)  # Process current question in _CURRENT_QUESTION

    # endregion Confirm submission

    # region Save answer

    # Determine answer save preference
    question = context.user_data.get(_CURRENT_QUESTION)
    default = {
        _GLOBAL_SAVE_PREF: SavePrefMarkup.get_ask_again(),
        _LOCAL_SAVE_PREF: {
            question.get_pref_key(): {
                _PREF_KEY: context.user_data.get(_SAVE_PREFS, {}).get(
                    _GLOBAL_SAVE_PREF, SavePrefMarkup.get_ask_again())
            }
        }
    }
    if _SAVE_PREFS not in context.user_data.keys():
        context.user_data[_SAVE_PREFS] = default
    elif _LOCAL_SAVE_PREF not in context.user_data.get(_SAVE_PREFS, {}).keys():
        context.user_data.get(_SAVE_PREFS, {})[_LOCAL_SAVE_PREF] = default.get(_LOCAL_SAVE_PREF)
    elif question.get_pref_key() not in context.user_data.get(_SAVE_PREFS, {}).get(_LOCAL_SAVE_PREF, {}).keys():
        context.user_data.get(_SAVE_PREFS, {}).get(_LOCAL_SAVE_PREF, {})[question.get_pref_key()] = \
            default.get(_LOCAL_SAVE_PREF).get(question.get_pref_key())
    question_pref = context.user_data.get(_SAVE_PREFS, {}).get(_LOCAL_SAVE_PREF, {}).get(question.get_pref_key())

    # Save answer according to preference
    if not SavePrefMarkup.is_option(question_pref.get(_PREF_KEY)):
        _logger.error("_submit_answer obtained preference which is not defined: %s", question_pref.get(_PREF_KEY))
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    elif question_pref.get(_PREF_KEY) == SavePrefMarkup.get_save_always():
        # Automatically save answer and continue
        question_pref[_ANSWER_KEY] = context.user_data.get(_CURRENT_ANSWER)
        update.callback_query.edit_message_text(
            utils.text_to_markdownv2("Your answer has been automatically saved!"),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        _remove_current_pointers(context)
        return _obtain_question(update, context)  # Process the next question
    elif question_pref.get(_PREF_KEY) == SavePrefMarkup.get_never_save():
        # No answers to be saved, continue
        update.callback_query.edit_message_text(
            utils.text_to_markdownv2("Your answer has been automatically discarded!"),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        _remove_current_pointers(context)
        return _obtain_question(update, context)  # Process the next question
    else:
        # Prompt for confirmation of saving of answer
        update.callback_query.edit_message_text(
            utils.text_to_markdownv2("💡 SAVE ANSWER PROMPT 💡\n"
                                     "Would you like me to save your answer to this question for future submissions?"),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=TFMarkup.get_markup()
        )
        return _SAVE_ANSWER

    # endregion Save answer


@_reset_garbage_counter
def _save_answer(update: Update, context: CallbackContext) -> str:
    """Confirms whether or not to save user answer.

    :param update: The update instance to confirm saving of answer.
    :param context: The CallbackContext instance to confirm saving of answer.
    :return: The relevant state for further processing.
    """

    # region Initialisation

    local_save_pref = context.user_data.get(_SAVE_PREFS, {}).get(_LOCAL_SAVE_PREF, {})
    try:
        assert update.callback_query.data is not None
        assert _CURRENT_ANSWER in context.user_data.keys()
        question = context.user_data.get(_CURRENT_QUESTION)
        assert isinstance(question, BaseQuestion)
        assert local_save_pref.get(question.get_pref_key(), {}).get(_PREF_KEY) == SavePrefMarkup.get_ask_again()
    except AssertionError as error:
        _logger.error("_save_answer AssertionError detected while trying to initialise:\n%s", error)
        if update.callback_query.message:
            utils.send_bug_message(update.callback_query.message)
        elif update.message:
            utils.send_bug_message(update.message)
        return _STOPPING
    update.callback_query.answer()

    # endregion Initialisation

    result = TFMarkup.confirm(update.callback_query.data)
    if result is None:
        _logger.error("_save_answer obtained unrecognised callback data: %s", update.callback_query.data)
        return _STOPPING
    elif result:
        local_save_pref.get(question.get_pref_key(), {})[_ANSWER_KEY] = context.user_data.get(_CURRENT_ANSWER)
    _remove_current_pointers(context)
    return _obtain_question(update, context)  # Process the next question

# endregion Processing form

# region Terminating functions


@_reset_garbage_counter
def _stop_helper(update: Update, context: CallbackContext, message: str, to_return: Union[int, str]) -> Union[int, str]:
    """Helper function to completely end conversation.

    :param update: The update instance that issued the /stop command.
    :param context: The CallbackContext instance that issued the /stop command.
    :param message: The message to send to the user.
    :param to_return: Either the ConversationHandler.END or _STOPPING state.
    :return: The to_return state to stop the bot.
    """

    # Initialise message
    text = utils.text_to_markdownv2(message)

    # Check if CallbackQueryHandler called
    if update.callback_query:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2)

    # Check if MessageHandler called
    elif update.message:
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=ReplyKeyboardRemove())

    # Error occurred
    else:
        _logger.error("Message class to send message not found: {}".format(update))
        # Can't use utils.send_bug_message since no message instance is found

    # Final preparations
    _clear_cache(context)
    return to_return


def _stop(update: Update, context: CallbackContext) -> int:
    """End conversation on command.

    :param update: The update instance that issued the /stop command.
    :param context: The CallbackContext instance that issued the /stop command.
    :return: The ConversationHandler.END state to stop the bot.
    """

    return _stop_helper(update, context, "🎉 Thank you for using AutoGFormBot! 🎉\n"
                                         "👋 Hope to see you again soon! 👋", ConversationHandler.END)


def _stop_nested(update: Update, context: CallbackContext) -> str:
    """Completely end conversation from within nested conversation.

    :param update: The update instance that issued the /stop command.
    :param context: The CallbackContext instance that issued the /stop command.
    :return: The _STOPPING state to stop the bot.
    """

    return _stop_helper(update, context, "😔 Aww, I'm sorry you had to stop me. 😔\n"
                                         "🎉 Thank you for using AutoGFormBot! 🎉\n"
                                         "👋 Hope to see you again soon! 👋", _STOPPING)


@_reset_garbage_counter
def _reset(update: Update, _: CallbackContext) -> str:
    """Handles bot reset.

    :param update: The update instance to reset.
    :return: The _CONFIRM_RESET state to handle reset confirmation.
    """

    update.callback_query.answer()
    update.callback_query.edit_message_text(utils.text_to_markdownv2("⚠️ IRREVERSIBLE ACTION WARNING ⚠️\n"
                                                                     "Are you sure you want to reset?"),
                                            parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=TFMarkup.get_markup())
    return _CONFIRM_RESET


@_reset_garbage_counter
def _confirm_reset(update: Update, context: CallbackContext) -> Union[int, str]:
    """Handles bot reset confirmation.

    :param update: The update instance to confirm reset.
    :param context: The CallbackContext instance to confirm rest.
    :return: The relevant state, according to whether the reset was confirmed.
    """

    # region Initialisation

    # Sanity check
    try:
        assert update.callback_query.data
    except AssertionError:
        _logger.error("AssertionError in _confirm_reset, please debug")
        if update.message:
            utils.send_bug_message(update.message)
    data = update.callback_query.data
    to_reset = TFMarkup.confirm(data)
    update.callback_query.answer()

    # endregion Initialisation

    # Reset confirmed
    if to_reset is True:
        update.callback_query.edit_message_text(
            utils.text_to_markdownv2("🔁 Resetting the bot now... 🔁"),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        _clear_cache(context)
        return _start(update, context)

    # Cancelling reset, go back to main menu
    elif to_reset is False:
        # Removing of inline keyboard to be done in _main_menu
        return _main_menu(update, context)

    # An error occurred
    else:
        _logger.error("Callback data received in _confirm_reset is not expected: %s", data)
        return ConversationHandler.END

# endregion Terminating functions

# region Handling unrecognised input


def _echo(update: Update, context: CallbackContext) -> None:
    """Handles unrecognised non-command inputs.

    For the fun of it, the bot takes the non-command input and sends a modified message based on the input.
    The bot also reminds users about its main purpose: to automate Google Forms, not as a conversation bot.

    :param update: The update instance sending the non-command inputs.
    :param context: The CallbackContext instance sending the non-command-inputs.
    """

    # Count how many times this has occurred
    if _GARBAGE_INPUT_COUNTER not in context.user_data.keys():
        context.user_data[_GARBAGE_INPUT_COUNTER] = 0
    context.user_data[_GARBAGE_INPUT_COUNTER] = context.user_data.get(_GARBAGE_INPUT_COUNTER) + 1

    # If unintentional, gently prompt user to input somthing recognised
    if context.user_data.get(_GARBAGE_INPUT_COUNTER) <= 2:
        utils.send_potential_feature_message(
            update.message,
            "😰 Sorry, I'm not programmed to understand what {} means. 😰".format(update.message.text)
        )
        return

    # Periodically, send anti-garbage prompt
    elif context.user_data.get(_GARBAGE_INPUT_COUNTER) % _ANTI_GARBAGE_PROMPT_AFTER == 0:
        text = _anti_garbage_replies[random.randint(0, len(_anti_garbage_replies)-1)]

    # Otherwise, just fool around
    else:
        text = _garbage_replies[random.randint(0, len(_garbage_replies)-1)]
        if text.count("{}") == 1:
            text = text.format(update.message.text)
        elif text.count("{}") == 2:
            text = text.format(update.message.text, update.message.from_user.full_name)

    # Send reply
    update.message.reply_text(
        utils.text_to_markdownv2(text),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove()
    )


def _unknown(update: Update, _: CallbackContext) -> None:
    """Handles unrecognised command inputs.

    :param update: The update instance sending the command inputs.
    :param _: The unused CallbackContext instance.
    """

    _logger.info("User %s issued an unknown command %s.", update.message.from_user.first_name, update.message.text)
    utils.send_potential_feature_message(
        update.message,
        "😰 Sorry, I'm not programmed to understand what the {} command means. 😰".format(update.message.text)
    )


def _error_handler(update: Update, context: CallbackContext) -> None:
    """Logs errors encountered by the bot and notifies the developer via Telegram message.

    This script was modified from the Examples repository of the Python Telegram Bot API:
    https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/errorhandlerbot.py

    :param update: The update instance that encountered the error.
    :param context: The CallbackContext instance with the error information.
    """

    _logger.error("Exception while handling an update:", exc_info=context.error)

    # Format traceback and log to developer chat
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = "----------------\n" \
              "DEVELOPER NOTICE\n" \
              "----------------\n" \
              "Exception raise while handling an update:\n\n" \
              "update = {}\n\n" \
              "context.chat_data = {}\n\n" \
              "context.user_data = {}\n\n" \
              "{}".format(update_str, str(context.chat_data), str(context.user_data), tb_string)
    for i in range(0, len(message), 4096):
        context.bot.send_message(
            chat_id=os.environ["DEVELOPER_CHAT_ID"],
            text=utils.text_to_markdownv2(message[i:i + min(4096, len(message) - i)]),
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
            reply_markup=ReplyKeyboardRemove()
        )

    # Send generic bug message to user
    if update.message or update.callback_query.message:
        utils.send_bug_message(update.message if update.message else update.callback_query.message)

# endregion Handling unrecognised input


def main() -> None:
    """Instantiates and runs the Telegram bot.

    This function is the main handler for all the bot commands and user responses.
    """

    # Instantiate bot handlers
    updater = Updater(os.environ["TELEGRAM_TOKEN"])
    dp = updater.dispatcher

    # region Set up second level ConversationHandler (submitting form)

    submit_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(_obtain_question, pattern="^" + _OBTAIN_QUESTION + "$"),
            # TODO add handlers for answers to entry states for job to acccess
            # MessageHandler((Filters.text & ~Filters.command) | Filters.regex("^/skip$"), _process_answer),
            # answer_handler
        ],
        states={
            _OBTAIN_QUESTION: [CallbackQueryHandler(_obtain_question, pattern=TFMarkup.get_pattern())],
            _SKIP_OR_ANSWER: [
                MessageHandler((Filters.text & ~Filters.command) | Filters.regex("^/skip$"), _process_answer),
                answer_handler
            ],
            _ANSWER_OTHER: [MessageHandler(Filters.text & ~Filters.command, _process_other)],
            _CONFIRM_SUBMIT: [CallbackQueryHandler(_submit_answer, pattern=TFMarkup.get_pattern())],
            _SAVE_ANSWER: [CallbackQueryHandler(_save_answer, pattern=TFMarkup.get_pattern())]
        },
        fallbacks=[CommandHandler("stop", _stop_nested)],
        map_to_parent={
            _RETURN: _OBTAINING_LINK,
            _STOPPING: ConversationHandler.END
        },
        allow_reentry=True
    )

    # endregion Set up second level ConversationHandler (submitting form)

    # region Set up second level ConversationHandler (reminder menu)

    remind_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(_remind_menu, pattern="^" + _SET_REMINDER + "$")],
        states={
            _SELECTING_ACTION: [
                CallbackQueryHandler(_select_frequency, pattern="^" + _ADD_JOB + "$"),
                CallbackQueryHandler(_select_reminder, pattern="^" + _REMOVE_JOB + "$"),
                CallbackQueryHandler(_remind_return, pattern="^" + _RETURN_CALLBACK_DATA + "$")
            ],
            _CHOOSE_FREQ: [
                CallbackQueryHandler(_custom_frequency, pattern="^" + FreqMarkup.get_custom() + "$"),
                CallbackQueryHandler(_fixed_frequency, pattern="^(" + "|".join((FreqMarkup.get_hourly(),
                                                                                FreqMarkup.get_daily(),
                                                                                FreqMarkup.get_weekly(),
                                                                                FreqMarkup.get_monthly())) + ")$")
            ],
            _CUSTOM_FREQ: [CallbackQueryHandler(_handle_custom, pattern=FreqCustomMarkup.get_pattern())],
            _SELECT_START: [CallbackQueryHandler(_start_date, pattern=DatetimeMarkup.get_pattern())],
            _CONFIRM_ADD: [CallbackQueryHandler(_confirm_add, pattern=TFMarkup.get_pattern())],
            _SELECT_JOB: [remind_handler],
            _CONFIRM_REMOVE: [CallbackQueryHandler(_perform_removal, pattern=TFMarkup.get_pattern())],
            _CANCEL: [CallbackQueryHandler(_remind_menu, pattern="^" + _SET_REMINDER + "$")]
        },
        fallbacks=[CommandHandler("stop", _stop_nested)],
        map_to_parent={
            _RETURN: _SELECTING_ACTION,
            _STOPPING: ConversationHandler.END
        },
        allow_reentry=True
    )

    # endregion Set up second level ConversationHandler (reminder menu)

    # region Set up second level ConversationHandler (preference menu)

    pref_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(_pref_menu, pattern="^" + _SET_PREFERENCE + "$")],
        states={
            _SELECTING_ACTION: [
                CallbackQueryHandler(_select_global_pref, pattern="^" + _EDIT_PREF_GLOBAL + "$"),
                CallbackQueryHandler(_select_local_pref, pattern="^" + _EDIT_PREF_LOCAL + "$"),
                CallbackQueryHandler(_pref_return, pattern="^" + _RETURN_CALLBACK_DATA + "$")
            ],
            _SELECT_QUESTION: [CallbackQueryHandler(_question_pref, pattern="^[0-9]+$")],
            _CONFIRM_PREF_GLOBAL: [CallbackQueryHandler(_confirm_global_pref, pattern=SavePrefMarkup.get_pattern())],
            _CONFIRM_PREF_LOCAL: [CallbackQueryHandler(_confirm_local_pref, pattern=SavePrefMarkup.get_pattern())],
            _CANCEL: [CallbackQueryHandler(_pref_menu, pattern="^" + _SET_PREFERENCE + "$")]
        },
        fallbacks=[CommandHandler("stop", _stop_nested)],
        map_to_parent={
            _RETURN: _SELECTING_ACTION,
            _STOPPING: ConversationHandler.END
        },
        allow_reentry=True
    )

    # endregion Set up second level ConversationHandler (preference menu)

    # region Put together main menu

    selection_handlers = [
        submit_conv_handler,
        remind_conv_handler,
        pref_conv_handler,
        CallbackQueryHandler(_stop, pattern="^" + _STOPPING + "$"),
        CallbackQueryHandler(_reset, pattern="^" + _RESET + "$")
    ]

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", _start),
            CallbackQueryHandler(_main_menu, pattern="^" + _RETURN_CALLBACK_DATA + "$")
        ],
        states={
            _OBTAINING_LINK: [
                MessageHandler(Filters.entity(MessageEntity.TEXT_LINK) | Filters.entity(MessageEntity.URL), _main_menu)
            ],
            _SELECTING_ACTION: selection_handlers,
            _CONFIRM_RESET: [CallbackQueryHandler(_confirm_reset, pattern=TFMarkup.get_pattern())],
            _STOPPING: [CommandHandler("start", _start)]  # If nested /stop issued, user has to /start again
        },
        fallbacks=[CommandHandler("stop", _stop)],
        allow_reentry=True
    )
    dp.add_handler(conv_handler)

    # endregion Put together main menu

    # Log all errors
    dp.add_error_handler(_error_handler)

    # Add unrecognised input handlers
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, _echo))
    dp.add_handler(MessageHandler(Filters.command, _unknown))  # NOTE: handler MUST be added LAST

    # Start the Bot
    _logger.info("The bot has been successfully deployed!")
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT.
    # This should be used most of the time, since start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    main()
