#!/usr/bin/env python3
"""
Behind-the-scenes non-functional utilities.

This script provides a list of utilities used by various other functions.
"""

import logging
import random
from telegram import Message, ParseMode, ReplyKeyboardRemove
from typing import Optional, Tuple, Union


# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
_logger = logging.getLogger(__name__)


def text_to_markdownv2(text: str) -> str:
    """Helper function to convert plaintext into MarkdownV2-friendly plaintext.

    This method is based on the fastest method available in:
    https://stackoverflow.com/questions/3411771/best-way-to-replace-multiple-characters-in-a-string

    :param text: The text to convert.
    :return: The MarkdownV2-friendly plaintext.
    """

    for ch in ('_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'):
        if ch in text:
            text = text.replace(ch, "\\" + ch)
    return text


def generate_random_signatures(n: int, length: Optional[int] = 5) -> Union[str, Tuple[str]]:
    """Helper function to generate random signatures of a fixed length.

    The minimum signature length is 3.
    Since there are so many permutations of signatures,
    assume mathematical impossibility in generating two exact signatures.

    :param n: The number of signatures to generate
    :param length: The length >=3 of the signatures to generature.
    :return If n=1, returns the generated signature.
            Else, returns a tuple of generated signatures.
    """

    chrs = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    # Sanity check
    if n < 1:
        _logger.warning("utils.generate_random_signature minimum n: 1, n=%d", n)
        n = 1
    if length < 3:
        _logger.info("utils.generate_random_signature minimum length: 3, length=%d", length)
        length = 3

    result = tuple("".join(list(map(lambda x: chrs[x], random.sample(range(len(chrs)), length)))) for _ in range(n))
    if n == 1:
        result = result[0]
    return result


def send_bug_message(message: Message, bug: Optional[str] = "") -> None:
    """Helper function to send a message when a bug is caught.

    The function sends a message to notify the user about a bug that occurred.
    Just a pretty way of not crashing the program.

    :param message: The message instance used to send the message.
    :param bug: The text representing the bug that occurred.
    """

    # Prepare message
    text = "🐞 BUG DETECTED IN BOT! 🐞\n" \
           "I can't handle whatever you seem to be doing.\n" \
           "Rest assured, the developer is already working on it.\n\n" \
           "Meanwhile, please refrain from using this function again.\n" \
           "🙏 Please bear with me! 🙏"
    if bug:
        text = bug + "\n\n" + text

    # Send message
    message.reply_text(
        text_to_markdownv2(text),
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
        reply_markup=ReplyKeyboardRemove()
    )


def send_potential_feature_message(message: Message, feature: Optional[str] = ""):
    """Helper function to send a message for potential unimplemented features.

    If the user performs some action that is not a bug but is not implemented,
    notify the user of the ways to potentially get the feature implemented.

    :param message: The message instance used to send the message.
    :param feature: The text representing the feature detected.
    """

    # Prepare message
    text = "💡 POTENTIAL FEATURE IDEA? 💡\n" \
           "If this feature might be useful to you, you can:\n" \
           "\t✋ Raise an issue in the GitHub repo\n" \
           "\t💬 Get in touch with the developer\n"
    if feature:
        text = feature + "\n\n" + text

    # Send message
    message.reply_text(
        text_to_markdownv2(text),
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
        reply_markup=ReplyKeyboardRemove()
    )


if __name__ == '__main__':
    pass
