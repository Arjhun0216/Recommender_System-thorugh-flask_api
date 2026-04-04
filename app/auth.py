# app/auth.py
from functools import wraps
from flask import request, jsonify
from app.models import Developer
from app.cache import api_key_cache


def require_api_key(f):
    """
    Protects API routes with key validation.
    Uses APIKeyCache — database is only hit once
    per key per 5 minutes instead of every request.
    """
    @wraps(f)
    def decorated(*args, **kwargs):

        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return jsonify({
                "status":  "error",
                "message": "Missing API key. Add X-API-Key to your request headers."
            }), 401

        # ── Check cache first (O(1)) ──
        developer = api_key_cache.get(api_key)

        if developer is None:
            # Cache miss — hit the database
            developer = Developer.query.filter_by(api_key=api_key).first()

            if not developer:
                return jsonify({
                    "status":  "error",
                    "message": "Invalid API key."
                }), 403

            # Store in cache for next requests
            api_key_cache.set(api_key, developer)

        return f(developer, *args, **kwargs)

    return decorated