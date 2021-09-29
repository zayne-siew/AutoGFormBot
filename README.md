# AutoGFormBot

## Description
What started out as a simple project to submit temperatures to Google Forms via Telegram, has now been generalised to automate the submission of _any_ Google Form. Deployed on Heroku (free).

## Features
- Automation: Your form responses are stored for future submissions.
- Ease-of-use: One-time setup of bot, little to no intervention required afterwards.
- Flexibility: Works for any valid Google Form, no tweaking of code required.
- Customisability: Save answers and set submission times based on your preference.

## How to Use
You can find the AutoGFormBot on the Telegram app at https://t.me/autogformbot.

Due to limitations of deploying onto Heroku for free, the bot may take up to 20 seconds to respond initially. Hence, please be patient with it.

## Making your own copy
The required dependencies for this project can be installed via
```pip install -r requirements.txt```

You will then need to [create a new Telegram bot account](https://core.telegram.org/bots#6-botfather) and [obtain your personal Telegram chat ID](https://www.alphr.com/telegram-find-user-id/). Once done, create a new ```.env``` file and input your bot's token and personal chat ID into the file. Please use the ```.env.example``` file as a template.

To deploy onto Heroku, I found [this article](https://towardsdatascience.com/how-to-deploy-a-telegram-bot-using-heroku-for-free-9436f89575d2) particularly useful. Feel free to experiment with different deployment options as well.

## Miscellaneous
If you would like to contribute, please submit a pull request. Thank you!
