import os
from typing import Optional, Dict
from verodat_connection import login, get_dataset_info, retrieve_data_from_dataset
from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig
import asyncio
import openai

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

    def get_raw_dataset_info(self) -> Dict:
        """Get raw dataset info directly from API"""
        return get_dataset_info(
            self.config.workspace_id,
            self.config.dataset_id,
            self.auth_token
        )

    def get_dataset_info(self) -> Dict:
        """Get relevant dataset metadata"""
        raw_info = self.get_raw_dataset_info()
        if not raw_info:
            return {}
            
        schema = raw_info.get('schema', {})
        return {
            "name": raw_info.get("name"),
            "description": raw_info.get("description"),
            "columns": [col.get('name') for col in schema.get('columns', [])],
            "record_count": raw_info.get("stats", {}).get("recordCount", 0)
        }
    
    def retrieve_data_from_dataset(self) -> Dict:
        """Get a representative sample of data"""
        raw_data = retrieve_data_from_dataset(
            self.config.workspace_id,
            self.config.dataset_id,
            self.auth_token,
            offset=0,  # Start from beginning
            max_records=10  # Get small representative sample
        )
        if not raw_data:
            return {}
            
        # Extract data summary
        return {
            "sample_records": raw_data.get("records", [])[:10],
            "column_stats": raw_data.get("stats", {})
        }

    async def generate_custom_schema(self):
        """Generate a custom schema based on dataset content using OpenAI API."""
        data = self.retrieve_data_from_dataset()
        if not data:
            print("No data retrieved from dataset.")
            return None

        # Extract sample records
        sample_records = data.get('sample_records', [])
        if not sample_records:
            print("No sample records available.")
            return None

        # Prepare the prompt
        prompt = (
            "Analyze the following data records and generate a schema that includes "
            "column names and a description of each column's content.\n\n"
            f"Data Records:\n{sample_records}"
        )

        # Use OpenAI's asynchronous API to generate the schema
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        schema = response['choices'][0]['message']['content'].strip()
        print("\nGenerated Schema:")
        print(schema)
        return schema

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

    # Generate custom schema
    asyncio.run(agent.generate_custom_schema())

if __name__ == "__main__":
    main()