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

from collections import OrderedDict
from functools import wraps
import logging
import os
import random
import re
from telegram import InlineKeyboardMarkup, MessageEntity, ParseMode, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater
)
import traceback
from typing import Any, Callable, Optional, Tuple, TypeVar, Union, cast
from src import FormProcessor, utils
from src.markups import (
    BaseMarkup,
    BaseOptionMarkup,
    DateMarkup,
    DatetimeMarkup,
    MenuMarkup,
    SavePrefMarkup,
    TimeMarkup,
    TFMarkup
)
from src.questions import (
    BaseQuestion,
    BaseOptionQuestion,
    BaseOptionGridQuestion,
    CheckboxQuestion,
    DateQuestion,
    DatetimeQuestion,
    DurationQuestion,
    TimeQuestion
)

# region Define constants

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)

# Type-hinting for decorator functions
_F = TypeVar('_F', bound=Callable[..., Any])

# Telegram bot states
(
    # Main menu states
    _OBTAINING_LINK,  # Prompting user for Google Form link
    _SELECTING_ACTION,  # Prompting user for action in main menu
    _SET_PREFERENCE,  # Set preference option in main menu
    _MAIN_MENU,  # Prompting user for action to return to main menu
    _RESET,  # Reset option in main menu
    _CONFIRM_RESET,  # Prompting user to confirm reset

    # Submitting form states
    _OBTAIN_QUESTION,  # Processing of Google Form questions
    _SKIP_OR_ANSWER,  # Processing user input
    _ANSWER_OTHER,  # Processing user alternative selection via the 'Other' option
    _CONFIRM_SUBMIT,  # Confirmation and submission of answers to Google Form
    _SAVE_ANSWER,  # Determine user preference for saving answer

    # Reminder menu states
    _REMIND_MENU,

    # Miscellaneous
    _STOPPING  # Force stop in nested ConversationHandlers
) = utils.generate_random_signatures(13)

# User data constants
(
    # For storing preference-related data
    _GLOBAL_SAVE_PREF,  # For storing of global save preference
    _LOCAL_SAVE_PREF,  # For storing of question save preferences and/or answers
    _PREF_KEY,  # For storing of individual question save preference
    _ANSWER_KEY,  # For storing of individual question answer

    # For Google Form processing
    _PROCESSOR,  # For storing of FormProcessor object
    _CURRENT_QUESTION,  # For storing of processed question to save between Telegram bot states
    _CURRENT_MARKUP,  # For storing of markup that is used to handle user input
    _CURRENT_ANSWER,  # For storing of user-inputted answer(s)

    # Miscellaneous
    _GARBAGE_INPUT_COUNTER  # For handling of unrecognised input
) = utils.generate_random_signatures(9)

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
    "💡 TempRecordBot Notification 💡\n"
    "Sorry to disturb your fun, but I'm not a conversation bot 😰.\n"
    "Can we go back to automating Google Forms, please? 🙏",
    "💡 TempRecordBot Notification 💡\n"
    "Hi, I'd love to talk, but I'm not programmed to! 😔\n"
    "Did you know, my main purpose is actually to help you automate your Google Forms!\n"
    "How about we get started with that, hm? 😍",
    "💡 TempRecordBot Notification 💡\n"
    "I'm feeling so useless... 😭\n"
    "I'm not being used for my intended purpose 😭.\n"
    "Could you... make me useful again? 😳👉👈"
)

# endregion Garbage echoes

# endregion Define constants

# region Helper functions


