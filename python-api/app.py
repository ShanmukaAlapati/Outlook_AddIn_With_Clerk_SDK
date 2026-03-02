import os
import logging
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from clerk_backend_api import Clerk, AuthenticateRequestOptions

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("case-counsel-api")

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": [
    "http://localhost:3000",
    "https://outlook-addin-with-clerk-sdk-1.onrender.com",
]}})

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Authorisation required"}), 401

        token = header.split(" ", 1)[1].strip()

        try:
            secret = os.getenv("CLERK_SECRET_KEY", "")
            if not secret:
                return jsonify({"error": "CLERK_SECRET_KEY not set"}), 500

            clerk = Clerk(bearer_auth=secret)

            # Build a minimal mock request object Clerk SDK expects
            class MockRequest:
                def __init__(self, token):
                    self.headers = {"Authorization": f"Bearer {token}"}
                    self.method = "POST"
                    self.url = "http://localhost:5000/api/check-user"

            state = clerk.authenticate_request(
                MockRequest(token),
                AuthenticateRequestOptions(
                    authorized_parties=["http://localhost:3000"]
                )
            )

            if not state.is_signed_in:
                log.warning("Token rejected: %s", state.reason)
                return jsonify({"error": "Invalid or expired token", "reason": str(state.reason)}), 401

            request.clerk_payload = state.payload
            log.info("Auth OK: %s", state.payload.get("sub"))

        except Exception as e:
            log.error("Token error: %s", e)
            return jsonify({"error": "Token verification failed", "detail": str(e)}), 401

        return f(*args, **kwargs)
    return wrapper


@app.route("/health")
def health():
    return jsonify({"status": "ok", "clerk_configured": bool(os.getenv("CLERK_SECRET_KEY"))})


@app.route("/api/check-user", methods=["POST"])
@require_auth
def check_user():
    payload = request.clerk_payload
    org = payload.get("o", {})
    return jsonify({
        "status": "success",
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "org_id": org.get("id"),
        "org_role": org.get("rol"),
        "org_slug": org.get("slg"),
    })


@app.route("/api/me", methods=["GET"])
@require_auth
def me():
    p = request.clerk_payload
    return jsonify({"user_id": p.get("sub"), "email": p.get("email")})


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