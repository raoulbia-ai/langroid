"""
Callbacks for Chainlit integration.
"""

import json
import logging
import textwrap
from typing import Any, Callable, Dict, List, Literal, Optional, no_type_check

try:
    import chainlit as cl
except ImportError:
    raise ImportError(
        """
        You are attempting to use `chainlit`, which is not installed 
        by default with `langroid`.
        Please install langroid with the `chainlit` extra using:
        `pip install langroid[chainlit]` or 
        `poetry install -E chainlit`
        depending on your scenario
        """
    )

from chainlit import run_sync
from chainlit.config import config
from chainlit.logger import logger

import langroid as lr
import langroid.language_models as lm
from langroid.utils.configuration import settings
from langroid.utils.constants import NO_ANSWER

# Attempt to reconfigure the root logger to your desired settings
log_level = logging.INFO if settings.debug else logging.INFO
logger.setLevel(log_level)

USER_TIMEOUT = 60_000


@no_type_check
async def ask_helper(func, **kwargs):
    res = await func(**kwargs).send()
    while not res:
        res = await func(**kwargs).send()
    return res


@no_type_check
async def setup_llm() -> None:
    llm_settings = cl.user_session.get("llm_settings", {})
    model = llm_settings.get("chat_model")
    context_length = llm_settings.get("context_length", 16_000)
    temperature = llm_settings.get("temperature", 0.2)
    timeout = llm_settings.get("timeout", 90)
    print(f"Using model: {model}")
    llm_config = lm.OpenAIGPTConfig(
        chat_model=model or lm.OpenAIChatModel.GPT4_TURBO,
        # or, other possibilities for example:
        # "litellm/ollama_chat/mistral"
        # "litellm/ollama_chat/mistral:7b-instruct-v0.2-q8_0"
        # "litellm/ollama/llama2"
        # "local/localhost:8000/v1"
        # "local/localhost:8000"
        chat_context_length=context_length,  # adjust based on model
        temperature=temperature,
        timeout=timeout,
    )
    llm = lm.OpenAIGPT(llm_config)
    cl.user_session.set("llm_config", llm_config)
    cl.user_session.set("llm", llm)


@no_type_check
async def update_agent(settings: Dict[str, Any], agent="agent") -> None:
    cl.user_session.set("llm_settings", settings)
    await inform_llm_settings()
    await setup_llm()
    agent = cl.user_session.get(agent)
    if agent is None:
        raise ValueError(f"Agent {agent} not found in user session")
    agent.llm = cl.user_session.get("llm")
    agent.config.llm = cl.user_session.get("llm_config")


async def make_llm_settings_widgets() -> None:
    await cl.ChatSettings(
        [
            cl.input_widget.TextInput(
                id="chat_model",
                label="Model Name (Default GPT4-Turbo)",
                initial="",
                placeholder="E.g. litellm/ollama_chat/mistral or "
                "local/localhost:8000/v1",
            ),
            cl.input_widget.NumberInput(
                id="context_length",
                label="Chat Context Length",
                initial=16_000,
                placeholder="E.g. 16000",
            ),
            cl.input_widget.Slider(
                id="temperature",
                label="LLM temperature",
                min=0.0,
                max=1.0,
                step=0.1,
                initial=0.2,
                tooltip="Adjust based on model",
            ),
            cl.input_widget.Slider(
                id="timeout",
                label="Timeout (seconds)",
                min=10,
                max=200,
                step=10,
                initial=90,
                tooltip="Timeout for LLM response, in seconds.",
            ),
        ]
    ).send()  # type: ignore


@no_type_check
async def inform_llm_settings() -> None:
    llm_settings: Dict[str, Any] = cl.user_session.get("llm_settings", {})
    settings_dict = dict(
        model=llm_settings.get("chat_model"),
        context_length=llm_settings.get("context_length"),
        temperature=llm_settings.get("temperature"),
        timeout=llm_settings.get("timeout"),
    )
    await cl.Message(
        author="System",
        content="LLM settings updated",
        elements=[
            cl.Text(
                name="settings",
                display="side",
                content=json.dumps(settings_dict, indent=4),
                language="json",
            )
        ],
    ).send()


async def add_instructions(
    title: str = "Instructions",
    content: str = "Enter your question/response in the dialog box below.",
    display: Literal["side", "inline", "page"] = "inline",
) -> None:
    await cl.Message(
        author="",
        content=title if display == "side" else "",
        elements=[
            cl.Text(
                name=title,
                content=content,
                display=display,
            )
        ],
    ).send()


