"""
A two agent chat system where
- AutoCorrect agent corrects the user's possibly mistyped input,
- Chatter agent responds to the corrected user's input.
"""

import typer
from rich import print

from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig
from langroid.agent.task import Task
from langroid.language_models.openai_gpt import OpenAIChatModel, OpenAIGPTConfig
from langroid.utils.configuration import set_global, Settings
from langroid.utils.logging import setup_colored_logging


app = typer.Typer()

setup_colored_logging()


def chat() -> None:
    print(
        """
        [blue]Welcome to the Autocorrecting Chatbot!
        You can quickly type your message, don't even look at your keyboard. 
        Feel free to type and I will try my best to understand it,
        and I will type out what I think you meant.
        If you agree with my suggestion, just hit enter so I can respond to it.
        If you disagree with my suggestion, say "try again" or say "no" or something 
        similar, and I will try again.
        When I am confused, I will offer some numbered choices to pick from.
        
        Let's go! Enter x or q to quit at any point.
        """
    )

    config = ChatAgentConfig(
        llm=OpenAIGPTConfig(
            chat_model=OpenAIChatModel.GPT4,
        ),
        vecdb=None,
    )
    autocorrect_agent = ChatAgent(config)
    autocorrect_task = Task(
        autocorrect_agent,
        name="AutoCorrect",
        system_message="""
        You are an expert at understanding mistyped text. You are also an expert in 
        the English language, and you have common sense, so you will only use the most 
        sensible version of the text you receive. For any text you receive,
        your job is to write the correct version of it, and not say anything else. 
        If you are unsure, offer up to 3 numbered suggestions, and the user will pick 
        one. Once the user selects a suggestion, simply write out that version.
        Start by asking me to writing something.
        """,
        llm_delegate=True,
        single_round=False,
    )

    chat_agent = ChatAgent(config)
    chat_task = Task(
        chat_agent,
        name="Chat",
        llm_delegate=False,
        single_round=True,
    )
    autocorrect_task.add_sub_task(chat_task)
    autocorrect_task.run()


@app.command()
def main(
    debug: bool = typer.Option(False, "--debug", "-d", help="debug mode"),
    no_stream: bool = typer.Option(False, "--nostream", "-ns", help="no streaming"),
    nocache: bool = typer.Option(False, "--nocache", "-nc", help="don't use cache"),
    cache_type: str = typer.Option(
        "redis", "--cachetype", "-ct", help="redis or momento"
    ),
) -> None:
    set_global(
        Settings(
            debug=debug,
            cache=not nocache,
            stream=not no_stream,
            cache_type=cache_type,
        )
    )
    chat()


if __name__ == "__main__":
    app()