def _reset_garbage_counter(function: _F) -> _F:
    """Custom decorator to reset the _GARBAGE_INPUT_COUNTER.

    Entry into the parsed function indicates that the user has inputted recognised input.
    Hence, the garbage counter (unrecognised input counter) is reset before proceeding.

    :param function: The function that handles recognised input.
    :return: The decorated function.
    """

    # NOTE: According to type-hinting documentation, inner wrapper functions are small enough
    # such that not type-checking them should not pose too big an issue
    # https://mypy.readthedocs.io/en/stable/generics.html#declaring-decorators
    @wraps(function)
    def _wrapper(*args, **kwargs):
        try:
            # Assert the second argument is the context argument
            assert len(args) >= 2
            assert isinstance(args[1], CallbackContext)

            # Reset the counter
            if _GARBAGE_INPUT_COUNTER in args[1].user_data.keys() and args[1].user_data.get(_GARBAGE_INPUT_COUNTER) > 0:
                args[1].user_data[_GARBAGE_INPUT_COUNTER] = 0

        except AssertionError:
            _logger.error("_reset_garbage_counter could not reset counter")
        finally:
            return function(*args, **kwargs)
    return cast(_F, _wrapper)


def _clear_cache(context: CallbackContext, keep_save_pref: Optional[bool] = False) -> None:
    """Helper function to clear the user data.

    :param context: The context containing the user data to clear.
    :param keep_save_pref: Flag to indicate whether to keep user preference for global answer save.
    """

    # Save preferences
    save_pref = None
    if keep_save_pref and _SET_PREFERENCE in context.user_data.keys():
        save_pref = context.user_data.get(_SET_PREFERENCE)

    # Clear cache and restore
    if _PROCESSOR in context.user_data.keys() and isinstance(context.user_data.get(_PROCESSOR), FormProcessor):
        context.user_data.get(_PROCESSOR).reset()
    context.user_data.clear()
    if save_pref:
        context.user_data[_SET_PREFERENCE] = save_pref


# endregion Helper functions


@_reset_garbage_counter
def _start(update: Update, _: CallbackContext) -> str:
    """Handles the start and reset of the bot.

    Upon either /start command or reset, the bot obtains the link to the Google form for processing.

    :param update: The update instance that started / resetted the bot.
    :return: The _OBTAINING_LINK state for main menu handling.
    """

    # Prepare message
    text = "🎉 Welcome to TempRecordBot! 🎉\n" \
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
        ("⚙️ Set preference", "⏰ Set reminders"),
        ("🔁 Reset", "👋 Exit"),
        "📡 Submit form now",
        option_datas={
            "⚙️ Set preference": _SET_PREFERENCE,
            "⏰ Set reminders": _REMIND_MENU,
            "🔁 Reset": _RESET,
            "👋 Exit": _STOPPING,
            "📡 Submit form now": _OBTAIN_QUESTION
        }
    )
    text = utils.text_to_markdownv2(
        "Welcome to the main menu! Here, you can:\n\n"
        "⚙️ Set save preferences for all questions.\n"
        "⏰ Select when and how often to automatically submit the form.\n"
        "🔁 Reset TempRecordBot with a different Google Form.\n"
        "👋 Stop TempRecordBot completely.\n"
        "📡 Submit the Google Form now.\n\n"
        "Please select an option:"
    )

    # endregion Initialise main menu

    # region Check if CallbackQueryHandler called

    if update.callback_query:

        # Store data from callback data if any
        # TODO remove
        if update.callback_query.data:
            data = update.callback_query.data

            # Expecting data from: _set_preference
            if SavePrefMarkup.is_option(data):
                if _SET_PREFERENCE not in context.user_data.keys():
                    context.user_data[_SET_PREFERENCE] = {}
                context.user_data.get(_SET_PREFERENCE)[_GLOBAL_SAVE_PREF] = data

            # Expecting False value from: _confirm_reset
            elif data == TFMarkup.get_false():
                # Nothing needs to be stored; do nothing
                pass

            # Unexpected callback data
            # Log mainly for debugging purposes
            else:
                _logger.warning("_main_menu recevied unexpected callback data: %s", data)

        # Edit message to main menu
        update.callback_query.answer()
        update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)

    # endregion Check if CallbackQueryHandler called

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
        _logger.error("_main_menu message class to send message not found: {}".format(update))
        return ConversationHandler.END

    return _SELECTING_ACTION


