"""
JWT token verification using Clerk's JWKS.
Handles token signature verification, claim extraction, and user data enrichment.
"""
import jwt
from jwt import PyJWKClient
from datetime import datetime, timedelta
import os
from utils.logging_errors import write_log
from auth.clerk_api import get_clerk_user_data, get_clerk_organization_data

# Global JWKS cache to avoid fetching on every request
_jwks_cache = {
    "client": None,
    "last_updated": None,
    "ttl_hours": 1  # Refresh JWKS every 1 hour
}


def get_jwks_client():
    """
    Returns a cached PyJWKClient instance for Clerk JWKS.
    Refreshes the cache if TTL has expired.
    
    JWKS (JSON Web Key Set) contains public keys used to verify JWT signatures.
    Caching prevents unnecessary network calls on every token verification.
    
    Returns:
        PyJWKClient: Initialized JWKS client
        
    Raises:
        Exception: If CLERK_FRONTEND_API is not configured
    """
    global _jwks_cache
    
    try:
        write_log("get_jwks_client: Checking JWKS cache")
        
        # Check if cache is still valid
        now = datetime.now()
        if (_jwks_cache["client"] is not None and 
            _jwks_cache["last_updated"] is not None):
            
            time_since_update = now - _jwks_cache["last_updated"]
            if time_since_update < timedelta(hours=_jwks_cache["ttl_hours"]):
                write_log("get_jwks_client: Using cached JWKS client")
                return _jwks_cache["client"]
        
        write_log("get_jwks_client: Cache expired or empty, fetching new JWKS")
        
        # Get Clerk Frontend API from environment
        clerk_frontend_api = os.getenv("CLERK_FRONTEND_API")
        
        if not clerk_frontend_api:
            raise Exception("CLERK_FRONTEND_API environment variable not set")
        
        # Construct JWKS URL
        jwks_url = f"https://{clerk_frontend_api}/.well-known/jwks.json"
        write_log(f"get_jwks_client: JWKS URL={jwks_url}")
        
        # Create PyJWKClient instance
        jwk_client = PyJWKClient(
            jwks_url,
            cache_keys=True,
            max_cached_keys=16,
            cache_jwk_set=True,
            lifespan=3600
        )
        
        # Update cache
        _jwks_cache["client"] = jwk_client
        _jwks_cache["last_updated"] = now
        
        write_log("get_jwks_client: JWKS client created and cached")
        return jwk_client
        
    except Exception as e:
        write_log(f"get_jwks_client: Error - {str(e)}")
        raise


