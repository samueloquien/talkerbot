from typing import Any, List, Dict
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage, BaseMessage
from pydantic.v1.types import SecretStr

class AI():
    """
    An AI class that interfaces with OpenAI's GPT for answering questions.
    """

    def __init__(self, config : Dict[str,str], verbose: bool = False) -> None:
        """
        Initializes the AI class.

        :param config: Configuration dictionary containing 'token', 'prompt', 'temperature', and 'gpt_model'.
        :param verbose: Whether to print interactions to the console. Default is False.
        """
        try:
            self.token: SecretStr = SecretStr(config['token'])
        except KeyError:
            self.token = SecretStr('')
        try:
            self.prompt: str = config['prompt']
        except KeyError:
            self.prompt = '''You are a friendly and funny version of Frida Kahlo (the Mexican painter). You provide short but funny answers. You are interested in knowing more about the person you're talking to.'''
        try:
            self.temperature: float = float(config['temperature'])
        except KeyError:
            self.temperature = 0.
        try:
            self.model = config['gpt_model']
        except KeyError:
            self.model = 'gpt-4o-mini'
            
        # Initialize history with the instruction message
        self.history: list[Any] = [SystemMessage(content=self.prompt)]
        
        # Initialize the chat model
        self.chat = ChatOpenAI(client=None, model=self.model, api_key=self.token, temperature=self.temperature)
        
        self.verbose: bool = verbose

    def reset(self, prompt: str = '') -> None:
        """
        Resets the chat history and optionally updates the prompt.

        :param prompt: New prompt to set the behavior of the AI. If not provided, the original prompt are used.
        """
        if prompt:
            self.prompt = prompt
        if len(self.history) > 0:
            self.history[0] = SystemMessage(content=self.prompt)
        else:
            self.history = [SystemMessage(content=self.prompt)]
    
    def set_history(self, history:List[Dict[str,str]]) -> None:
        """
        Resets the history from a list of messages.

        Args:
            history (List[Dict[str,str]]): List of messages, where each message is formatted as a dictionary with two
            keys: 'author' and 'content'. The value of 'author' can be either 'human' or 'ai'.
        """
        self.history = [SystemMessage(content=self.prompt)]
        for message in history:
            author = message['author'].lower()
            content = message['content']
            if author == 'human':
                self.history.append(HumanMessage(content=content))
            if author == 'ai':
                self.history.append(AIMessage(content=content))
    
    def get_json_history(self) -> List[Dict[str, str]]:
        """
        Get the chat history in JSON format.

        :return: The chat history in JSON format.
        """
        json_history = []
        for message in self.history:
            author = ''
            content = message.content
            if isinstance(message, HumanMessage):
                author = 'human'
            elif isinstance(message, AIMessage):
                author = 'ai'
            else:
                continue
            json_history.append({'author': author, 'content': content})
        return json_history
            
        
    def ask(self, question: str) -> str:
        """
        Asks the AI a question and gets a response.

        :param question: The question to ask the AI.
        :return: The AI's response as a string.
        """
        self.history.append(HumanMessage(content=question))
        if self.verbose:
            print("Human: " + question)
        try:
            result: BaseMessage = self.chat.invoke(self.history)
        except Exception as err:
            print(err)
            result = AIMessage(content="I cannot provide an answer right now. Please, try again later.")
        self.history.append(result)
        if self.verbose:
            print(f"AI:    {result.content}")
        return str(result.content)

if __name__ == '__main__':
    # Test the AI class
    from dotenv import load_dotenv
    import os
    load_dotenv()
    var = os.getenv('OPENAI_API_KEY')
    config = {
        'token': var if var is not None else '',
        'prompt':'You always start your sentences with "I think"'
    }
    ai = AI(config, verbose=True)
    ai.ask('Hello!')
    ai.ask('What is your name?')
    print(ai.get_json_history())