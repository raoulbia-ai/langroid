import requests
from typing import Optional, Dict, Any
import json
from dotenv import load_dotenv
import os

def login(username: str, password: str, remember_me: bool = False) -> Optional[str]:
    """
    Authenticates user and returns the access token.
    """
    url = "https://verodat.io/api/v3/signin"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    payload = {
        "username": username,
        "password": password,
        "rememberme": str(remember_me).lower()
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get('access_token')
    except requests.exceptions.RequestException as e:
        print(f"Error during authentication: {e}")
        return None

def get_dataset_schema(
    workspace_id: int,
    dataset_id: int,
    auth_token: str
) -> Dict[Any, Any]:
    """
    Returns the output schema for the specified dataset within the workspace.
    
    Args:
        workspace_id (int): The ID of the workspace
        dataset_id (int): The ID of the dataset
        auth_token (str): Authorization token for API authentication
    
    Returns:
        dict: The schema response from the API
    """
    base_url = "https://verodat.io/api/v3"
    url = f"{base_url}/workspaces/{workspace_id}/datasets/{dataset_id}/dout-schema"
    
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching dataset schema: {e}")
        return None

def main():
    # Load environment variables
    load_dotenv()

    # Validate environment variables
    required_vars = ["VERODAT_USERNAME", "VERODAT_PASSWORD"]
    for var in required_vars:
        if not os.getenv(var):
            print(f"{var} not found in environment variables. Please set it before running the script.")
            return

    # Get credentials from environment variables
    username = os.getenv("VERODAT_USERNAME")
    password = os.getenv("VERODAT_PASSWORD")
    remember_me = True

    # First, get the auth token
    print("Logging in...")
    auth_token = login(username, password, remember_me)
    
    if not auth_token:
        print("Login failed! Cannot proceed.")
        return
    
    print("Login successful!")
    
    # Example parameters for dataset schema
    workspace_id = 161
    dataset_id = 3641
    
    # Get dataset schema using the token
    print("\nFetching dataset schema...")
    schema_result = get_dataset_schema(
        workspace_id=workspace_id,
        dataset_id=dataset_id,
        auth_token=auth_token
    )
    
    if schema_result:
        print("\nDataset schema:")
        print(json.dumps(schema_result, indent=2))
    else:
        print("Failed to retrieve dataset schema")

if __name__ == "__main__":
    main()