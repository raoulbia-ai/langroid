from typing import Optional, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import asyncio
from agent_value_prop import ValuePropAgent, ValuePropAgentConfig
from pprint import pprint
import json
import aisuite as ai
from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig

# Load environment variables
load_dotenv()

class CEOAgentConfig(BaseModel):
    system_message: str = """You are an AI CEO assistant that can analyze business data
    and provide strategic insights. When provided with data, analyze it and answer questions
    in a concise, executive-level manner. Focus on key strategic points and build upon previous insights."""
    
    model: str = "openai:gpt-4"
    temperature: float = 0.3
    max_tokens: int = 500


class CEOAgent:  # Remove the empty parentheses if not inheriting
    def __init__(self, config: CEOAgentConfig, value_prop_agent: ValuePropAgent) -> None:
        # Remove the super().__init__() call since we're not inheriting
        self.config = config  # Store the config as an instance variable
        self.value_prop_agent = value_prop_agent
        self.client = ai.Client()

    async def respond(self, human_input: str) -> str:
        """Override ChatAgent's respond method"""
        return await self.get_answer(human_input)

    async def get_answer(self, question: str) -> str:
        # Use ValuePropAgent to get dataset info and data
        dataset_info = self.value_prop_agent.get_dataset_info()
        data = self.value_prop_agent.retrieve_data_from_dataset()

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

        # Use aisuite to generate response
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

    async def summarize_columns(self) -> Optional[str]:
        """
        Generate a summary of each column in the dataset, excluding columns that start with 'g360',
        using ChatGPT in a single API call.
        """
        # Get schema and data from ValuePropAgent
        dataset_schema = self.value_prop_agent.get_dataset_schema()
        data = self.value_prop_agent.retrieve_data_from_dataset()

        if not dataset_schema or not data:
            print("Failed to retrieve dataset schema or data.")
            return None

        # Extract column information and sample data
        columns = dataset_schema  # Assuming dataset_schema is a list of columns
        sample_records = data.get('output', [])[:5]  # Take first 5 records as sample

        # Filter out columns that start with 'g360'
        filtered_columns = [
            col for col in columns if not col.get('name', '').startswith('g360')
        ]

        # Prepare schema details for the prompt
        schema_info = []
        for col in filtered_columns:
            col_name = col.get('name', 'Unknown')
            col_type = col.get('type', 'Unknown')
            schema_info.append({"name": col_name, "type": col_type})

        # Prepare the prompt
        prompt = (
            "You are a data analyst tasked with summarizing the following dataset columns.\n"
            "For each column, provide a brief summary of its content based on the data provided.\n"
            "Exclude any columns that are not listed.\n\n"
            f"Dataset Schema:\n{json.dumps(schema_info, indent=2)}\n\n"
            f"Sample Data:\n{json.dumps(sample_records, indent=2)}\n"
        )

        # Use aisuite to generate summaries
        messages = [
            {"role": "system", "content": self.config.system_message},
            {"role": "user", "content": prompt}
        ]

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

        summaries = response.choices[0].message.content.strip()
        return summaries

async def main():
    # Validate environment variables
    required_vars = ["OPENAI_API_KEY", "VERODAT_USERNAME", "VERODAT_PASSWORD"]
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"{var} not found in environment variables")

    # Initialize ValuePropAgent
    value_prop_config = ValuePropAgentConfig(
        username=os.getenv("VERODAT_USERNAME"),
        password=os.getenv("VERODAT_PASSWORD"),
        workspace_id=161,
        dataset_id=3641
    )
    value_prop_agent = ValuePropAgent(value_prop_config)

    ceo_config = CEOAgentConfig()
    ceo_agent = CEOAgent(ceo_config, value_prop_agent)

    # Generate column summaries using aisuite
    summaries = await ceo_agent.summarize_columns()
    if summaries:
        print("\nColumn Summaries:")
        print(summaries)
    else:
        print("Could not generate column summaries.")

    # Example usage
    question = "What are the key insights from our dataset?"
    answer = await ceo_agent.get_answer(question)
    print(f"Question: {question}")
    print(f"Answer: {answer}")

if __name__ == "__main__":
    asyncio.run(main())