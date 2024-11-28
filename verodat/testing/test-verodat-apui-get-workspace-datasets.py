import requests
from typing import Optional, Dict, Any, List
import json

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
        print("Login response:", json.dumps(result, indent=2))
        # Changed from result.get('token') to result.get('access_token')
        return result.get('access_token')  # Get the access_token instead of token
    except requests.exceptions.RequestException as e:
        print(f"Error during authentication: {e}")
        return None

def get_workspace_datasets(
    workspace_id: int,
    auth_token: str,
    offset: Optional[int] = None,
    max_datasets: Optional[int] = None,
    filter_state: Optional[str] = None
) -> Dict[Any, Any]:
    """
    Returns a list of datasets for the specified workspace.
    """
    base_url = "https://verodat.io/api/v3"
    url = f"{base_url}/workspaces/{workspace_id}/datasets"
    
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    
    params = {}
    if offset is not None:
        params["offset"] = offset
    if max_datasets is not None:
        params["max"] = max_datasets
    if filter_state:
        params["filter"] = filter_state
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching workspace datasets: {e}")
        return None

def print_dataset_info(datasets: List[Dict]) -> None:
    """
    Helper function to print dataset information.
    """
    if not datasets:
        print("No datasets found")
        return
        
    for dataset in datasets:
        print("\n" + "="*50)
        print(f"Dataset ID: {dataset.get('id')}")
        print(f"Name: {dataset.get('name')}")
        print(f"Version: {dataset.get('version')}")
        print(f"State: {dataset.get('state')}")
        print(f"Created: {dataset.get('created_at')}")
        print(f"Updated: {dataset.get('updated_at')}")

def main():
    # Login credentials
    username = "raoul@verodat.com"
    password = ""
    remember_me = True
    workspace_id = 161
    
    # First, get the auth token
    print("Logging in...")
    auth_token = login(username, password, remember_me)
    
    if not auth_token:
        print("Login failed! Cannot proceed.")
        return
    
    print("Login successful!")
    # print(f"Auth token: {auth_token[:50]}...")  # Print first 50 chars of token for verification
    
    # Get workspace datasets using the token
    print("\nFetching workspace datasets...")
    datasets_result = get_workspace_datasets(
        workspace_id=workspace_id,
        auth_token=auth_token,
        filter_state="design"
    )
    
    if datasets_result:
        print("\nWorkspace datasets:")
        print_dataset_info(datasets_result.get('datasets', []))
    else:
        print("Failed to retrieve datasets")

if __name__ == "__main__":
    main()
