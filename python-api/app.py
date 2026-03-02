import os
import jwt
import logging
import requests
from jwt import PyJWKClient
from datetime import datetime
from functools import lru_cache
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from utils.logging_errors import write_log

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("case-counsel-api")

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",
    "https://localhost:3000",
    "https://outlook-addin-with-clerk-sdk-1.onrender.com",
    "https://outlook-addin-with-clerk-sdk.onrender.com",
    "https://outlook.office.com",
]}})


# ─── JWKS Client ──────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_jwks_client():
    try:
        clerk_domain = os.getenv("CLERK_FRONTEND_API")
        write_log(f"get_jwks_client: Building JWKS client for domain={clerk_domain}")
        jwks_url = f"https://{clerk_domain}/.well-known/jwks.json"
        client = PyJWKClient(jwks_url, cache_keys=True, cache_jwk_set=True, lifespan=3600)
        write_log("get_jwks_client: JWKS client created successfully")
        return client
    except Exception as e:
        write_log(f"get_jwks_client: Failed to create JWKS client - {str(e)}")
        raise


# ─── Clerk API Helpers ────────────────────────────────────────────────────────
def get_clerk_user_data(user_id: str) -> dict:
    try:
        write_log(f"get_clerk_user_data: Fetching user data for user_id={user_id}")
        secret_key = os.getenv("CLERK_SECRET_KEY")
        url = f"https://api.clerk.com/v1/users/{user_id}"
        res = requests.get(url, headers={"Authorization": f"Bearer {secret_key}"})
        write_log(f"get_clerk_user_data: Clerk API response status={res.status_code}")
        res.raise_for_status()
        data = res.json()
        write_log(f"get_clerk_user_data: User data fetched successfully for user_id={user_id}")
        return data
    except requests.exceptions.HTTPError as e:
        write_log(f"get_clerk_user_data: HTTP error fetching user - status={res.status_code} error={str(e)}")
        raise
    except Exception as e:
        write_log(f"get_clerk_user_data: Unexpected error - {str(e)}")
        raise


def get_clerk_organization_data(org_id: str) -> dict:
    try:
        write_log(f"get_clerk_organization_data: Fetching org data for org_id={org_id}")
        secret_key = os.getenv("CLERK_SECRET_KEY")
        url = f"https://api.clerk.com/v1/organizations/{org_id}"
        res = requests.get(url, headers={"Authorization": f"Bearer {secret_key}"})
        write_log(f"get_clerk_organization_data: Clerk API response status={res.status_code}")
        res.raise_for_status()
        data = res.json()
        write_log(f"get_clerk_organization_data: Org data fetched successfully for org_id={org_id}")
        return data
    except requests.exceptions.HTTPError as e:
        write_log(f"get_clerk_organization_data: HTTP error fetching org - status={res.status_code} error={str(e)}")
        raise
    except Exception as e:
        write_log(f"get_clerk_organization_data: Unexpected error - {str(e)}")
        raise


