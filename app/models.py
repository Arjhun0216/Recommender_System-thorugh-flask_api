# app/models.py
from datetime import datetime
from app import db


# ─────────────────────────────────────────
# TABLE 1 — Users
# ─────────────────────────────────────────
class User(db.Model):
    """
    Represents a user of any application that integrates with our system.
    One row per unique user.
    """
    __tablename__ = "users"

    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.String(100), unique=True, nullable=False)
    region    = db.Column(db.String(50),  nullable=True)
    created_at = db.Column(db.DateTime,   default=datetime.utcnow)

    # Relationships — tells SQLAlchemy how tables connect
    interactions    = db.relationship("Interaction",    backref="user", lazy=True)
    recommendations = db.relationship("Recommendation", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.user_id}>"


# ─────────────────────────────────────────
# TABLE 2 — Items
# ─────────────────────────────────────────
class Item(db.Model):
    """
    Represents anything that can be recommended —
    a product, video, article, song, etc.
    """
    __tablename__ = "items"

    id         = db.Column(db.Integer, primary_key=True)
    item_id    = db.Column(db.String(100), unique=True, nullable=False)
    category   = db.Column(db.String(100), nullable=True)
    region     = db.Column(db.String(50),  nullable=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    interactions = db.relationship("Interaction", backref="item", lazy=True)

    def __repr__(self):
        return f"<Item {self.item_id}>"


# ─────────────────────────────────────────
# TABLE 3 — Interactions
# ─────────────────────────────────────────

# Action weights — how much each action is worth
ACTION_WEIGHTS = {
    "view":  2,
    "like":  4,
    "cart":  8,
    "buy":  10,
}

class Interaction(db.Model):
    """
    Records every action a user performs on an item.
    This is the raw data the ML engine learns from.
    """
    __tablename__ = "interactions"

    id         = db.Column(db.Integer,     primary_key=True)
    user_id    = db.Column(db.String(100), db.ForeignKey("users.user_id"),  nullable=False)
    item_id    = db.Column(db.String(100), db.ForeignKey("items.item_id"),  nullable=False)
    action     = db.Column(db.String(20),  nullable=False)   # view/like/cart/buy
    weight     = db.Column(db.Float,       nullable=False)   # numeric score for ML
    region     = db.Column(db.String(50),  nullable=True)
    category   = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def __init__(self, user_id, item_id, action, region=None, category=None):
        self.user_id  = user_id
        self.item_id  = item_id
        self.action   = action
        self.weight   = ACTION_WEIGHTS.get(action, 1)  # auto-assign weight from action
        self.region   = region
        self.category = category

    def __repr__(self):
        return f"<Interaction {self.user_id} → {self.action} → {self.item_id}>"


# ─────────────────────────────────────────
# TABLE 4 — Recommendations
# ─────────────────────────────────────────
class Recommendation(db.Model):
    """
    Stores the ML engine's output for each user.
    The GET /recommend endpoint reads from this table.
    """
    __tablename__ = "recommendations"

    id           = db.Column(db.Integer,     primary_key=True)
    user_id      = db.Column(db.String(100), db.ForeignKey("users.user_id"), nullable=False)
    item_id      = db.Column(db.String(100), nullable=False)
    score        = db.Column(db.Float,       nullable=False)   # 0.0 to 1.0
    source       = db.Column(db.String(50),  nullable=True)    # history/collaborative/trending
    generated_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def __repr__(self):
        return f"<Recommendation {self.user_id} → {self.item_id} ({self.score})>"