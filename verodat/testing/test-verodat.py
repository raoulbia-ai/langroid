import os
import socket
import urllib.request
from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector.errors import DatabaseError, ProgrammingError, OperationalError
from contextlib import closing

def clean_account_identifier(account):
    """Clean the account identifier by removing quotes and extra spaces."""
    # Remove quotes, spaces, and any azure region suffix
    cleaned = account.strip().strip('"').strip("'")
    # Remove any azure region suffix if present
    if '.' in cleaned:
        cleaned = cleaned.split('.')[0]
    return cleaned

def load_config():
    """Load and validate Snowflake configuration from environment variables."""
    print("\nLoading configuration...")
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path)
    
    config = {
        "SNOWFLAKE_USER": os.getenv("SNOWFLAKE_USER", "").strip().strip('"'),
        "SNOWFLAKE_PASSWORD": os.getenv("SNOWFLAKE_PASSWORD", "").strip().strip('"'),
        "SNOWFLAKE_ACCOUNT": clean_account_identifier(os.getenv("SNOWFLAKE_ACCOUNT", "")),
        "SNOWFLAKE_WAREHOUSE": os.getenv("SNOWFLAKE_WAREHOUSE", "").strip().strip('"'),
        "SNOWFLAKE_DATABASE": os.getenv("SNOWFLAKE_DATABASE", "").strip().strip('"'),
        "SNOWFLAKE_SCHEMA": os.getenv("SNOWFLAKE_SCHEMA", "").strip().strip('"')
    }
    
    # Validate configuration
    missing_vars = [k for k, v in config.items() if not v]
    if missing_vars:
        raise ValueError(f"Missing or empty required variables: {', '.join(missing_vars)}")
    
    # Print configuration (except password)
    print("Configuration loaded:")
    for key, value in config.items():
        if key != "SNOWFLAKE_PASSWORD":
            print(f"{key}: {value}")
    
    return config

def get_snowflake_connection(config):
    """Create a Snowflake connection with the provided configuration."""
    print("\nInitiating Snowflake connection...")
    
    try:
        print(f"Connecting to account: {config['SNOWFLAKE_ACCOUNT']}")
        print(f"User: {config['SNOWFLAKE_USER']}")
        print(f"Warehouse: {config['SNOWFLAKE_WAREHOUSE']}")
        print(f"Database: {config['SNOWFLAKE_DATABASE']}")
        print(f"Schema: {config['SNOWFLAKE_SCHEMA']}")
        
        conn = snowflake.connector.connect(
            user=config['SNOWFLAKE_USER'],
            password=config['SNOWFLAKE_PASSWORD'],
            account=config['SNOWFLAKE_ACCOUNT'],
            warehouse=config['SNOWFLAKE_WAREHOUSE'],
            database=config['SNOWFLAKE_DATABASE'],
            schema=config['SNOWFLAKE_SCHEMA'],
            region='azure-northeurope',
            login_timeout=15
        )
        print("Connection established successfully")
        return conn
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        raise

def verify_connection(conn):
    """Verify the connection is working with a simple query."""
    try:
        with closing(conn.cursor()) as cursor:
            print("\nTesting connection with simple query...")
            cursor.execute("SELECT CURRENT_VERSION()")
            version = cursor.fetchone()
            print(f"Snowflake version: {version[0]}")
            return True
    except Exception as e:
        print(f"Query failed: {str(e)}")
        return False

def main():
    """Main function with basic connection test."""
    try:
        config = load_config()
        
        # Create .env template if it doesn't exist
        env_template = """
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=YI47469
SNOWFLAKE_WAREHOUSE=G360_VERODAT_MARKETING_161
SNOWFLAKE_DATABASE=G360_VERODAT_130
SNOWFLAKE_SCHEMA=G360_MARKETING_DATA_DESIGN
"""
        if not os.path.exists('.env'):
            print("Creating .env template...")
            with open('.env', 'w') as f:
                f.write(env_template)
            print("Please fill in the .env file with your credentials and run again.")
            return
        
        with closing(get_snowflake_connection(config)) as conn:
            if verify_connection(conn):
                print("Connection test successful!")
            else:
                print("Connection test failed!")
                
    except ValueError as e:
        print("Configuration error:", str(e))
    except DatabaseError as e:
        print("Snowflake database error:", str(e))
    except Exception as e:
        print("Unexpected error:", str(e))
    finally:
        print("\nScript execution completed")

if __name__ == "__main__":
    main()