# ─── Token Verification ───────────────────────────────────────────────────────
def verify_and_decode_clerk_token(token: str) -> dict:
    try:
        write_log("verify_and_decode_clerk_token: Starting token verification")

        # Step 1 — Get JWKS client
        try:
            jwk_client = get_jwks_client()
            write_log("verify_and_decode_clerk_token: JWKS client retrieved")
        except Exception as e:
            write_log(f"verify_and_decode_clerk_token: Failed to get JWKS client - {str(e)}")
            raise

        # Step 2 — Extract token header
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            write_log(f"verify_and_decode_clerk_token: Token header extracted, kid={kid}")
        except Exception as e:
            write_log(f"verify_and_decode_clerk_token: Failed to extract token header - {str(e)}")
            raise jwt.InvalidTokenError(f"Invalid token header: {str(e)}")

        # Step 3 — Get signing key
        try:
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            public_key = signing_key.key
            write_log("verify_and_decode_clerk_token: Signing key retrieved from JWKS")
        except Exception as e:
            write_log(f"verify_and_decode_clerk_token: Failed to get signing key - {str(e)}")
            raise jwt.InvalidTokenError(f"Failed to get signing key: {str(e)}")

        # Step 4 — Decode and verify token
        try:
            clerk_frontend_api = os.getenv("CLERK_FRONTEND_API")
            issuer = f"https://{clerk_frontend_api}"
            write_log(f"verify_and_decode_clerk_token: Verifying token with issuer={issuer}")

            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=issuer,
                leeway=60,
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
            write_log(f"verify_and_decode_clerk_token: Token decoded successfully, claims={list(decoded.keys())}")
        except jwt.ExpiredSignatureError:
            write_log("verify_and_decode_clerk_token: Token is expired")
            raise
        except jwt.InvalidIssuerError:
            write_log(f"verify_and_decode_clerk_token: Invalid issuer in token")
            raise
        except jwt.InvalidTokenError as e:
            write_log(f"verify_and_decode_clerk_token: Token decode failed - {str(e)}")
            raise

        # Step 5 — Extract claims
        try:
            user_id    = decoded.get("sub")
            session_id = decoded.get("sid")
            issued_at  = decoded.get("iat")
            expires_at = decoded.get("exp")

            org_claim = decoded.get("o", {}) or {}
            org_id    = org_claim.get("id")
            org_slug  = org_claim.get("slg")
            org_role  = org_claim.get("rol")

            write_log(f"verify_and_decode_clerk_token: Claims extracted - user_id={user_id}, org_id={org_id}, org_role={org_role}")
        except Exception as e:
            write_log(f"verify_and_decode_clerk_token: Failed to extract claims - {str(e)}")
            raise

        # Step 6 — Fetch user from Clerk API
        try:
            write_log(f"verify_and_decode_clerk_token: Fetching user from Clerk API for user_id={user_id}")
            user_data = get_clerk_user_data(user_id)

            email_addresses  = user_data.get("email_addresses", [])
            primary_email_id = user_data.get("primary_email_address_id")

            email      = None
            all_emails = []
            for email_obj in email_addresses:
                email_addr = email_obj.get("email_address")
                if email_addr:
                    all_emails.append(email_addr)
                    if email_obj.get("id") == primary_email_id:
                        email = email_addr

            if not email and all_emails:
                email = all_emails[0]

            first_name = user_data.get("first_name")
            last_name  = user_data.get("last_name")
            full_name  = f"{first_name or ''} {last_name or ''}".strip() or None
            username   = user_data.get("username")

            write_log(f"verify_and_decode_clerk_token: User data resolved - email={email}, full_name={full_name}")
        except Exception as e:
            write_log(f"verify_and_decode_clerk_token: Failed to fetch user data - {str(e)}")
            raise

        # Step 7 — Fetch org from Clerk API
        try:
            org_name = None
            if org_id:
                write_log(f"verify_and_decode_clerk_token: Fetching org from Clerk API for org_id={org_id}")
                org_data = get_clerk_organization_data(org_id)
                org_name = org_data.get("name")
                write_log(f"verify_and_decode_clerk_token: Org resolved - org_name={org_name}")
            else:
                write_log("verify_and_decode_clerk_token: No org_id in token, skipping org fetch")
        except Exception as e:
            write_log(f"verify_and_decode_clerk_token: Failed to fetch org data - {str(e)}")
            raise

        # Step 8 — Determine role
        try:
            def timestamp_to_iso(ts):
                if ts:
                    return datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                return None

            super_admin_email = os.getenv("SUPER_ADMIN_EMAIL")
            if super_admin_email and email and email.lower() == super_admin_email.lower():
                final_org_role = "super-admin"
                write_log(f"verify_and_decode_clerk_token: Super admin detected - email={email}")
            else:
                final_org_role = f"org:{org_role}" if org_role else None
                write_log(f"verify_and_decode_clerk_token: Role resolved - final_org_role={final_org_role}")
        except Exception as e:
            write_log(f"verify_and_decode_clerk_token: Failed to determine role - {str(e)}")
            raise

        # Step 9 — Build auth_info
        try:
            auth_info = {
                "user_id":                user_id,
                "sub":                    user_id,
                "email":                  email,
                "full_name":              full_name,
                "username":               username,
                "all_emails":             all_emails,
                "org_id":                 org_id,
                "org_slug":               org_slug,
                "org_name":               org_name,
                "org_role":               final_org_role,
                "session_id":             session_id,
                "session_status":         "active",
                "session_last_active_at": timestamp_to_iso(issued_at),
                "session_expire_at":      timestamp_to_iso(expires_at),
                "session_created_at":     timestamp_to_iso(issued_at),
                "session_updated_at":     timestamp_to_iso(issued_at),
                "raw_token":              token,
            }
            write_log(f"verify_and_decode_clerk_token: auth_info built successfully - user={email}, role={final_org_role}")
            return auth_info
        except Exception as e:
            write_log(f"verify_and_decode_clerk_token: Failed to build auth_info - {str(e)}")
            raise

    except jwt.ExpiredSignatureError as e:
        write_log(f"verify_and_decode_clerk_token: Token expired - {str(e)}")
        raise
    except jwt.InvalidTokenError as e:
        write_log(f"verify_and_decode_clerk_token: Invalid token - {str(e)}")
        raise
    except Exception as e:
        write_log(f"verify_and_decode_clerk_token: Unexpected error - {str(e)}")
        raise jwt.InvalidTokenError(f"Token verification failed: {str(e)}")


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    write_log("health: Health check called")
    return jsonify({"status": "ok"})


