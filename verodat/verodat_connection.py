import requests
from typing import Optional, Dict, Any

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

def get_workspace_datasets(
    workspace_id: int,
    auth_token: str,
    offset: Optional[int] = None,
    max_datasets: Optional[int] = None,
    filter_state: Optional[str] = None,
    scope: Optional[str] = None
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
    if scope:
        params["scope"] = scope
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching workspace datasets: {e}")
        return None

def get_dataset_info(workspace_id: int, dataset_id: int, auth_token: str) -> Optional[Dict]:
    """
    Get information about a specific dataset.
    """
    base_url = "https://verodat.io/api/v3"
    url = f"{base_url}/workspaces/{workspace_id}/datasets/{dataset_id}"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }

    # Remove the 'scope' parameter from params
    params = {
        "include": "version"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        dataset_info = response.json()
        return dataset_info
    except requests.exceptions.RequestException as e:
        print(f"Error fetching dataset info: {e}")
        return None

def retrieve_data_from_dataset(
    workspace_id: int, 
    dataset_id: int, 
    auth_token: str,
    offset: int = 0,
    max_records: int = 50
) -> Optional[Dict]:
    """
    Retrieve data from a specific dataset.
    """
    base_url = "https://verodat.io/api/v3"
    # Change the endpoint to match the working version
    url = f"{base_url}/workspaces/{workspace_id}/datasets/{dataset_id}/dout-data"
    
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    
    # Add pagination parameters
    params = {
        "offset": offset,
        "max": max_records
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            print(f"Dataset with ID {dataset_id} not found in workspace {workspace_id}.")
        else:
            print(f"HTTP error occurred: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving data from dataset: {e}")
        return None