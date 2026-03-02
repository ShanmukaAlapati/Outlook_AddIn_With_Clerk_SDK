import os
import logging
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from clerk_backend_api import Clerk, AuthenticateRequestOptions

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("case-counsel-api")

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",
    "https://localhost:3000",
    "https://outlook-addin-with-clerk-sdk.onrender.com",
    "https://outlook-addin-with-clerk-sdk-1.onrender.com",
    "https://outlook.office.com",
]}})

clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY", ""))

AUTHORIZED_PARTIES = [
    "http://localhost:3000",       # ✅ local Next.js dev
    "https://localhost:3000",
    "https://outlook-addin-with-clerk-sdk.onrender.com",
    "https://outlook.office.com",
]

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = clerk.authenticate_request(
                request,
                AuthenticateRequestOptions(
                    authorized_parties=AUTHORIZED_PARTIES
                )
            )
            if not result.is_signed_in:
                log.warning("Auth failed: %s", result.reason)
                return jsonify({"error": "Unauthorised", "reason": str(result.reason)}), 401

            request.clerk_payload = result.payload
            log.info("Auth OK: %s", result.payload.get("sub"))
        except Exception as e:
            log.error("Auth error: %s", e)
            return jsonify({"error": "Token verification failed", "detail": str(e)}), 401

        return f(*args, **kwargs)
    return wrapper


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/check-user", methods=["POST"])
@require_auth
def check_user():
    p = request.clerk_payload
    org_claim = p.get("o") or {}
    return jsonify({
        "status":   "success",
        "user_id":  p.get("sub"),
        "email":    p.get("email", ""),
        "org_id":   org_claim.get("id", ""),
        "org_role": f"org:{org_claim.get('rol')}" if org_claim.get("rol") else None,
        "org_slug": org_claim.get("slg", ""),
    })


@app.route("/api/me", methods=["GET"])
@require_auth
def me():
    p = request.clerk_payload
    return jsonify({"user_id": p.get("sub"), "email": p.get("email", "")})


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
