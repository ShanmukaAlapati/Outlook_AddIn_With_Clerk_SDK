"""
Clerk API client for fetching user and organization data.
Uses Clerk Secret Key to authenticate server-side API requests.
"""
import requests
import os
from utils.logging_errors import write_log

def get_clerk_user_data(user_id: str) -> dict:
    """
    Fetch user data from Clerk API using verified user_id.
    
    SECURITY: This is called AFTER token verification, using the
    user_id extracted from the verified JWT token.
    
    Args:
        user_id: Clerk user ID from verified JWT (e.g., user_xxxxx)
        
    Returns:
        dict: User data including email, name, etc.
    """
    try:
        clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
        
        if not clerk_secret_key:
            write_log("get_clerk_user_data: CLERK_SECRET_KEY not set")
            return {}
        
        # Clerk Backend API endpoint
        url = f"https://api.clerk.com/v1/users/{user_id}"
        
        headers = {
            "Authorization": f"Bearer {clerk_secret_key}",
            "Content-Type": "application/json"
        }
        
        write_log(f"get_clerk_user_data: Fetching data for user_id={user_id}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            write_log(f"get_clerk_user_data: API error {response.status_code} - {response.text}")
            return {}
        
        user_data = response.json()
        write_log(f"get_clerk_user_data: Successfully fetched data for {user_id}")
        
        return user_data
        
    except requests.exceptions.Timeout:
        write_log("get_clerk_user_data: Request timeout")
        return {}
    except requests.exceptions.RequestException as e:
        write_log(f"get_clerk_user_data: Request error - {str(e)}")
        return {}
    except Exception as e:
        write_log(f"get_clerk_user_data: Unexpected error - {str(e)}")
        return {}


def get_clerk_organization_data(org_id: str) -> dict:
    """
    Fetch organization data from Clerk API using verified org_id.
    
    SECURITY: Called AFTER token verification, using org_id
    extracted from the verified JWT token.
    
    Args:
        org_id: Clerk organization ID from verified JWT (e.g., org_xxxxx)
        
    Returns:
        dict: Organization data including name
    """
    try:
        clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
        
        if not clerk_secret_key:
            write_log("get_clerk_organization_data: CLERK_SECRET_KEY not set")
            return {}
        
        # Clerk Backend API endpoint
        url = f"https://api.clerk.com/v1/organizations/{org_id}"
        
        headers = {
            "Authorization": f"Bearer {clerk_secret_key}",
            "Content-Type": "application/json"
        }
        
        write_log(f"get_clerk_organization_data: Fetching data for org_id={org_id}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            write_log(f"get_clerk_organization_data: API error {response.status_code} - {response.text}")
            return {}
        
        org_data = response.json()
        write_log(f"get_clerk_organization_data: Successfully fetched data for {org_id}")
        
        return org_data
        
    except requests.exceptions.Timeout:
        write_log("get_clerk_organization_data: Request timeout")
        return {}
    except requests.exceptions.RequestException as e:
        write_log(f"get_clerk_organization_data: Request error - {str(e)}")
        return {}
    except Exception as e:
        write_log(f"get_clerk_organization_data: Unexpected error - {str(e)}")
        return {}