async def ask_user_step(
    name: str,
    prompt: str,
    parent_id: str | None = None,
    timeout: int = USER_TIMEOUT,
    suppress_values: List[str] = ["c"],
) -> str:
    """
    Ask user for input, as a step nested under parent_id.
    Rather than rely entirely on AskUserMessage (which doesn't let us
    nest the question + answer under a step), we instead create fake
    steps for the question and answer, and only rely on AskUserMessage
    with an empty prompt to await user response.

    Args:
        name (str): Name of the agent
        prompt (str): Prompt to display to user
        parent_id (str): Id of the parent step under which this step should be nested
            (If None, the step will be shown at root level)
        timeout (int): Timeout in seconds
        suppress_values (List[str]): List of values to suppress from display
            (e.g. "c" for continue)

    Returns:
        str: User response
    """

    # save hide_cot status to restore later
    # (We should probably use a ctx mgr for this)
    hide_cot = config.ui.hide_cot

    # force hide_cot to False so that the user question + response is visible
    config.ui.hide_cot = False

    if prompt != "":
        # Create a question step to ask user
        question_step = cl.Step(
            name=f"{name} (AskUser ❓)",
            type="run",
            parent_id=parent_id,
        )
        question_step.output = prompt
        await question_step.send()  # type: ignore

    # Use AskUserMessage to await user response,
    # but with an empty prompt so the question is not visible,
    # but still pauses for user input in the input box.
    res = await cl.AskUserMessage(
        content="",
        timeout=timeout,
    ).send()

    if res is None:
        run_sync(
            cl.Message(
                content=f"Timed out after {USER_TIMEOUT} seconds. Exiting."
            ).send()
        )
        return "x"

    # The above will try to display user response in res
    # but we create fake step with same id as res and
    # erase it using empty output so it's not displayed
    step = cl.Step(
        id=res["id"], name="TempUserResponse", type="run", parent_id=parent_id
    )
    step.output = ""
    await step.update()  # type: ignore

    # Finally, reproduce the user response at right nesting level
    if res["output"] in suppress_values:
        config.ui.hide_cot = hide_cot  # restore original value
        return ""

    step = cl.Step(
        name=f"{name}(You 😃)",
        type="run",
        parent_id=parent_id,
    )
    step.output = res["output"]
    await step.send()  # type: ignore
    config.ui.hide_cot = hide_cot  # restore original value
    return res["output"]


def wrap_text_preserving_structure(text: str, width: int = 90) -> str:
    """Wrap text preserving paragraph breaks. Typically used to
    format an agent_response output, which may have long lines
    with no newlines or paragraph breaks."""

    paragraphs = text.split("\n\n")  # Split the text into paragraphs
    wrapped_text = []

    for para in paragraphs:
        if para.strip():  # If the paragraph is not just whitespace
            # Wrap this paragraph and add it to the result
            wrapped_paragraph = textwrap.fill(para, width=width)
            wrapped_text.append(wrapped_paragraph)
        else:
            # Preserve paragraph breaks
            wrapped_text.append("")

    return "\n\n".join(wrapped_text)