def verify_and_decode_clerk_token(token: str) -> dict:
    """
    SECURE: Verifies JWT token and enriches with Clerk API data.
    
    Security flow:
    1. Verify token signature with Clerk's public key (JWKS)
    2. Validate token claims (expiration, issuer, etc.)
    3. Extract user_id from VERIFIED token
    4. Fetch user data from Clerk API using verified user_id
    5. Fetch org data from Clerk API using verified org_id
    6. Return enriched auth_info based on verified data only
    
    Args:
        token (str): JWT token from Clerk session
        
    Returns:
        dict: auth_info with verified and enriched user data
        
    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token signature is invalid
    """
    try:
        write_log("verify_and_decode_clerk_token: Starting token verification")
        
        # Get JWKS client (cached)
        jwk_client = get_jwks_client()
        
        # Extract key ID from token header
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        write_log(f"verify_and_decode_clerk_token: Token kid={kid}")
        
        # Get signing key from JWKS
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        public_key = signing_key.key
        write_log("verify_and_decode_clerk_token: Public key retrieved from JWKS")
        
        # Get Clerk configuration
        clerk_frontend_api = os.getenv("CLERK_FRONTEND_API")
        issuer = f"https://{clerk_frontend_api}"
        
        # SECURITY: Verify and decode token with full validation
        # Add leeway to handle clock skew between client and server
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=issuer,
            leeway=60,  # Allow 60 seconds clock skew
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": False,
                "require_exp": True,
                "require_iat": True,
            }
        )
        
        write_log(f"verify_and_decode_clerk_token: Token verified, claims={list(decoded.keys())}")
        
        # Extract claims from VERIFIED token
        user_id = decoded.get("sub")
        session_id = decoded.get("sid")
        issued_at = decoded.get("iat")
        expires_at = decoded.get("exp")
        
        # Extract organization from 'o' claim
        org_claim = decoded.get("o", {}) or {}
        org_id = org_claim.get("id")
        org_slug = org_claim.get("slg")
        org_role = org_claim.get("rol")
        
        write_log(f"verify_and_decode_clerk_token: Verified user_id={user_id}, org_id={org_id}, org_role={org_role}")
        
        # SECURITY: Fetch user data from Clerk API using VERIFIED user_id
        write_log(f"verify_and_decode_clerk_token: Fetching user data from Clerk API")
        user_data = get_clerk_user_data(user_id)
        
        # Extract email from API response
        email_addresses = user_data.get("email_addresses", [])
        primary_email_id = user_data.get("primary_email_address_id")
        
        email = None
        all_emails = []
        for email_obj in email_addresses:
            email_addr = email_obj.get("email_address")
            if email_addr:
                all_emails.append(email_addr)
                if email_obj.get("id") == primary_email_id:
                    email = email_addr
        
        if not email and all_emails:
            email = all_emails[0]
        
        # Extract name from API response
        first_name = user_data.get("first_name")
        last_name = user_data.get("last_name")
        full_name = None
        if first_name or last_name:
            full_name = f"{first_name or ''} {last_name or ''}".strip()
        
        username = user_data.get("username")
        
        # Fetch organization name from Clerk API if org exists
        org_name = None
        if org_id:
            write_log(f"verify_and_decode_clerk_token: Fetching org data from Clerk API")
            org_data = get_clerk_organization_data(org_id)
            org_name = org_data.get("name")
        
        # Convert timestamps to ISO format
        def timestamp_to_iso(ts):
            if ts:
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            return None
        
        # ===== SUPER ADMIN DETECTION =====
        # Check if user email matches the super admin email from environment
        # If it matches, override the org_role to 'super-admin' for proper routing
        super_admin_email = os.getenv("SUPER_ADMIN_EMAIL")
        final_org_role = None
        
        if super_admin_email and email and email.lower() == super_admin_email.lower():
            # This user is the super admin - override role
            final_org_role = "super-admin"
            write_log(f"verify_and_decode_clerk_token: Super admin detected - email={email}")
        else:
            # Regular user - use org role from Clerk token
            # OLD CODE: org_role was directly prefixed with "org:"
            # NEW CODE: Check for super admin first, then apply org prefix
            final_org_role = f"org:{org_role}" if org_role else None
            write_log(f"verify_and_decode_clerk_token: Regular user - role={final_org_role}")
        
        # Build auth_info with verified and enriched data
        auth_info = {
            "user_id": user_id,
            "sub": user_id,  # Alias for standard claim name
            "email": email,
            "full_name": full_name,
            "username": username,
            "all_emails": all_emails,
            "org_id": org_id,
            "org_slug": org_slug,
            "org_name": org_name,
            # "org_role": f"org:{org_role}" if org_role else None,
            "org_role": final_org_role,  # Use the final_org_role (either 'super-admin' or 'org:role')
            "session_id": session_id,
            "session_status": "active",
            "session_last_active_at": timestamp_to_iso(issued_at),
            "session_expire_at": timestamp_to_iso(expires_at),
            "session_created_at": timestamp_to_iso(issued_at),
            "session_updated_at": timestamp_to_iso(issued_at),
            "raw_token": token,
        }
        
        write_log(f"verify_and_decode_clerk_token: Complete - user={email}, role={auth_info['org_role']}")
        return auth_info
        
    except jwt.ExpiredSignatureError as e:
        write_log(f"verify_and_decode_clerk_token: Token expired - {str(e)}")
        raise
    except jwt.InvalidTokenError as e:
        write_log(f"verify_and_decode_clerk_token: Invalid token - {str(e)}")
        raise
    except Exception as e:
        write_log(f"verify_and_decode_clerk_token: Unexpected error - {str(e)}")
        raise jwt.InvalidTokenError(f"Token verification failed: {str(e)}")
