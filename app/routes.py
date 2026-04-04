# app/routes.py
from flask import Blueprint, request, jsonify
from app import db
from app.models import Developer, User, Item, Interaction, Recommendation
from app.engine import generate_recommendations
from app.auth import require_api_key
from datetime import datetime

api = Blueprint("api", __name__)


# ─────────────────────────────────────────
# REGISTER — no API key needed for this one
# POST /api/v1/register
# ─────────────────────────────────────────
@api.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    required = ["name", "email", "app_name"]
    for field in required:
        if not data or field not in data:
            return jsonify({
                "status":  "error",
                "message": f"Missing required field: {field}"
            }), 400

    # Check email not already registered
    existing = Developer.query.filter_by(email=data["email"]).first()
    if existing:
        return jsonify({
            "status":  "error",
            "message": "Email already registered."
        }), 409

    developer = Developer(
        name     = data["name"],
        email    = data["email"],
        app_name = data["app_name"]
    )
    db.session.add(developer)
    db.session.commit()

    return jsonify({
        "status":   "success",
        "message":  "Registration successful. Store your API key safely — it will not be shown again.",
        "api_key":  developer.api_key,
        "app_name": developer.app_name,
    }), 201


# ─────────────────────────────────────────
# HEALTH CHECK
# GET /api/v1/health
# ─────────────────────────────────────────
@api.route("/health", methods=["GET"])
def health():
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
@require_api_key
def interact(developer):
    data = request.get_json()

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

    api_key  = developer.api_key
    user_id  = data["user_id"]
    item_id  = data["item_id"]
    action   = data["action"]
    region   = data.get("region")
    category = data.get("category")

    # Create user if not exists — scoped to this api_key
    user = User.query.filter_by(api_key=api_key, user_id=user_id).first()
    if not user:
        user = User(api_key=api_key, user_id=user_id, region=region)
        db.session.add(user)

    # Create item if not exists — scoped to this api_key
    item = Item.query.filter_by(api_key=api_key, item_id=item_id).first()
    if not item:
        item = Item(api_key=api_key, item_id=item_id, category=category, region=region)
        db.session.add(item)

    interaction = Interaction(
        api_key=api_key,
        user_id=user_id,
        item_id=item_id,
        action=action,
        region=region,
        category=category
    )
    db.session.add(interaction)
    db.session.commit()

    generate_recommendations(api_key, user_id)

    return jsonify({
        "status":          "success",
        "message":         "Interaction recorded",
        "interaction_id":  interaction.id,
        "weight_assigned": interaction.weight
    }), 201


# ─────────────────────────────────────────
# GET RECOMMENDATIONS
# GET /api/v1/recommend?user_id=xxx
# ─────────────────────────────────────────
@api.route("/recommend", methods=["GET"])
@require_api_key
def recommend(developer):
    user_id = request.args.get("user_id")
    limit   = request.args.get("limit", 10, type=int)

    if not user_id:
        return jsonify({
            "status":  "error",
            "message": "Missing required parameter: user_id"
        }), 400

    api_key = developer.api_key
    user = User.query.filter_by(api_key=api_key, user_id=user_id).first()
    if not user:
        return jsonify({
            "status":  "error",
            "message": f"User '{user_id}' not found."
        }), 404

    recs = (
        Recommendation.query
        .filter_by(api_key=api_key, user_id=user_id)
        .order_by(Recommendation.score.desc())
        .limit(limit)
        .all()
    )

    return jsonify({
        "status":          "success",
        "user_id":         user_id,
        "app_name":        developer.app_name,
        "count":           len(recs),
        "recommendations": [
            {"item_id": r.item_id, "score": r.score}
            for r in recs
        ],
        "generated_at": recs[0].generated_at.isoformat() if recs else None
    }), 200


# ─────────────────────────────────────────
# GET MY USERS
# GET /api/v1/users
# ─────────────────────────────────────────
@api.route("/users", methods=["GET"])
@require_api_key
def get_users(developer):
    users = User.query.filter_by(api_key=developer.api_key).all()
    return jsonify({
        "status":   "success",
        "app_name": developer.app_name,
        "count":    len(users),
        "users": [
            {"user_id": u.user_id, "region": u.region}
            for u in users
        ]
    }), 200


# ─────────────────────────────────────────
# GET MY INTERACTIONS
# GET /api/v1/interactions
# ─────────────────────────────────────────
@api.route("/interactions", methods=["GET"])
@require_api_key
def get_interactions(developer):
    user_id = request.args.get("user_id")

    query = Interaction.query.filter_by(api_key=developer.api_key)
    if user_id:
        query = query.filter_by(user_id=user_id)

    interactions = query.all()
    return jsonify({
        "status":   "success",
        "app_name": developer.app_name,
        "count":    len(interactions),
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