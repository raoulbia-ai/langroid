import os
import asyncio
from dotenv import load_dotenv
import aisuite as ai
from agent_ceo import CEOAgent, CEOAgentConfig
from agent_value_prop import ValuePropAgent, ValuePropAgentConfig
from typing import List, Dict

load_dotenv()

class ConversationMemory:
    def __init__(self, client: ai.Client, max_insights: int = 5):
        self.insights: List[Dict[str, str]] = []
        self.max_insights = max_insights
        self.client = client

    async def add_insight(self, agent: str, content: str):
        insight = await self._extract_key_point(agent, content)
        self.insights.append(insight)
        if len(self.insights) > self.max_insights:
            self.insights = self.insights[-self.max_insights:]

    def get_context(self) -> str:
        if not self.insights:
            return ""
        return "\n".join([
            f"{insight['agent']}: {insight['point']}" 
            for insight in self.insights
        ])

    async def _extract_key_point(self, agent: str, content: str) -> dict:
        response = self.client.chat.completions.create(
            model="openai:gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": (
                    "Extract the single most important point from this text "
                    "in 15-20 words maximum."
                )},
                {"role": "user", "content": content}
            ],
            temperature=0.3,
            max_tokens=30
        )
        return {
            "agent": agent,
            "point": response.choices[0].message.content
        }

class ConversationManager:
    def __init__(self):
        self._check_env_vars()
        self.client = ai.Client()
        self.memory = ConversationMemory(self.client)
        self.value_prop_agent = self._setup_value_prop_agent()
        self.ceo_agent = self._setup_ceo_agent()
    
    def _check_env_vars(self):
        required_vars = ["VERODAT_USERNAME", "VERODAT_PASSWORD"]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    def _setup_value_prop_agent(self):
        config = ValuePropAgentConfig(
            username=os.getenv("VERODAT_USERNAME"),
            password=os.getenv("VERODAT_PASSWORD"),
            workspace_id=161,
            dataset_id=3641,
            model="openai:gpt-4",
            temperature=0.3,
            max_tokens=500
        )
        return ValuePropAgent(config)
    
    def _setup_ceo_agent(self):
        config = CEOAgentConfig(
            model="openai:gpt-4",
            temperature=0.3,
            max_tokens=500
        )
        return CEOAgent(config, self.value_prop_agent)

    async def generate_follow_up(self, ceo_response: str, vp_response: str, context: str) -> str:
        messages = [
            {"role": "system", "content": (
                "Based on the previous exchange, generate a focused follow-up "
                "question that explores a key point from the discussion. "
                "Question should be specific and reference prior insights."
            )},
            {"role": "user", "content": (
                f"Context:\n{context}\n\n"
                f"CEO: {ceo_response}\n"
                f"ValueProp: {vp_response}"
            )}
        ]
        
        response = self.client.chat.completions.create(
            model="openai:gpt-3.5-turbo",
            messages=messages,
            temperature=0.3,
            max_tokens=50
        )
        return response.choices[0].message.content

    async def run_conversation(self):
        seed_question = "What is our most impactful offering?"
        current_question = seed_question
        
        print("\n=== Strategic Analysis ===\n")
        
        for i in range(3):
            print(f"\nRound {i+1}")
            print(f"QUESTION: {current_question}\n")
            
            try:
                # Get condensed context from memory
                context = self.memory.get_context()
                
                # CEO Analysis
                ceo_prompt = (
                    f"Previous insights:\n{context}\n\n"
                    f"Question: {current_question}\n\n"
                    "Provide a concise, focused response that builds on previous insights."
                )
                ceo_response = await self.ceo_agent.get_answer(ceo_prompt)
                print(f"CEO AGENT:")
                print(f"{ceo_response}\n")
                await self.memory.add_insight("CEO", ceo_response)
                
                # ValueProp Analysis
                vp_prompt = (
                    f"Previous insights:\n{context}\n\n"
                    f"CEO just said: {ceo_response}\n\n"
                    "Provide new insights that build on and extend the CEO's analysis."
                )
                vp_response = await self.value_prop_agent.process_message(vp_prompt)
                print(f"VALUE PROP AGENT:")
                print(f"{vp_response}\n")
                await self.memory.add_insight("ValueProp", vp_response)
                
                # Generate next question for first two rounds
                if i < 2:
                    current_question = await self.generate_follow_up(
                        ceo_response, vp_response, context
                    )
                    print(f"NEXT QUESTION:")
                    print(f"{current_question}\n")
                
                print("-" * 50)
                
            except Exception as e:
                print(f"Error in round {i+1}: {str(e)}")
                raise

async def main():
    try:
        conversation = ConversationManager()
        await conversation.run_conversation()
    except Exception as e:
        print(f"Failed to run conversation: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())