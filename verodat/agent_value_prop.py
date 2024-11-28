import os
from typing import Optional, Dict
from verodat_connection import login, get_dataset_info, retrieve_data_from_dataset, get_dataset_schema
from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig
from pprint import pprint
import aisuite as ai
from pydantic import BaseModel 

# Only showing the changed parts
class ValuePropAgentConfig(BaseModel):
    username: str
    password: str
    remember_me: bool = True
    workspace_id: int
    dataset_id: int
    model: str = "openai:gpt-4"
    temperature: float = 0.3
    max_tokens: int = 500
    system_message: str = """You are a data analysis expert that understands business value propositions.
    Your role is to analyze dataset information and provide insights about business value.
    Communicate with the CEO in a clear, data-driven manner. Focus on adding new insights
    that build upon and extend previous points in the conversation."""

class ValuePropAgent:  # Remove empty parentheses
    def __init__(self, config: ValuePropAgentConfig) -> None:
        # Remove the super().__init__(config) call
        self.config = config
        self.auth_token = self.login()
        self.client = ai.Client()

    def login(self) -> Optional[str]:
        print("Logging in...")
        auth_token = login(self.config.username, self.config.password, self.config.remember_me)
        if not auth_token:
            print("Login failed! Cannot proceed.")
            return None
        print("Login successful!")
        print(f"Auth token: {auth_token[:50]}...")
        return auth_token

    def get_dataset_info(self) -> Optional[Dict]:
        return get_dataset_info(
            self.config.workspace_id,
            self.config.dataset_id,
            self.auth_token
        )

    def retrieve_data_from_dataset(self) -> Optional[Dict]:
        return retrieve_data_from_dataset(
            self.config.workspace_id, 
            self.config.dataset_id, 
            self.auth_token
        )

    def get_dataset_schema(self) -> Optional[Dict]:
        """Get the dataset schema using the connection module."""
        return get_dataset_schema(
            self.config.workspace_id,
            self.config.dataset_id,
            self.auth_token
        )

    async def process_message(self, message: str) -> str:
        """Process incoming messages and generate responses using LLM"""
        dataset_info = self.get_dataset_info()
        data = self.retrieve_data_from_dataset()
        schema = self.get_dataset_schema()

        context = f"""
        Dataset Context:
        Information: {dataset_info}
        Schema: {schema}
        Sample Data: {data}

        Incoming message: {message}
        """

        messages = [
            {"role": "system", "content": self.config.system_message},
            {"role": "user", "content": context}
        ]

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

        return response.choices[0].message.content

def main():
    config = ValuePropAgentConfig(
        username=os.environ.get("VERODAT_USERNAME"),
        password=os.environ.get("VERODAT_PASSWORD"),
        workspace_id=161,
        dataset_id=3641
    )
    agent = ValuePropAgent(config)

    # Retrieve dataset information
    dataset_info = agent.get_dataset_info()
    if dataset_info:
        print("\nDataset Information:")
        print(f"Dataset Name: {dataset_info.get('name', 'N/A')}")
        version_info = dataset_info.get('version', {})
        print(f"Dataset Version: {version_info.get('version', 'N/A')}")
    else:
        print("Failed to retrieve dataset information.")

    # Retrieve and display dataset schema
    dataset_schema = agent.get_dataset_schema()
    if dataset_schema:
        print("\nDataset Schema:")
        pprint(dataset_schema)
    else:
        print("Failed to retrieve dataset schema.")

    # Retrieve and display dataset data
    data = agent.retrieve_data_from_dataset()
    if data:
        print("\nDataset Data:")
        records = data.get('output', [])
        if records:
            for i, record in enumerate(records, 1):
                print(f"\nRecord {i}:")
                pprint(record)
        else:
            print("No records found in dataset.")
    else:
        print("Failed to retrieve dataset data.")

if __name__ == "__main__":
    main()