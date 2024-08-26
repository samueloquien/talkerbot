import pytest
from db import DB
from dotenv import load_dotenv
load_dotenv()
import os, sys
db_host = os.getenv('DB_HOST')

@pytest.fixture
def db():
    # Set up the database connection for testing
    test_db = DB(db_host=db_host)
    yield test_db
    # Teardown - Close the database connection after testing
    del test_db

def test_openai_config_crud(db):
    # Test Create, Read, Update, and Delete operations for openai_config table
    telegram_user_id = 'test_telegram_user_id'

    # Test create_openai_config
    db.create_openai_config(telegram_user_id)
    config = db.read_openai_config(telegram_user_id)
    assert config['telegram_user_id'] == telegram_user_id

    # Test update_openai_config
    db.update_openai_config(telegram_user_id, gpt_model='gpt6')
    updated_config = db.read_openai_config(telegram_user_id)
    assert updated_config['gpt_model'] == 'gpt6'

    # Test delete_openai_config
    db.delete_openai_config(telegram_user_id)
    deleted_config = db.read_openai_config(telegram_user_id)
    assert deleted_config == {}

def test_conversation_history_crud(db):
    # Test Create, Read, Update, and Delete operations for conversation_history table
    telegram_user_id = 'test_telegram_user_id'

    # Test create_conversation_history
    db.create_conversation_history(telegram_user_id)
    history = db.read_conversation_history(telegram_user_id)
    assert len(history) == 0

    # Test update_conversation_history
    messages = [{'author': 'ai', 'content': 'Hello!'}, {'author': 'human', 'content': 'Hi there!'}]
    db.update_conversation_history(telegram_user_id, messages)
    updated_history = db.read_conversation_history(telegram_user_id)
    assert len(updated_history) == 2

    # Test delete_conversation_history
    db.delete_conversation_history(telegram_user_id)
    deleted_history = db.read_conversation_history(telegram_user_id)
    assert len(deleted_history) == 0