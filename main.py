from telegram import ForceReply, Update, User
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, Updater
from telegram.ext._contexttypes import ContextTypes
from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Request, Response
from logging_config import *
from ai import AI
from db import DB
import os, sys
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
# Load database connection string
ENV = os.getenv('ENV')
if not ENV:
    ENV = 'dev'
# Load database connection string
DB_HOST = os.getenv('DB_HOST')
if not DB_HOST:
    logger.error('Unable to load DB_HOST from env.')
    sys.exit(1)
# Load Telegram bot token from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    logger.error('Unable to load TELEGRAM_BOT_TOKEN from env.')
    sys.exit(1)
# Load webhook URL for the Telegram bot
WEBHOOK_URL: str = os.getenv('WEBHOOK_URL', default='')
if ENV == 'prod' and not WEBHOOK_URL:
    logger.error('Unable to load WEBHOOK_URL from env.')
    sys.exit(1)

# Initialize database connection
db: DB = DB(DB_HOST)

def get_pig_prompt(user: User) -> str:
    return f'You are "Talker", a funny pig, who always has an intelligent response. My name is "{user.first_name}".'

def get_greeting_message(username: str | None = None) -> str:
    """Return the generic greeting message."""
    if username:
        username = ' ' + username
    msg = f"Hi{username}! I'm Talker, your pig friend. I'm happy to engage in endless " \
          "conversations with you. But please, enter the /token command, followed by " \
          "your OpenAI API token. Otherwise I'm brainless!\nEnter the /help command " \
          "for details and further options."
    return msg

def initialize_ai_config(user: User, token: str):
    """Initialize AI for a user with given token."""
    db.create_openai_config(str(user.id))
    db.update_openai_config(str(user.id), token=token, prompt=get_pig_prompt(user))

# Initialize python telegram bot

ptb: Application
if ENV == 'prod':
    ptb = (
        Application.builder()
        .updater(None)
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(7)
        .get_updates_read_timeout(42)
        .build()
    )
elif ENV == 'dev':
    ptb = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

@asynccontextmanager
async def lifespan_production(_: FastAPI):
    """Manage the lifespan of the FastAPI app."""
    await ptb.bot.setWebhook(WEBHOOK_URL)  # Set webhook URL
    async with ptb:
        await ptb.start()
        yield
        await ptb.stop()

# Initialize FastAPI app (similar to Flask)
app: FastAPI
if ENV == 'dev':
    app = FastAPI()
elif ENV == 'prod':
    app = FastAPI(lifespan=lifespan_production)

@app.post("/")
async def process_update(request: Request):
    """Process incoming updates from Telegram."""
    req = await request.json()
    update = Update.de_json(req, ptb.bot)
    await ptb.process_update(update)
    return Response(status_code=HTTPStatus.OK)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a greetings message when the command /start is issued."""
    if not update.message or not update.effective_user:
        logger.error("Missing update.message or update.effective_user in start command.")
        return
    response = get_greeting_message(update.effective_user.first_name)
    await update.message.reply_text(response, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    if not update.message:
        logger.error("Missing update.message in help command.")
        return
    response = """This is *Talker*, a chatbot that allows you to interact with OpenAI language models.

The following commands allow you to customize your experience:
- /start Shows a greeting message.
- /help Shows this message.
- /token `<OPENAI API KEY>` Sets your OpenAI API token.
- /reset `<instructions>` Provides initial instructions for the bot to know how to behave and format its answers. If no `<instructions>` are provided, the default ones are set (a funny and friendly pig).
- /forget Makes the bot forget the conversation. Only the initial instructions will be maintained. Notice that it's recommended to /forget often for two reasons: having a short context window reduces OpenAI API costs (less context tokens), and forgetting when you switch conversation topic helps the model provide better answers.
- /model `<model_name>` Sets the OpenAI model you want to interact with. Be aware that using more advanced models may have higher costs associated. Check your OpenAI API subscription plan for details.
- /temperature `<temperature>` Sets the temperature parameter of your OpenAI model. This is a way to control randomness of answers. Lower values (0. - 0.3) provide more deterministic answers, while high values ( 0.8 - 2.) may lead to more creative answers. High values may also result in less coherent or relevant answers.
- /deleteme Deletes all your configuration and data from Talker's database, including your OpenAI token and your conversation history.

This bot is provided free of charge. However, for you to interact with OpenAI models you need an OpenAI subscription. By using *Talker* with your OpenAI API key, you are effectively using tokens from your OpenAI subscription plan, and you will be charged by OpenAI accordingly. Please, check your OpenAI account settings for details.

