import requests
import json

def login(username: str, password: str, remember_me: bool = False) -> dict:
    """
    Authenticates a user with the API and provides access tokens.
    
    Args:
        username (str): The user's username
        password (str): The user's password
        remember_me (bool, optional): Whether to enable remember me functionality. Defaults to False.
    
    Returns:
        dict: The response from the API containing access tokens
    """
    # API endpoint
    url = "https://verodat.io/api/v3/signin"
    
    # Request headers
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    
    # Request body
    payload = {
        "username": username,
        "password": password,
        "rememberme": str(remember_me).lower()  # Convert boolean to string "true" or "false"
    }
    
    try:
        # Make the POST request
        response = requests.post(url, headers=headers, json=payload)
        
        # Raise an exception for bad status codes
        response.raise_for_status()
        
        # Return the JSON response
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error during authentication: {e}")
        return None

def main():
    # Example usage
    username = "raoul@verodat.com"
    password = ""
    remember_me = "y"
    
    result = login(username, password, remember_me)
    
    if result:
        print("Login successful!")
        print("Response:", json.dumps(result, indent=2))
    else:
        print("Login failed!")

if __name__ == "__main__":
    main()