@app.route("/api/check-user", methods=["POST"])
def check_user():
    try:
        write_log("check_user: Endpoint called")

        # Step 1 — Validate Authorization header
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                write_log("check_user: Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(" ")[1]
            write_log(f"check_user: Token extracted, length={len(token)}")
        except Exception as e:
            write_log(f"check_user: Failed to extract token - {str(e)}")
            return jsonify({"error": "Failed to extract token"}), 401

        # Step 2 — Verify token
        try:
            auth_info = verify_and_decode_clerk_token(token)
            write_log(f"check_user: Token verified successfully, user_id={auth_info.get('user_id')}")
        except jwt.ExpiredSignatureError:
            write_log("check_user: Token expired")
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            write_log(f"check_user: Invalid token - {str(e)}")
            return jsonify({"error": "Invalid token", "detail": str(e)}), 401
        except Exception as e:
            write_log(f"check_user: Token verification failed - {str(e)}")
            return jsonify({"error": "Token verification failed", "detail": str(e)}), 401

        # Step 3 — Build and return response
        try:
            org_role = auth_info.get("org_role")
            write_log(f"check_user: Response prepared - role={org_role}, user_id={auth_info.get('user_id')}")
            return jsonify({
                "role":      org_role,
                "user_info": auth_info,
            }), 200
        except Exception as e:
            write_log(f"check_user: Failed to build response - {str(e)}")
            return jsonify({"error": "Failed to build response"}), 500

    except Exception as e:
        write_log(f"check_user: Unexpected error - {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/me", methods=["GET"])
def me():
    try:
        write_log("me: Endpoint called")

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                write_log("me: Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(" ")[1]
            write_log(f"me: Token extracted, length={len(token)}")
        except Exception as e:
            write_log(f"me: Failed to extract token - {str(e)}")
            return jsonify({"error": "Failed to extract token"}), 401

        try:
            auth_info = verify_and_decode_clerk_token(token)
            write_log(f"me: Token verified, user_id={auth_info.get('user_id')}, email={auth_info.get('email')}")
            return jsonify({
                "user_id": auth_info.get("user_id"),
                "email":   auth_info.get("email"),
            })
        except jwt.ExpiredSignatureError:
            write_log("me: Token expired")
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            write_log(f"me: Invalid token - {str(e)}")
            return jsonify({"error": "Invalid token", "detail": str(e)}), 401
        except Exception as e:
            write_log(f"me: Token verification failed - {str(e)}")
            return jsonify({"error": "Token verification failed", "detail": str(e)}), 401

    except Exception as e:
        write_log(f"me: Unexpected error - {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


# ─── Error Handlers ───────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    write_log(f"404: Route not found - {request.path}")
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    write_log(f"500: Internal server error - {str(e)}")
    log.exception("Unhandled error")
    return jsonify({"error": "Internal server error"}), 500


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    write_log(f"Starting Case Counsel API on port={port}, debug={debug}")
    app.run(host="0.0.0.0", port=port, debug=debug)
