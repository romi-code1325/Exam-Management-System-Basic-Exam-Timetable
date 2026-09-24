"""
JWT-based authentication.

Two roles: "admin" (single bootstrap account from env vars) and "student"
(registered in the DB). Tokens carry {sub, role, ...} and are verified on
every protected route via the decorators below.
"""
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, jsonify, request

from config import Config


def issue_token(subject: str, role: str, extra: dict | None = None) -> str:
    payload = {
        "sub": subject,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=Config.JWT_EXPIRES_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])


def _extract_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):].strip()
    return None


def require_auth(*allowed_roles: str):
    """
    Decorator enforcing a valid JWT and (optionally) a specific role.
    On success, sets g.current_user = decoded token payload.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = _extract_token()
            if not token:
                return jsonify({"error": "Missing bearer token."}), 401
            try:
                payload = _decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token has expired."}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token."}), 401

            if allowed_roles and payload.get("role") not in allowed_roles:
                return jsonify({"error": "Insufficient permissions."}), 403

            g.current_user = payload
            return fn(*args, **kwargs)

        return wrapper

    return decorator
