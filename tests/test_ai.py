import pytest
from unittest.mock import MagicMock, patch
from ai import AI
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from dotenv import load_dotenv
import os
load_dotenv()

class TestAI:
    @pytest.fixture
    def ai_instance(self):
        mocked_chat_response = "I don't know"
        with patch.object(ChatOpenAI, '__call__', return_value = AIMessage(content = mocked_chat_response)) as mocked_chat:
            ai = AI({'token':os.getenv('OPENAI_API_KEY')})
            yield ai, mocked_chat, mocked_chat_response
    
    @pytest.fixture
    def openai_fails(self):
        with patch.object(ChatOpenAI, '__call__', side_effect=Exception()) as mocked_chat:
            ai = AI({'token':os.getenv('OPENAI_API_KEY')})
            yield ai, mocked_chat
    
    def test_init(self, ai_instance):
        ai, _ , _ = ai_instance
        expected_instructions = '''You are a friendly and funny version of Frida Kahlo (the Mexican painter). You provide short but funny answers. You are interested in knowing more about the person you're talking to.'''
        assert ai.prompt == expected_instructions
        assert ai.verbose == False
        assert isinstance(ai.chat, ChatOpenAI)
        assert isinstance(ai.history[0], SystemMessage)

    def test_reset(self, ai_instance):
        ai, _ , _ = ai_instance
        new_instructions = 'New instructions'
        ai.reset(new_instructions)
        assert ai.prompt == new_instructions
        assert len(ai.history) == 1  # there should be a single SystemMessage in history
        assert isinstance(ai.history[0], SystemMessage)

    def test_ask(self, ai_instance):
        ai, _ , mocked_response = ai_instance
        question = 'What is the meaning of life?'
        response = ai.ask(question)
        assert response == mocked_response
        assert isinstance(ai.history[-1], AIMessage)  # the latest message in history should be the AI response
    
    def test_several_questions_and_resets(self, ai_instance):
        ai, _, mocked_response = ai_instance
        question = "what's the meaning of life?"
        ai.ask(question)
        ai.ask(question)
        assert len(ai.history) == 5 # instructions + (question, answer) x 2 = 5
        ai.reset()
        ai.ask(question)
        ai.ask(question)
        ai.ask(question)
        assert len(ai.history) == 7 # instructions + (question, answer) x 3 = 7
        assert ai.history[-1].content == mocked_response

    def test_instructions_are_followed(self):
        instructions = "you are a creative assistant, who provides short answers always with words starting with vowels."
        ai = AI({'token':os.getenv('OPENAI_API_KEY'), 'prompt':instructions})
        response = ai.ask('how are you feeling today')
        for word in response.split(' '): # ai must answer with all words starting with vowels
            assert word[0].lower() in 'aeiou'
        instructions = "you are a precise assistant, who always answers with an even number of words."
        ai.reset(instructions)
        response = ai.ask('how are you feeling today') # ai must answer with an even number of words
        assert len(response.split(' ')) % 2 == 0
    
    def test_ask_fails(self, openai_fails):
        ai, mocked_chat = openai_fails
        response = ai.ask('How are you?') # AI provides a valid response if OpenAI fails
        assert response == "I cannot provide an answer right now. Please, try again later."
        assert isinstance(ai.history[-1], AIMessage)