# region Setting preferences

@_reset_garbage_counter
def _set_preference(update: Update, context: CallbackContext) -> str:
    """Handles user preference to save answers.

    :param update: The update instance that is setting the save preference.
    :param context: The CallbackContext instance that is setting the save preference.
    :return: The _OBTAINING_LINK state to go back to the main menu.
    """

    # TODO make new menu for preferences

    # Initialise save preference menu
    text = utils.text_to_markdownv2(
        "❗ Should I save ALL your answers? ❗\n"
        "This will affect ALL questions for this form!"
    )
    if _GLOBAL_SAVE_PREF in context.user_data.get(_SET_PREFERENCE, {}).keys():
        text += utils.text_to_markdownv2(
            "\n\nYour current preference is:\n\t{}\n"
            "❗ Selecting a new preference will OVERRIDE the current one! ❗".format(
                context.user_data.get(_SET_PREFERENCE, {}).get(_GLOBAL_SAVE_PREF))
        )

    # Prompt user for preference
    update.callback_query.answer()
    update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2,
                                            reply_markup=SavePrefMarkup().get_markup())
    return _OBTAINING_LINK

# endregion Setting preferences


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
    elif isinstance(result, str):

        # Check if 'Other' option is selected
        if result == BaseOptionQuestion.get_other_option_label():
            if update.callback_query:
                update.callback_query.edit_message_text(
                    utils.text_to_markdownv2(update.callback_query.message.text),
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            update.message.reply_text(
                utils.text_to_markdownv2("Please specify your alternative option:"),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove()
            )
            return _ANSWER_OTHER

        # Save answer into user data
        if isinstance(context.user_data.get(_CURRENT_ANSWER), OrderedDict):
            keys = list(context.user_data.get(_CURRENT_ANSWER).keys())
            for key in keys:
                if context.user_data.get(_CURRENT_ANSWER).get(key) is None:
                    context.user_data.get(_CURRENT_ANSWER)[key] = result
                    break
        else:
            context.user_data[_CURRENT_ANSWER] = result

        # Prompt for user input
        text = utils.text_to_markdownv2("Are you sure you want to skip this question?"
                                        if result == BaseOptionMarkup.get_skip() or result == "/skip" else
                                        "Please confirm your answer:\n{}".format(result))
        tf_markup = TFMarkup().get_markup()
        if update.message:
            update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=tf_markup)
        else:
            update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=tf_markup)
        return _CONFIRM_SUBMIT
    return _SKIP_OR_ANSWER

    # endregion Determine action according to result


# Dynamic CallbackQueryHandler
dynamic_callback_handler = CallbackQueryHandler(_process_answer)


@_reset_garbage_counter
def _process_other(update: Update, context: CallbackContext) -> str:
    """Handler for processing selection for specified 'Other' option.

    :param update: The update instance to process the 'Other' option selection.
    :param context: The CallbackContext instance to process the 'Other' option selection.
    :return: The relevant state for further processing.
    """

    # Initialisation
    try:
        assert _CURRENT_MARKUP in context.user_data.keys()
    except AssertionError as error:
        _logger.error("_process_other AssertionError detected while trying to initialise:\n%s", error)
        utils.send_bug_message(update.message)
        return _STOPPING

    # TODO context.user_data.get(_CURRENT_MARKUP).update_other_option()
    
    return _SKIP_OR_ANSWER


