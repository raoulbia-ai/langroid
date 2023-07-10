from langroid.parsing.urls import get_list_from_user
from langroid.utils.logging import setup_colored_logging
from langroid.agent.task import Task
from langroid.agent.special.doc_chat_agent import DocChatAgent, DocChatAgentConfig
from langroid.utils import configuration


import re
import typer


import os
from rich import print
from rich.prompt import Prompt
import warnings

app = typer.Typer()

setup_colored_logging()


def chat(config: DocChatAgentConfig) -> None:
    configuration.update_global_settings(config, keys=["debug", "stream", "cache"])

    default_paths = config.default_paths
    agent = DocChatAgent(config)
    n_deletes = agent.vecdb.clear_empty_collections()
    collections = agent.vecdb.list_collections()
    collection_name = "NEW"
    is_new_collection = False
    replace_collection = False
    if len(collections) > 1:
        n = len(collections)
        delete_str = f"(deleted {n_deletes} empty collections)" if n_deletes > 0 else ""
        print(f"Found {n} collections: {delete_str}")
        for i, option in enumerate(collections, start=1):
            print(f"{i}. {option}")
        while True:
            choice = Prompt.ask(
                f"Enter a number in the range [1, {n}] to select a collection, "
                "or hit enter to create a NEW collection",
                default="0",
            )
            if choice.isdigit() and 0 <= int(choice) <= n:
                break

        if int(choice) > 0:
            collection_name = collections[int(choice) - 1]
            print(f"Using collection {collection_name}")
            choice = Prompt.ask(
                "Would you like to replace this collection?",
                choices=["y", "n"],
                default="n",
            )
            replace_collection = choice == "y"

    if collection_name == "NEW":
        is_new_collection = True
        collection_name = Prompt.ask(
            "What would you like to name the NEW collection?", default="urlqa-chat"
        )

    agent.vecdb.set_collection(collection_name, replace=replace_collection)

    print("[blue]Welcome to the document chatbot!")
    print("[cyan]Enter x or q to quit, or ? for evidence")
    default_urls_str = " (or leave empty for default URLs)" if is_new_collection else ""
    print("[blue]Enter some URLs or file/dir paths below " f"{default_urls_str}")
    inputs = get_list_from_user()
    if len(inputs) == 0:
        if is_new_collection:
            inputs = default_paths
    agent.config.doc_paths = inputs
    doc_results = agent.ingest()
    n_docs = len(doc_results["urls"]) + len(doc_results["paths"])

    if n_docs > 0:
        n_urls = len(doc_results["urls"])
        n_paths = len(doc_results["paths"])
        n_splits = doc_results["n_splits"]
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        print(
            f"""
        [green]I have processed the following {n_urls} URLs 
        and {n_paths} paths into {n_splits} parts:
        """.strip()
        )
        print("\n".join(doc_results["urls"]))
        print("\n".join(doc_results["paths"]))

    warnings.filterwarnings(
        "ignore",
        message="Token indices sequence length.*",
        # category=UserWarning,
        module="transformers",
    )
    system_msg = Prompt.ask(
        """
    [blue] Tell me who I am; complete this sentence: You are...
    [or hit enter for default] 
    [blue] Human
    """,
        default="a helpful assistant.",
    )
    system_msg = re.sub("you are", "", system_msg, flags=re.IGNORECASE)
    task = Task(
        agent,
        llm_delegate=False,
        single_round=False,
        system_message="You are " + system_msg,
    )
    task.run()


@app.command()
def main(
    debug: bool = typer.Option(False, "--debug", "-d", help="debug mode"),
    nocache: bool = typer.Option(False, "--nocache", "-nc", help="don't use cache"),
) -> None:
    config = DocChatAgentConfig(debug=debug, cache=not nocache)
    chat(config)


if __name__ == "__main__":
    app()