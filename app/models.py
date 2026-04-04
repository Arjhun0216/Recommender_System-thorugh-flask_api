# app/models.py
import uuid
from datetime import datetime
from app import db


# ─────────────────────────────────────────
# Helper — generate unique API keys
# ─────────────────────────────────────────
def generate_api_key():
    return "rec_" + uuid.uuid4().hex  # e.g. rec_a3f9b2c1d4e5...


# ─────────────────────────────────────────
# TABLE 1 — Developers
# ─────────────────────────────────────────
class Developer(db.Model):
    __tablename__ = "developers"

    id         = db.Column(db.Integer,     primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), unique=True, nullable=False)
    app_name   = db.Column(db.String(100), nullable=False)
    api_key    = db.Column(db.String(100), unique=True, nullable=False,
                           default=generate_api_key)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def __repr__(self):
        return f"<Developer {self.email}>"


# ─────────────────────────────────────────
# TABLE 2 — Users
# ─────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer,     primary_key=True)
    api_key    = db.Column(db.String(100), nullable=False)   # which developer owns this user
    user_id    = db.Column(db.String(100), nullable=False)
    region     = db.Column(db.String(50),  nullable=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    interactions    = db.relationship("Interaction",    backref="user", lazy=True)
    recommendations = db.relationship("Recommendation", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.api_key}:{self.user_id}>"


# ─────────────────────────────────────────
# TABLE 3 — Items
# ─────────────────────────────────────────
class Item(db.Model):
    __tablename__ = "items"

    id         = db.Column(db.Integer,     primary_key=True)
    api_key    = db.Column(db.String(100), nullable=False)
    item_id    = db.Column(db.String(100), nullable=False)
    category   = db.Column(db.String(100), nullable=True)
    region     = db.Column(db.String(50),  nullable=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    interactions = db.relationship("Interaction", backref="item", lazy=True)

    def __repr__(self):
        return f"<Item {self.api_key}:{self.item_id}>"


# ─────────────────────────────────────────
# TABLE 4 — Interactions
# ─────────────────────────────────────────
ACTION_WEIGHTS = {
    "view":  2,
    "like":  4,
    "cart":  8,
    "buy":  10,
}

class Interaction(db.Model):
    __tablename__ = "interactions"

    id         = db.Column(db.Integer,     primary_key=True)
    api_key    = db.Column(db.String(100), nullable=False)
    user_id    = db.Column(db.String(100), db.ForeignKey("users.user_id"),  nullable=False)
    item_id    = db.Column(db.String(100), db.ForeignKey("items.item_id"),  nullable=False)
    action     = db.Column(db.String(20),  nullable=False)
    weight     = db.Column(db.Float,       nullable=False)
    region     = db.Column(db.String(50),  nullable=True)
    category   = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def __init__(self, api_key, user_id, item_id, action, region=None, category=None):
        self.api_key  = api_key
        self.user_id  = user_id
        self.item_id  = item_id
        self.action   = action
        self.weight   = ACTION_WEIGHTS.get(action, 1)
        self.region   = region
        self.category = category

    def __repr__(self):
        return f"<Interaction {self.api_key}:{self.user_id} → {self.action} → {self.item_id}>"


# ─────────────────────────────────────────
# TABLE 5 — Recommendations
# ─────────────────────────────────────────
class Recommendation(db.Model):
    __tablename__ = "recommendations"

    id           = db.Column(db.Integer,     primary_key=True)
    api_key      = db.Column(db.String(100), nullable=False)
    user_id      = db.Column(db.String(100), db.ForeignKey("users.user_id"), nullable=False)
    item_id      = db.Column(db.String(100), nullable=False)
    score        = db.Column(db.Float,       nullable=False)
    source       = db.Column(db.String(50),  nullable=True)
    generated_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def __repr__(self):
        return f"<Recommendation {self.api_key}:{self.user_id} → {self.item_id}>"