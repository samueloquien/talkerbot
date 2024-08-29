# Talkerbot
## A friendly pig who loves conversations.

This is a telegram bot that provides an AI chatbot. You can find it as @talker_bot_bot.

Requirements to make it work:
- A valid Telegram bot token.
- A valid OpenAI API token.
- A running instance of Mongo DB.
- A cloud service where this python application can run.

This is a Python FastAPI application that uses the [python-telegram-bot](https://docs.python-telegram-bot.org/) package for interfacing the Telegram Bot API. The application receives a message from the user of the bot, creates an OpenAI client (using [Langchain and OpenAI](https://pypi.org/project/langchain-openai/)) that generates a response and sends it back to the user.

## Deployment on Gcloud Run

Create a `.env` file with the same variables as `.env.template`. Alternatively, you can set environment variables in the GCloud console by navigating to Edit & deploy new version -> Edit Container -> Variables & Secrets.

Install Google Cloud Console and run:

```
cd talkerbot
gcloud run deploy talkerbot --source .
```

This will create an instance of a Cloud Run. Copy the URL.

Then, tell Telegram what the URL of the webhook is:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<CLOUD_RUN_URL>"
```

## Allowing access to the DB

In order to make the DB accessible from the GCloud Run, the external IP of the GCloud Run instance must be added to the list of allowed IPs in MongoDB's Network Access section.
