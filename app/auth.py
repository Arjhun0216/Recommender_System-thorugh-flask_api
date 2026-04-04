# app/auth.py
from functools import wraps
from flask import request, jsonify
from app.models import Developer


def require_api_key(f):
    """
    Decorator that protects any route.
    Reads X-API-Key from request header,
    validates it, and injects the developer
    object into the route function.

    Usage:
        @api.route("/interact")
        @require_api_key
        def interact(developer):
            # developer is automatically available here
    """
    @wraps(f)
    def decorated(*args, **kwargs):

        # Read the API key from request header
        api_key = request.headers.get("X-API-Key")

        # Missing key
        if not api_key:
            return jsonify({
                "status":  "error",
                "message": "Missing API key. Add X-API-Key to your request headers."
            }), 401

        # Look up the developer
        developer = Developer.query.filter_by(api_key=api_key).first()

        # Invalid key
        if not developer:
            return jsonify({
                "status":  "error",
                "message": "Invalid API key. Register at POST /api/v1/register"
            }), 403

        # Valid — pass developer into the route
        return f(developer, *args, **kwargs)

    return decorated