from typing import Dict, List
from pymongo import MongoClient
from bson import ObjectId

class DB():
    def __init__(self, db_host: str):
        """
        Initialize the database connection and collections.

        :param db_host: The host address of the MongoDB database.
        """
        self.client: MongoClient = MongoClient(host=db_host, tls=True, tlsAllowInvalidCertificates=True)
        self.db = self.client['talkerbot']
        self.openai_config = self.db['openai_config']
        self.conversation_history = self.db['conversation_history']

    '''
    CRUD for openai_config table
    '''
    def create_openai_config(self, telegram_user_id: str) -> None:
        """
        Create an OpenAI configuration for the specified user.

        :param telegram_user_id: The Telegram user ID for which the configuration is being created.
        """
        # Delete any previous configuration for this user
        self.delete_openai_config(telegram_user_id)
        # Set the default configuration
        default_config = {
            'telegram_user_id': telegram_user_id,
            'token': '',
            'gpt_model': 'gpt-4o-mini',
            'temperature': 0,
            'prompt': 'You are a friendly and funny version of Frida Kahlo (the Mexican painter). You provide short but funny answers. You are interested in knowing more about the person you\'re talking to.'
        }
        self.openai_config.insert_one(default_config)

    def read_openai_config(self, telegram_user_id: str) -> Dict[str, str]:
        """
        Read the OpenAI configuration for the specified user.

        :param telegram_user_id: The Telegram user ID to get the configuration for.
        :return: The OpenAI configuration for the user as a dictionary.
        """
        config = self.openai_config.find_one({'telegram_user_id': telegram_user_id})
        if config is not None:
            return config
        else:
            return {}

    def update_openai_config(self, telegram_user_id: str, token: str = '', gpt_model: str = '', temperature: float = 0., prompt: str = '') -> None:
        """
        Update the OpenAI configuration for the specified user.

        :param telegram_user_id: The Telegram user ID to update the configuration for.
        :param token: The API token for OpenAI.
        :param gpt_model: The GPT model to use.
        :param temperature: The temperature (kind of randomness) of the AI model.
        :param prompt: The initial instructions for the AI model.
        """
        config: Dict[str, str] = {}
        if token:
            config['token'] = token
        if gpt_model:
            config['gpt_model'] = gpt_model
        if prompt:
            config['prompt'] = prompt
        if temperature and temperature >= 0. and temperature <= 2.:
            config['temperature'] = f'{temperature}'
        self.openai_config.update_one({'telegram_user_id': telegram_user_id}, {'$set': config})

    def delete_openai_config(self, telegram_user_id: str):
        """
        Delete the OpenAI configuration for the specified user.

        :param telegram_user_id: The Telegram user ID to delete the configuration for.
        """
        self.openai_config.delete_many({'telegram_user_id': telegram_user_id})

    '''
    CRUD for conversation_history table
    '''
    def create_conversation_history(self, telegram_user_id: str) -> None:
        """
        Create an empty conversation history for the specified user.

        :param telegram_user_id: The Telegram user ID to create the conversation history for.
        """
        self.delete_conversation_history(telegram_user_id)
        default_conversation = {
            'telegram_user_id': telegram_user_id,
            'messages': []
        }
        self.conversation_history.insert_one(default_conversation)

    def read_conversation_history(self, telegram_user_id: str) -> List[Dict[str, str]]:
        """
        Read the conversation history for the specified user.

        :param telegram_user_id: The Telegram user ID to get the conversation history for.
        :return: The conversation history for the user as a list of messages.
        """
        history = self.conversation_history.find_one({'telegram_user_id': telegram_user_id})
        if history is not None:
            return history['messages']
        else:
            return []

    def update_conversation_history(self, telegram_user_id: str, messages: List[Dict[str, str]], append: bool = True) -> None:
        """
        Update the conversation history for the specified user.

        :param telegram_user_id: The Telegram user ID to update the conversation history for.
        :param messages: The list of message dictionaries to update the history with.
        :param append: Whether to append messages to the existing history or replace it.
        """
        if append:
            history = self.read_conversation_history(telegram_user_id) + messages
        else:
            history = messages
        self.conversation_history.update_one({'telegram_user_id': telegram_user_id}, {'$set': {'messages': history}}, upsert=True)

    def delete_conversation_history(self, telegram_user_id: str) -> None:
        """
        Delete the conversation history for the specified user.

        :param telegram_user_id: The Telegram user ID to delete the conversation history for.
        """
        self.conversation_history.delete_many({'telegram_user_id': telegram_user_id})

if __name__ == '__main__':
    # Test the DB class
    from dotenv import load_dotenv
    load_dotenv()
    import os, sys
    db_host = os.getenv('DB_HOST')
    if db_host is None:
        print('Error: Unable to read DB_HOST from environment.')
        sys.exit(1)
    db = DB(db_host)
    TELEGRAM_UID = 'asdfasdfadsf'
    db.create_openai_config(TELEGRAM_UID)
    db.update_openai_config(TELEGRAM_UID, gpt_model='gpt5')
    config = db.read_openai_config(TELEGRAM_UID)
    print(config)
    db.create_conversation_history(TELEGRAM_UID)
    db.update_conversation_history(TELEGRAM_UID, [{'Human': 'hello'}, {'ai': 'hi there'}])
    db.update_conversation_history(TELEGRAM_UID, [{'Human': 'how are you'}])
    history = db.read_conversation_history(TELEGRAM_UID)
    assert len(history) == 3
    db.update_conversation_history(TELEGRAM_UID, [{'Human': 'how are you really'}], False)
    print(db.read_conversation_history(TELEGRAM_UID))