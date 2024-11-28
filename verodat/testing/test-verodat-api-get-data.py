import requests
from typing import Optional, Dict, Any, List
import json
import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 30)

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

def get_dataset_info(workspace_id: int, dataset_id: int, auth_token: str, scope: str = "DESIGN") -> Optional[Dict]:
    """
    Get information about a specific dataset.
    """
    datasets_result = get_workspace_datasets(workspace_id, auth_token)
    if datasets_result and 'datasets' in datasets_result:
        for dataset in datasets_result['datasets']:
            if dataset['id'] == dataset_id and dataset.get('scope') == scope:
                return dataset
    return None

def get_dataset_output(
    workspace_id: int,
    dataset_id: int,
    auth_token: str,
    offset: int = 0,
    max_records: int = 15,
    filter_str: Optional[str] = None
) -> Dict[Any, Any]:
    """
    Fetches output data from a dataset within a workspace.
    """
    base_url = "https://verodat.io/api/v3"
    url = f"{base_url}/workspaces/{workspace_id}/datasets/{dataset_id}/dout-data"
    
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    
    params = {
        "offset": offset,
        "max": max_records
    }
    
    if filter_str:
        params["filter"] = filter_str
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching dataset output: {e}")
        return None

def main():
    # Login credentials
    username = "raoul@verodat.com"
    password = ""
    remember_me = True
    
    # First, get the auth token
    print("Logging in...")
    auth_token = login(username, password, remember_me)
    
    if not auth_token:
        print("Login failed! Cannot proceed.")
        return
    
    print("Login successful!")
    print(f"Auth token: {auth_token[:50]}...")
    
    # Example parameters for dataset output
    workspace_id = 161
    dataset_id = 3641
    
    # First get dataset info
    dataset_info = get_dataset_info(workspace_id, dataset_id, auth_token, scope="DESIGN")
    if dataset_info:
        print("\nDataset Information:")
        print(f"Dataset Name: {dataset_info.get('name', 'N/A')}")
        print(f"Dataset Version: {dataset_info.get('version', 'N/A')}")
    else:
        print(f"Dataset with ID {dataset_id} not found in workspace {workspace_id} with scope 'DESIGN'.")
        print("Could not retrieve dataset information")
    
    # Get dataset output using the token
    print("\nFetching dataset output...")
    output_result = get_dataset_output(
        workspace_id=workspace_id,
        dataset_id=dataset_id,
        auth_token=auth_token,
        max_records=50
    )

    if output_result:
        print("\nDataset output:")          
        ls = []
        for item in output_result['output']:
            ls.append(item)
        df = pd.DataFrame(ls)
        
        print("\nColumns available:")
        print(df.columns.tolist())
        
        print("\nDataFrame (normal view):")
        print(df.T)
    
        # Save to CSV with dataset name in filename if available
        filename = f"dataset_{dataset_info.get('name', dataset_id) if dataset_info else dataset_id}.csv"
        df.to_csv(filename, index=False)
        print(f"\nData saved to {filename}")
    else:
        print("Failed to retrieve dataset output")

if __name__ == "__main__":
    main()