@_reset_garbage_counter
def _obtain_question(update: Update, context: CallbackContext, start: bool = True) -> str:
    """Handler for obtaining Google Form questions.

    The function obtains the next question to be processed (or remains at the current question instance,
    if the user rejects any answer recommendations) and displays relevant question metadata awaiting user input.

    :param update: The update instance to obtain the Google Form question.
    :param context: The CallbackContext instance to obtain the Google Form question.
    :param start: Flag to indicate if this is the first Google Forms question being processed.
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
    to_process = _CURRENT_QUESTION not in context.user_data.keys()
    # Answer the callback query from _main_menu
    if start:
        update.callback_query.answer()

    # endregion Initialisation

    # region Obtain the next Google Form question

    # Obtain FormProcessor
    processor = context.user_data.get(_PROCESSOR)
    if not isinstance(processor, FormProcessor):
        assert isinstance(processor, str)
        # processor = FormProcessor(processor, headless=True)
        processor = FormProcessor(processor)
        context.user_data[_PROCESSOR] = processor

    # Initialise new question instance based on Google Form question
    if to_process:
        question = processor.get_question(start)
        if question is True:
            # No more questions, exit back to main menu
            update.callback_query.edit_message_text(
                utils.text_to_markdownv2("🥳 The form has submitted successfully! 🥳"),
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return _main_menu(update, context)
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
    if to_process and _SET_PREFERENCE in context.user_data.keys():

        # Check local preference first; it takes precedence over global preference
        if _LOCAL_SAVE_PREF in context.user_data.get(_SET_PREFERENCE, {}).keys():
            prefs = context.user_data.get(_SET_PREFERENCE, {}).get(_LOCAL_SAVE_PREF, {})

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
                            return _obtain_question(update, context, False)  # Process the next question
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
           "{}{}".format(question.get_header(), question.get_description(),
                         "\n\nThis is a required question." if question.is_required() else "")

    # Format sub-question for grid-based questions
    if isinstance(question, BaseOptionGridQuestion):
        if _CURRENT_ANSWER not in context.user_data.keys():
            context.user_data[_CURRENT_ANSWER] = OrderedDict((q, None) for q in question.get_sub_questions())

        # Obtain the next sub-question to process
        sub_question = None
        for key, value in context.user_data.get(_CURRENT_ANSWER, OrderedDict()):
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
        if answer:
            if not isinstance(answer, dict):
                _logger.warning("_obtain_question unexpected saved answer for %s\n"
                                "question=%s, answer=%s", question.__class__.__name__, question, answer)
                _ = context.user_data.get(_SET_PREFERENCE, {}).get(_LOCAL_SAVE_PREF, {}).pop(question.get_pref_key())
                answer = None
            else:
                answer = answer.get(sub_question)

    # Format saved answers
    if to_process and bool(answer):

        # Format answer
        if answer == BaseOptionMarkup.get_skip():
            answer_text = "Skipping the question"
        elif isinstance(answer, str):
            answer_text = answer
        else:
            # Expecting isinstance(answer, Tuple)
            answer_text = " | ".join(answer)

        if preference == SavePrefMarkup.get_ask_again():
            # Based on user preference, ask to use saved answer
            text += "\n\n💡 SAVED ANSWER DETECTED 💡" \
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
                                                reply_markup=TFMarkup().get_markup())
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
        dynamic_callback_handler.pattern = re.compile(markup.get_pattern())
        markup = markup.get_markup()

    # Prompt user for selection / input
    text += "\nPlease {} your answer.".format("select" if isinstance(question, BaseOptionQuestion) else "input")
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
            return _obtain_question(update, context, False)  # Process next sub-question in _CURRENT_QUESTION
        else:
            result = _submit_to_google_forms(context.user_data.get(_PROCESSOR), context.user_data.get(_CURRENT_ANSWER))
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
        return _obtain_question(update, context, False)  # Process current question in _CURRENT_QUESTION

    # endregion Confirm submission

    # region Save answer

    # Determine answer save preference
    question = context.user_data.get(_CURRENT_QUESTION)
    default = {
        _GLOBAL_SAVE_PREF: SavePrefMarkup.get_ask_again(),
        _LOCAL_SAVE_PREF: {
            question.get_pref_key(): {
                _PREF_KEY: context.user_data.get(_SET_PREFERENCE, {}).get(
                    _GLOBAL_SAVE_PREF, SavePrefMarkup.get_ask_again())
            }
        }
    }
    if _SET_PREFERENCE not in context.user_data.keys():
        context.user_data[_SET_PREFERENCE] = default
    elif _LOCAL_SAVE_PREF not in context.user_data.get(_SET_PREFERENCE, {}).keys():
        context.user_data.get(_SET_PREFERENCE, {})[_LOCAL_SAVE_PREF] = default.get(_LOCAL_SAVE_PREF)
    elif question.get_pref_key() not in context.user_data.get(_SET_PREFERENCE, {}).get(_LOCAL_SAVE_PREF, {}).keys():
        context.user_data.get(_SET_PREFERENCE, {}).get(_LOCAL_SAVE_PREF, {})[question.get_pref_key()] = \
            default.get(_LOCAL_SAVE_PREF).get(question.get_pref_key())
    question_pref = context.user_data.get(_SET_PREFERENCE, {}).get(_LOCAL_SAVE_PREF, {}).get(question.get_pref_key())

    # Save answer according to preference
    if not SavePrefMarkup.is_option(question_pref.get(_PREF_KEY)):
        _logger.error("_submit_answer obtained preference which is not defined: %s", question_pref.get(_PREF_KEY))
        utils.send_bug_message(update.callback_query.message)
        return _STOPPING
    elif question_pref.get(_PREF_KEY) == SavePrefMarkup.get_save_always():
        # Automatically save answer and continue
        question_pref[_ANSWER_KEY] = context.user_data.get(_CURRENT_ANSWER)
        _remove_current_pointers(context)
        return _obtain_question(update, context, False)  # Process the next question
    elif question_pref.get(_PREF_KEY) == SavePrefMarkup.get_never_save():
        # No answers to be saved, continue
        _remove_current_pointers(context)
        return _obtain_question(update, context, False)  # Process the next question
    else:
        # Prompt for confirmation of saving of answer
        update.callback_query.edit_message_text(
            utils.text_to_markdownv2("💡 SAVE ANSWER PROMPT 💡\n"
                                     "Would you like me to save your answer to this question for future submissions?"),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=TFMarkup().get_markup()
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

    local_save_pref = context.user_data.get(_SET_PREFERENCE, {}).get(_LOCAL_SAVE_PREF, {})
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
    return _obtain_question(update, context, False)  # Process the next question

# endregion Processing form


# region Terminating functions

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

    return _stop_helper(update, context, "🎉 Thank you for using TempRecordBot! 🎉\n"
                                         "👋 Hope to see you again soon! 👋", ConversationHandler.END)


@_reset_garbage_counter
def _stop_nested(update: Update, context: CallbackContext) -> str:
    """Completely end conversation from within nested conversation.

    :param update: The update instance that issued the /stop command.
    :param context: The CallbackContext instance that issued the /stop command.
    :return: The _STOPPING state to stop the bot.
    """

    return _stop_helper(update, context, "😔 Aww, I'm sorry you had to stop me. 😔\n"
                                         "🎉 Thank you for using TempRecordBot! 🎉\n"
                                         "👋 Hope to see you again soon! 👋", _STOPPING)


@_reset_garbage_counter
def _reset(update: Update, _: CallbackContext) -> str:
    """Handles bot reset.

    :param update: The update instance to reset.
    :return: The _CONFIRM_RESET state to handle reset confirmation.
    """

    update.callback_query.answer()
    update.callback_query.edit_message_text(
        utils.text_to_markdownv2(
            "❗ Are you sure you want to RESET? ❗\n"
            "This action is IRREVERSIBLE!"
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=TFMarkup().get_markup()
    )
    return _CONFIRM_RESET


@_reset_garbage_counter
def _confirm_reset(update: Update, context: CallbackContext) -> Union[int, str]:
    """Handles bot reset confirmation.

    :param update: The update instance to confirm reset.
    :param context: The CallbackContext instance to confirm rest.
    :return: The relevant state, according to whether the reset was confirmed.
    """

    # Sanity check
    try:
        assert update.callback_query.data
    except AssertionError:
        _logger.error("AssertionError in _confirm_reset, please debug")
        if update.message:
            utils.send_bug_message(update.message)

    # Initialise
    data = update.callback_query.data
    to_reset = TFMarkup.confirm(data)
    update.callback_query.answer()

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

# endregion Handling unrecognised input


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


def main() -> None:
    """Instantiates and runs the Telegram bot.

    This function is the main handler for all the bot commands and user responses.
    """

    # Instantiate bot handlers
    updater = Updater(os.environ["TELEGRAM_TOKEN"])
    dp = updater.dispatcher

    # region Set up second level ConversationHandler (submitting form)

    submit_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(_obtain_question, pattern="^" + _OBTAIN_QUESTION + "$")],
        states={
            _OBTAIN_QUESTION: [CallbackQueryHandler(_obtain_question, pattern=TFMarkup.get_pattern())],
            _SKIP_OR_ANSWER: [
                MessageHandler((Filters.text & ~Filters.command) | Filters.regex("^/skip$"), _process_answer),
                dynamic_callback_handler
            ],
            _ANSWER_OTHER: [MessageHandler(Filters.text & ~Filters.command, _process_other)],
            _CONFIRM_SUBMIT: [CallbackQueryHandler(_submit_answer, pattern=TFMarkup.get_pattern())],
            _SAVE_ANSWER: [CallbackQueryHandler(_save_answer, pattern=TFMarkup.get_pattern())]
        },
        fallbacks=[CommandHandler("stop", _stop_nested)],
        map_to_parent={_STOPPING: ConversationHandler.END}
    )

    # endregion Set up second level ConversationHandler (submitting form)

    # region Set up second level ConversationHandler (reminder menu)

    # TODO set up reminder menu
    remind_conv_handler = ConversationHandler(
        entry_points=[
            # CallbackQueryHandler(_remind_menu, pattern="^" + _REMIND_MENU + "$")
        ],
        states={},
        fallbacks=[CommandHandler("stop", _stop_nested)],
        map_to_parent={_STOPPING: ConversationHandler.END}
    )

    # endregion Set up second level ConversationHandler (reminder menu)

    # region Set up second level ConversationHandler (preference menu)

    # TODO set up preference menu
    pref_conv_handler = ConversationHandler(
        entry_points=[
            # CallbackQueryHandler(_set_preference, pattern="^" + _SET_PREFERENCE + "$")
        ],
        states={},
        fallbacks=[CommandHandler("stop", _stop_nested)],
        map_to_parent={_STOPPING: ConversationHandler.END}
    )

    # endregion Set up second level ConversationHandler (preference menu)

    # region Put together main menu

    selection_handlers = [
        submit_conv_handler,
        remind_conv_handler,
        CallbackQueryHandler(_set_preference, pattern="^" + _SET_PREFERENCE + "$"),  # TODO REMOVE
        pref_conv_handler,
        CallbackQueryHandler(_stop, pattern="^" + _STOPPING + "$"),
        CallbackQueryHandler(_reset, pattern="^" + _RESET + "$")
    ]

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", _start)],
        states={
            _OBTAINING_LINK: [
                MessageHandler(Filters.entity(MessageEntity.TEXT_LINK) | Filters.entity(MessageEntity.URL), _main_menu),
                CallbackQueryHandler(_main_menu, pattern=SavePrefMarkup.get_pattern())
            ],
            _SELECTING_ACTION: selection_handlers,
            _CONFIRM_RESET: [CallbackQueryHandler(_confirm_reset, pattern=TFMarkup.get_pattern())],
            _STOPPING: [CommandHandler("start", _start)]  # If nested /stop issued, user has to /start again
        },
        fallbacks=[CommandHandler("stop", _stop)]
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