The source code of this bot can be found [here](https://github.com/samueloquien/talkerbot).
"""
                
    await update.message.reply_text(response, parse_mode='Markdown')

async def token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set the OpenAI token for the current user."""
    if not update.effective_user or not update.message or not update.message.text:
        logger.error("Missing update.effective_user, update.message, or update.message.text in token command.")
        return
    try:
        token = update.message.text.split(' ')[1]
        response = "Alright, let's chat!"
    except:
        token = ''
        response = 'Invalid token. Please provide a valid OpenAI API key with the /token command. Type /help for more info.'
    initialize_ai_config(update.effective_user, token)
    await update.message.reply_text(response, parse_mode='Markdown')

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update the AI prompt instructions. If no instructions are provided, the default
    ones (a friendly pig) are set."""
    if not update.effective_user or not update.message or not update.message.text:
        logger.error("Missing update.effective_user, update.message, or update.message.text in reset command.")
        return
    user_id = update.effective_user.id
    reply_text = "Fresh start!"
    instructions = ''
    if ' ' in update.message.text:
        instructions = ' '.join(update.message.text.split()[1:])
    else:
        instructions = get_pig_prompt(update.effective_user)
        reply_text += ' Oink oink!'
    db.update_openai_config(str(user_id), prompt=instructions)
    await update.message.reply_text(reply_text, parse_mode='Markdown')

async def forget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forget conversation history."""
    if not update.effective_user or not update.message or not update.message.text:
        logger.error("Missing update.effective_user, update.message, or update.message.text in reset command.")
        return
    user_id = update.effective_user.id
    db.update_conversation_history(str(user_id), [], append=False)
    await update.message.reply_text("Conversation history deleted.", parse_mode='Markdown')

async def temperature_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update the temperature of the AI model."""
    if not update.effective_user or not update.message or not update.message.text:
        logger.error("Missing update.effective_user, update.message, or update.message.text in reset command.")
        return
    user_id = update.effective_user.id
    new_temperature: float = 0.
    try:
        new_temperature = float(update.message.text.split(' ')[1])
        if new_temperature < 0 or new_temperature > 2:
            raise ValueError(f'Invalid temperature value: {new_temperature}')
        db.update_openai_config(str(user_id), temperature=new_temperature)
        await update.message.reply_text(f"Model temperature updated to {new_temperature}.")
    except:
        await update.message.reply_text(f"Invalid model temperature value {new_temperature}. Provide a value between 0. and 2.")

async def deleteme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete user from the database."""
    if not update.effective_user or not update.message or not update.message.text:
        logger.error("Missing update.effective_user, update.message, or update.message.text in reset command.")
        return
    user_id = update.effective_user.id
    db.delete_conversation_history(str(user_id))
    db.delete_openai_config(str(user_id))
    await update.message.reply_text("All your data has been deleted from Talker's database. Hope to see you back here soon.", parse_mode='Markdown')

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update the model of the AI."""
    if not update.effective_user or not update.message or not update.message.text:
        logger.error("Missing update.effective_user, update.message, or update.message.text in reset command.")
        return
    user_id = update.effective_user.id
    new_model: str = ''
    try:
        new_model = update.message.text.split(' ')[1]
        db.update_openai_config(str(user_id), gpt_model=new_model)
        config = db.read_openai_config(str(user_id))
        ai = AI(config=config)
        ai.ask('Can you understand me?')
        await update.message.reply_text(f"Model updated to {new_model}.")
    except:
        await update.message.reply_text(f"Invalid model value {new_model}. Model not updated. Please, refer to the OpenAI API documentation to check the names of the available models.")

async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide an intelligent response."""
    if not update.message or not update.message.text or not update.effective_user:
        logger.error("Missing update.message, update.message.text, or update.effective_user in talk command.")
        return
    user_id = update.effective_user.id
    config = db.read_openai_config(str(user_id))
    response: str = ''
    if not config or not config['token']:
        response = 'Please, enter a valid token using the /token command. Type /help for more info.'
    else:
        history = db.read_conversation_history(str(user_id))
        num_messages = len(history)
        ai = AI(config)
        history = ai.shorten_history(history)
        if len(history) != num_messages: # history has been shortened. Update DB.
            db.update_conversation_history(str(user_id), history, append=False)
        ai.set_history(history)
        response = ai.ask(update.message.text)
        db.update_conversation_history(str(user_id),[
                {'author':'human', 'content':update.message.text, 'tokens': str(ai.prompt_tokens - ai.total_tokens)},
                {'author':'ai','content':response, 'tokens': str(ai.completion_tokens)}
            ])
    await update.message.reply_text(response, parse_mode='Markdown')

# Add command handlers to the bot
ptb.add_handler(CommandHandler("start", start_command))
ptb.add_handler(CommandHandler("help", help_command))
ptb.add_handler(CommandHandler("token", token_command))
ptb.add_handler(CommandHandler("reset", reset_command))
ptb.add_handler(CommandHandler("forget", forget_command))
ptb.add_handler(CommandHandler("temperature", temperature_command))
ptb.add_handler(CommandHandler("deleteme", deleteme))
ptb.add_handler(CommandHandler("model", model_command))

# Add message handler for non-command messages
ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk))

if ENV == 'dev':
    ptb.run_polling()
