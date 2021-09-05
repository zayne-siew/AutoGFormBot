# AutoGFormBot

## Description
A simple project to submit temperatures to Google Forms via Telegram, generalised to automate the submission of _any_ Google Form.

## Features
- Automation: Your form responses are stored for future submissions.
- Ease-of-use: One-time setup of bot, little to no intervention required afterwards.
- Flexibility: Works for any valid Google Form, no tweaking of code required.
- Customisability: Save answers and set submission times based on your preference.

## How to Use
You can find the AutoGFormBot on the Telegram app at https://t.me/temperature_record_bot.

## Making your own copy
The required dependencies for this project can be installed via
```pip install -r requirements.txt```

You will also need to [create a new Telegram bot account](https://core.telegram.org/bots#6-botfather) and [obtain your personal Telegram chat ID](https://www.alphr.com/telegram-find-user-id/). Once done, create a new ```.env``` file and input your bot's token and personal chat ID into the file. Please use the ```.env.example``` file as a template.

## Miscellaneous
If you would like to contribute, please submit a pull request. Thank you!
