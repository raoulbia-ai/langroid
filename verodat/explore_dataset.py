from dotenv import load_dotenv
import os
from agent_value_proposition import ValuePropAgent, ValuePropAgentConfig
from pprint import pprint

def explore_dataset():
    load_dotenv()
    
    # Initialize agent
    config = ValuePropAgentConfig(
        username=os.environ.get("VERODAT_USERNAME"),
        password=os.environ.get("VERODAT_PASSWORD"),
        workspace_id=161,
        dataset_id=3641
    )
    agent = ValuePropAgent(config)
    
    # Get raw dataset info first for debugging
    raw_info = agent.get_raw_dataset_info()
    print("\n=== Raw API Response ===")
    pprint(raw_info)
    
    # Get structured dataset info
    dataset_info = agent.get_dataset_info()
    print("\n=== Dataset Structure ===")
    print(f"Name: {dataset_info.get('name', 'N/A')}")
    print(f"Description: {dataset_info.get('description', 'N/A')}")
    
    # Extract schema information
    schema = raw_info.get('schema', {})
    columns = schema.get('columns', [])
    print("\n=== Schema Details ===")
    print(f"Schema Version: {schema.get('version', 'N/A')}")
    print("\nColumns:")
    for col in columns:
        col_name = col.get('name', 'N/A')
        col_type = col.get('type', 'N/A')
        print(f"- {col_name} ({col_type})")
    
    # Get and display sample data
    print("\n=== Sample Data ===")
    data = agent.retrieve_data_from_dataset()
    records = data.get('output', [])  # Check 'output' key instead of 'records'
    if records:
        for i, record in enumerate(records[:3], 1):
            print(f"\nRecord {i}:")
            pprint(record)
    else:
        print("No sample records found")

if __name__ == "__main__":
    explore_dataset()