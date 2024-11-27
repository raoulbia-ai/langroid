import os
from typing import Optional, Dict
from verodat_connection import login, get_dataset_info, retrieve_data_from_dataset
from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig

class ValuePropAgentConfig(ChatAgentConfig):
    username: str
    password: str
    remember_me: bool = True
    workspace_id: int
    dataset_id: int

class ValuePropAgent(ChatAgent):
    def __init__(self, config: ValuePropAgentConfig) -> None:
        self.config = config
        self.auth_token = self.login()
        super().__init__(config)

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

if __name__ == "__main__":
    main()