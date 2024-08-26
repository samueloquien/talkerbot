from telegram import ForceReply, Update, User
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.ext._contexttypes import ContextTypes
from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Request, Response
import logging
from ai import AI
from db import DB
import os, sys
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
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
WEBHOOK_URL : str = os.getenv('WEBHOOK_URL', default='')
if not WEBHOOK_URL:
    logger.error('Unable to load WEBHOOK_URL from env.')
    sys.exit(1)

# Initialize database connection
db: DB = DB(DB_HOST)

def initialize_ai(user: User, token: str):
    """Initialize AI for a user with given token."""
    initial_instructions = f'You are "Talker", a funny pig, who always has an intelligent response. My name is "{user.first_name}".'
    db.create_openai_config(str(user.id))
    db.update_openai_config(str(user.id), token=token, initial_instructions=initial_instructions)

# Initialize python telegram bot
ptb = (
    Application.builder()
    .updater(None)
    .token(TELEGRAM_BOT_TOKEN)
    .read_timeout(7)
    .get_updates_read_timeout(42)
    .build()
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage the lifespan of the FastAPI app."""
    await ptb.bot.setWebhook(WEBHOOK_URL)  # Set webhook URL
    async with ptb:
        await ptb.start()
        yield
        await ptb.stop()

# Initialize FastAPI app (similar to Flask)
app = FastAPI(lifespan=lifespan)

@app.post("/")
async def process_update(request: Request):
    """Process incoming updates from Telegram."""
    req = await request.json()
    update = Update.de_json(req, ptb.bot)
    await ptb.process_update(update)
    return Response(status_code=HTTPStatus.OK)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    if not update.message or not update.effective_user:
        logger.error("Missing update.message or update.effective_user in start command.")
        return
    response = f"Hi {update.effective_user.first_name}! I'm Talker, your pig friend. Please, enter the /token command, followed by your authentication token."
    await update.message.reply_text(response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    if not update.message:
        logger.error("Missing update.message in help command.")
        return
    response = f"If you want me to respond, please enter the /token command, followed by your OpenAI API token."
    await update.message.reply_text(response)

async def token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create AI for this user if a valid token is provided."""
    if not update.effective_user or not update.message or not update.message.text:
        logger.error("Missing update.effective_user, update.message, or update.message.text in token command.")
        return
    token = update.message.text.split()[-1]
    initialize_ai(update.effective_user, token)
    await update.message.reply_text("Alright, let's chat!")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reinitialize the AI for this user based on the provided instructions."""
    if not update.effective_user or not update.message or not update.message.text:
        logger.error("Missing update.effective_user, update.message, or update.message.text in reset command.")
        return
    user_id = update.effective_user.id
    instructions = ''
    if ' ' in update.message.text:
        instructions = ' '.join(update.message.text.split()[1:])
    if instructions:
        db.update_openai_config(str(user_id), initial_instructions=instructions)
    db.update_conversation_history(str(user_id), [], append=False)
    await update.message.reply_text("Fresh start!")

async def talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide an intelligent response."""
    if not update.message or not update.message.text or not update.effective_user:
        logger.error("Missing update.message, update.message.text, or update.effective_user in talk command.")
        return
    user_id = update.effective_user.id
    config = db.read_openai_config(str(user_id))
    response : str = ''
    if not config or not config['token']:
        response = 'Please, enter a valid token using the /token command.'
    else:
        history = db.read_conversation_history(str(user_id))
        ai = AI(config)
        ai.set_history(history)
        response = ai.ask(update.message.text)
    await update.message.reply_text(response)

# Add command handlers to the bot
ptb.add_handler(CommandHandler("start", start))
ptb.add_handler(CommandHandler("help", help_command))
ptb.add_handler(CommandHandler("token", token_command))
ptb.add_handler(CommandHandler("reset", reset_command))

# Add message handler for non-command messages
ptb.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk))
