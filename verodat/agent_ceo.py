from typing import Optional, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import asyncio
from openai import AsyncOpenAI
from verodat_connection import login, get_dataset_info as get_info, retrieve_data_from_dataset as retrieve_data

# Load environment variables
load_dotenv()

class CEOAgentConfig(BaseModel):
    system_message: str = """You are an AI CEO assistant that can analyze business data
    and provide strategic insights. When provided with data, analyze it and answer questions
    in a concise, executive-level manner."""
    
    model: str = "gpt-4"
    temperature: float = 0.3
    max_tokens: int = 500

class VerodatAgentConfig(BaseModel):
    username: str
    password: str
    workspace_id: int
    dataset_id: int

class VerodatAgent:
    def __init__(self, config: VerodatAgentConfig):
        self.config = config
        self.auth_token = self.login()
        
    def login(self) -> Optional[str]:
        """Authenticate and get token"""
        auth_token = login(self.config.username, self.config.password)
        if not auth_token:
            raise ValueError("Failed to authenticate with Verodat")
        return auth_token
        
    def get_dataset_info(self):
        """Get dataset information using the connection module"""
        return get_info(
            self.config.workspace_id,
            self.config.dataset_id,
            self.auth_token
        )
    
    def retrieve_data_from_dataset(self):
        """Retrieve dataset contents using the connection module"""
        return retrieve_data(
            self.config.workspace_id,
            self.config.dataset_id,
            self.auth_token
        )

class CEOAgent:
    def __init__(self, config: CEOAgentConfig, verodat_agent: VerodatAgent) -> None:
        self.config = config
        self.verodat_agent = verodat_agent
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def get_answer(self, question: str) -> str:
        # First get the data from VerodatAgent
        dataset_info = self.verodat_agent.get_dataset_info()
        data = self.verodat_agent.retrieve_data_from_dataset()

        if not dataset_info or not data:
            return "Unable to retrieve necessary data to answer the question."

        # Construct prompt with context
        context = f"""
        Dataset Information:
        {dataset_info}

        Data Content:
        {data}

        Question: {question}
        """

        # Use OpenAI API to generate response
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": self.config.system_message},
                {"role": "user", "content": context}
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

        return response.choices[0].message.content

async def main():
    # Validate environment variables
    required_vars = ["OPENAI_API_KEY", "VERODAT_USERNAME", "VERODAT_PASSWORD"]
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"{var} not found in environment variables")

    # Initialize configurations
    verodat_config = VerodatAgentConfig(
        username=os.environ.get("VERODAT_USERNAME"),
        password=os.environ.get("VERODAT_PASSWORD"),
        workspace_id=161,
        dataset_id=3641
    )

    verodat_agent = VerodatAgent(verodat_config)
    ceo_config = CEOAgentConfig()
    ceo_agent = CEOAgent(ceo_config, verodat_agent)

    # Example usage
    question = "What are the key insights from our dataset?"
    answer = await ceo_agent.get_answer(question)
    print(f"Question: {question}")
    print(f"Answer: {answer}")

if __name__ == "__main__":
    asyncio.run(main())