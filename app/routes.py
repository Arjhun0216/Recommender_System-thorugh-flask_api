# app/routes.py
from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Item, Interaction, Recommendation
from app.engine import generate_recommendations
from datetime import datetime

api = Blueprint("api", __name__)


# ─────────────────────────────────────────
# HEALTH CHECK
# GET /api/v1/health
# ─────────────────────────────────────────
@api.route("/health", methods=["GET"])
def health():
    """
    Simple check to confirm the server is running.
    Use this first whenever you start the server.
    """
    return jsonify({
        "status":  "ok",
        "message": "Recommendation system is running",
        "time":    datetime.utcnow().isoformat()
    }), 200


# ─────────────────────────────────────────
# RECORD INTERACTION
# POST /api/v1/interact
# ─────────────────────────────────────────
@api.route("/interact", methods=["POST"])
def interact():
    """
    Receives a user action on an item.
    Creates the user and item if they don't exist yet.
    Records the interaction and triggers recommendation generation.

    Expected JSON body:
    {
        "user_id":  "user_123",
        "item_id":  "product_456",
        "action":   "buy",
        "region":   "IN-TN",       (optional)
        "category": "electronics"  (optional)
    }
    """

    # Step 1 — parse the incoming JSON
    data = request.get_json()

    # Step 2 — validate required fields
    required = ["user_id", "item_id", "action"]
    for field in required:
        if not data or field not in data:
            return jsonify({
                "status":  "error",
                "message": f"Missing required field: {field}"
            }), 400

    valid_actions = ["view", "like", "cart", "buy"]
    if data["action"] not in valid_actions:
        return jsonify({
            "status":  "error",
            "message": f"Invalid action. Must be one of: {valid_actions}"
        }), 400

    user_id  = data["user_id"]
    item_id  = data["item_id"]
    action   = data["action"]
    region   = data.get("region")
    category = data.get("category")

    # Step 3 — create user if doesn't exist
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        user = User(user_id=user_id, region=region)
        db.session.add(user)

    # Step 4 — create item if doesn't exist
    item = Item.query.filter_by(item_id=item_id).first()
    if not item:
        item = Item(item_id=item_id, category=category, region=region)
        db.session.add(item)

    # Step 5 — record the interaction
    interaction = Interaction(
        user_id=user_id,
        item_id=item_id,
        action=action,
        region=region,
        category=category
    )
    db.session.add(interaction)
    db.session.commit()

    # Step 6 — regenerate recommendations for this user
    generate_recommendations(user_id)

    return jsonify({
        "status":         "success",
        "message":        "Interaction recorded",
        "interaction_id": interaction.id,
        "weight_assigned": interaction.weight
    }), 201


# ─────────────────────────────────────────
# GET RECOMMENDATIONS
# GET /api/v1/recommend?user_id=xxx&limit=10
# ─────────────────────────────────────────
@api.route("/recommend", methods=["GET"])
def recommend():
    """
    Returns personalized recommendations for a user.
    Reads from the recommendations table (pre-generated after each interaction).

    Query params:
        user_id  — required
        limit    — optional, default 10
    """

    # Step 1 — read query parameters
    user_id = request.args.get("user_id")
    limit   = request.args.get("limit", 10, type=int)

    # Step 2 — validate
    if not user_id:
        return jsonify({
            "status":  "error",
            "message": "Missing required parameter: user_id"
        }), 400

    # Step 3 — check user exists
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify({
            "status":  "error",
            "message": f"User '{user_id}' not found. Send an interaction first."
        }), 404

    # Step 4 — fetch recommendations from db
    recs = (
        Recommendation.query
        .filter_by(user_id=user_id)
        .order_by(Recommendation.score.desc())
        .limit(limit)
        .all()
    )

    # Step 5 — format and return
    return jsonify({
        "status":          "success",
        "user_id":         user_id,
        "count":           len(recs),
        "recommendations": [
            {
                "item_id": r.item_id,
                "score":   r.score,
            }
            for r in recs
        ],
        "generated_at": recs[0].generated_at.isoformat() if recs else None
    }), 200


# ─────────────────────────────────────────
# GET ALL USERS  (useful for testing)
# GET /api/v1/users
# ─────────────────────────────────────────
@api.route("/users", methods=["GET"])
def get_users():
    """Returns all users currently in the system."""
    users = User.query.all()
    return jsonify({
        "status": "success",
        "count":  len(users),
        "users": [
            {"user_id": u.user_id, "region": u.region, "created_at": u.created_at.isoformat()}
            for u in users
        ]
    }), 200


# ─────────────────────────────────────────
# GET ALL INTERACTIONS  (useful for testing)
# GET /api/v1/interactions?user_id=xxx
# ─────────────────────────────────────────
@api.route("/interactions", methods=["GET"])
def get_interactions():
    """Returns all interactions, optionally filtered by user_id."""
    user_id = request.args.get("user_id")

    if user_id:
        interactions = Interaction.query.filter_by(user_id=user_id).all()
    else:
        interactions = Interaction.query.all()

    return jsonify({
        "status": "success",
        "count":  len(interactions),
        "interactions": [
            {
                "user_id":  i.user_id,
                "item_id":  i.item_id,
                "action":   i.action,
                "weight":   i.weight,
                "region":   i.region,
                "category": i.category,
            }
            for i in interactions
        ]
    }), 200