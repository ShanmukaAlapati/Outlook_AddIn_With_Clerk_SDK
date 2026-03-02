import os
import logging
import jwt
from jwt import PyJWKClient
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("case-counsel-api")

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",
    "https://outlook-addin-with-clerk-sdk-1.onrender.com",
]}})

# ── JWKS client (cached) ───────────────────────────────────────────────────────
_jwks_client = None

def get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        frontend_api = os.getenv("CLERK_FRONTEND_API", "")
        if not frontend_api:
            raise Exception("CLERK_FRONTEND_API env var not set")
        jwks_url = f"https://{frontend_api}/.well-known/jwks.json"
        log.info("JWKS URL: %s", jwks_url)
        _jwks_client = PyJWKClient(
            jwks_url,
            cache_keys=True,
            cache_jwk_set=True,
            lifespan=3600
        )
    return _jwks_client


def verify_clerk_token(token: str) -> dict:
    client = get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)

    frontend_api = os.getenv("CLERK_FRONTEND_API", "")
    issuer = f"https://{frontend_api}"

    decoded = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=issuer,
        leeway=60,
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": False,
        }
    )

    org_claim = decoded.get("o") or {}
    return {
        "user_id": decoded.get("sub"),
        "sub":     decoded.get("sub"),
        "email":   decoded.get("email", ""),
        "org_id":  org_claim.get("id", ""),
        "org_role": f"org:{org_claim.get('rol')}" if org_claim.get("rol") else None,
        "org_slug": org_claim.get("slg", ""),
    }


# ── Auth decorator ─────────────────────────────────────────────────────────────
def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Authorisation required"}), 401

        token = header.split(" ", 1)[1].strip()

        try:
            request.clerk_payload = verify_clerk_token(token)
            log.info("Auth OK: %s", request.clerk_payload.get("user_id"))
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            log.error("Invalid token: %s", e)
            return jsonify({"error": "Invalid token"}), 401
        except Exception as e:
            log.error("Token error: %s", e)
            return jsonify({"error": "Token verification failed", "detail": str(e)}), 401

        return f(*args, **kwargs)
    return wrapper


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/check-user", methods=["POST"])
@require_auth
def check_user():
    p = request.clerk_payload
    return jsonify({
        "status":   "success",
        "user_id":  p.get("user_id"),
        "email":    p.get("email"),
        "org_id":   p.get("org_id"),
        "org_role": p.get("org_role"),
        "org_slug": p.get("org_slug"),
    })


@app.route("/api/me", methods=["GET"])
@require_auth
def me():
    p = request.clerk_payload
    return jsonify({"user_id": p.get("user_id"), "email": p.get("email")})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    log.exception("Unhandled error")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    log.info("Starting on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