class ChainlitAgentCallbacks:
    """Inject Chainlit callbacks into a Langroid Agent"""

    last_step: Optional[cl.Step] = None  # used to display sub-steps under this
    stream: Optional[cl.Step] = None  # pushed into openai_gpt.py to stream tokens
    parent_agent: Optional[lr.Agent] = None  # used to get parent id, for step nesting

    def __init__(self, agent: lr.Agent):
        agent.callbacks.start_llm_stream = self.start_llm_stream
        agent.callbacks.cancel_llm_stream = self.cancel_llm_stream
        agent.callbacks.finish_llm_stream = self.finish_llm_stream
        agent.callbacks.show_llm_response = self.show_llm_response
        agent.callbacks.show_agent_response = self.show_agent_response
        agent.callbacks.get_user_response = self.get_user_response
        agent.callbacks.get_last_step = self.get_last_step
        agent.callbacks.set_parent_agent = self.set_parent_agent
        self.agent: lr.Agent = agent
        self.name = agent.config.name

    def _get_parent_id(self) -> str | None:
        """Get step id under which we need to nest the current step:
        This should be the parent Agent's last_step.
        """
        if self.parent_agent is None:
            logger.info(f"No parent agent found for {self.name}")
            return None
        logger.info(
            f"Parent agent found for {self.name} = {self.parent_agent.config.name}"
        )
        last_step = self.parent_agent.callbacks.get_last_step()
        if last_step is None:
            logger.info(f"No last step found for {self.parent_agent.config.name}")
            return None
        logger.info(
            f"Last step found for {self.parent_agent.config.name} = {last_step.id}"
        )
        return last_step.id  # type: ignore

    def set_parent_agent(self, parent: lr.Agent) -> None:
        self.parent_agent = parent

    def get_last_step(self) -> Optional[cl.Step]:
        return self.last_step

    def start_llm_stream(self) -> Callable[[str], None]:
        """Returns a streaming fn that can be passed to the LLM class"""
        logger.info(
            f"""
            Starting LLM stream for {self.agent.config.name} 
            under parent {self._get_parent_id()}
        """
        )
        self.stream = cl.Step(
            name=self.agent.config.name + "(LLM 🧠)",
            type="llm",
            parent_id=self._get_parent_id(),
        )
        self.last_step = self.stream
        run_sync(self.stream.send())  # type: ignore

        def stream_token(t: str) -> None:
            if self.stream is None:
                raise ValueError("Stream not initialized")
            run_sync(self.stream.stream_token(t))

        return stream_token

    def cancel_llm_stream(self) -> None:
        """Called when cached response found."""
        self.last_step = None
        if self.stream is not None:
            run_sync(self.stream.remove())  # type: ignore

    def finish_llm_stream(self, content: str, is_tool: bool = False) -> None:
        """Update the stream, and display entire response in the right language."""
        tool_indicator = " =>  🛠️" if is_tool else ""
        if self.agent.llm is None or self.stream is None:
            raise ValueError("LLM or stream not initialized")
        model = self.agent.llm.config.chat_model
        if content == "":
            run_sync(self.stream.remove())  # type: ignore
        else:
            run_sync(self.stream.update())  # type: ignore
        stream_id = self.stream.id if content else None
        step = cl.Step(
            id=stream_id,
            name=self.agent.config.name + f"(LLM {model} 🧠{tool_indicator})",
            type="llm",
            parent_id=self._get_parent_id(),
            language="json" if is_tool else None,
        )
        step.output = content or NO_ANSWER
        run_sync(step.update())  # type: ignore

    def show_llm_response(self, content: str, is_tool: bool = False) -> None:
        """Show non-streaming LLM response."""
        model = self.agent.llm is not None and self.agent.llm.config.chat_model
        tool_indicator = " =>  🛠️" if is_tool else ""
        step = cl.Step(
            name=self.agent.config.name + f"(LLM {model} 🧠{tool_indicator})",
            type="llm",
            parent_id=self._get_parent_id(),
            language="json" if is_tool else None,
        )
        self.last_step = step
        step.output = content or NO_ANSWER
        run_sync(step.send())  # type: ignore

    def show_agent_response(self, content: str) -> None:
        """Show message from agent (typically tool handler).
        Agent response can be considered as a "step"
        between LLM response and user response
        """
        step = cl.Step(
            name=self.agent.config.name + "(Agent <>)",
            type="tool",
            parent_id=self._get_parent_id(),
            language="text",
        )
        self.last_step = step
        step.output = wrap_text_preserving_structure(content, width=90)
        run_sync(step.send())  # type: ignore

    def _get_user_response_buttons(self, prompt: str) -> str:
        """Not used. Save for future reference"""
        res = run_sync(
            ask_helper(
                cl.AskActionMessage,
                content="Continue, exit or say something?",
                actions=[
                    cl.Action(
                        name="continue",
                        value="continue",
                        label="✅ Continue",
                    ),
                    cl.Action(
                        name="feedback",
                        value="feedback",
                        label="💬 Say something",
                    ),
                    cl.Action(name="exit", value="exit", label="🔚 Exit Conversation"),
                ],
            )
        )
        if res.get("value") == "continue":
            return ""
        if res.get("value") == "exit":
            return "x"
        if res.get("value") == "feedback":
            return self.get_user_response(prompt)
        return ""  # process the "feedback" case here

    def get_user_response(self, prompt: str) -> str:
        """Ask for user response, wait for it, and return it,
        as a cl.Step rather than as a cl.Message so we can nest it
        under the parent step.
        """
        return run_sync(
            ask_user_step(
                name=self.agent.config.name,
                prompt=prompt,
                parent_id=self._get_parent_id(),
                suppress_values=["c"],
            )
        )


class ChainlitTaskCallbacks:
    """
    Inject ChainlitCallbacks into a Langroid Task's agent and
    agents of sub-tasks.
    """

    def __init__(self, task: lr.Task):
        ChainlitTaskCallbacks._inject_callbacks(task)

    @staticmethod
    def _inject_callbacks(task: lr.Task) -> None:
        # recursively apply ChainlitCallbacks to agents of sub-tasks
        ChainlitAgentCallbacks(task.agent)
        for t in task.sub_tasks:
            ChainlitTaskCallbacks._inject_callbacks(t)
