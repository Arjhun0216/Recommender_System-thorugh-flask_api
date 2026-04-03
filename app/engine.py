# app/engine.py
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app import db
from app.models import User, Item, Interaction, Recommendation
from datetime import datetime


# ─────────────────────────────────────────
# HELPER — Normalize scores to 0.0 → 1.0
# ─────────────────────────────────────────
def normalize(scores: dict) -> dict:
    """
    Takes a dict of {item_id: raw_score}
    Returns the same dict with scores scaled between 0.0 and 1.0

    Example:
        Input:  {"item_a": 10, "item_b": 20, "item_c": 5}
        Output: {"item_a": 0.5, "item_b": 1.0, "item_c": 0.25}
    """
    if not scores:
        return {}

    max_score = max(scores.values())

    if max_score == 0:
        return {k: 0.0 for k in scores}

    return {k: round(v / max_score, 4) for k, v in scores.items()}


# ─────────────────────────────────────────
# SOURCE 1 — User's Own History (40%)
# ─────────────────────────────────────────
def get_history_scores(user_id: str) -> dict:
    """
    Scores items based on what THIS user has interacted with.
    Higher weight actions (buy=10) score higher than low weight (view=2).

    Returns: {item_id: total_weight_score}
    """
    interactions = Interaction.query.filter_by(user_id=user_id).all()

    scores = {}
    for interaction in interactions:
        item = interaction.item_id
        scores[item] = scores.get(item, 0) + interaction.weight

    return normalize(scores)


# ─────────────────────────────────────────
# SOURCE 2 — Collaborative Filtering (30%)
# ─────────────────────────────────────────
def get_collaborative_scores(user_id: str) -> dict:
    """
    Finds users who behaved similarly to this user (using cosine similarity).
    Recommends items those similar users liked that this user hasn't seen yet.

    Steps:
    1. Build a user-item matrix (rows=users, columns=items, values=weights)
    2. Compute cosine similarity between our user and all others
    3. Find top 5 most similar users
    4. Collect items those users interacted with
    5. Exclude items our user already knows about
    6. Score by how similar the users were

    Returns: {item_id: collaborative_score}
    """
    # Step 1 — pull all interactions from the database
    all_interactions = Interaction.query.all()

    if not all_interactions:
        return {}

    # Build a DataFrame: rows=users, cols=items, values=sum of weights
    data = [{"user_id": i.user_id, "item_id": i.item_id, "weight": i.weight}
            for i in all_interactions]
    df = pd.DataFrame(data)

    # Pivot into matrix form
    matrix = df.pivot_table(
        index="user_id",
        columns="item_id",
        values="weight",
        aggfunc="sum",
        fill_value=0
    )

    # Step 2 — if this user isn't in the matrix yet, no collaborative data
    if user_id not in matrix.index:
        return {}

    # Step 3 — compute cosine similarity between all users
    similarity_matrix = cosine_similarity(matrix)
    similarity_df = pd.DataFrame(
        similarity_matrix,
        index=matrix.index,
        columns=matrix.index
    )

    # Step 4 — get similarity scores for our user, sorted descending
    user_similarities = similarity_df[user_id].drop(user_id).sort_values(ascending=False)

    # Take top 5 most similar users
    top_similar_users = user_similarities.head(5)

    if top_similar_users.empty:
        return {}

    # Step 5 — items our user has already seen
    seen_items = set(matrix.columns[matrix.loc[user_id] > 0])

    # Step 6 — score unseen items by similar users' interactions
    scores = {}
    for similar_user, similarity_score in top_similar_users.items():
        if similarity_score <= 0:
            continue

        # Items this similar user interacted with
        similar_user_items = matrix.loc[similar_user]
        for item_id, weight in similar_user_items.items():
            if item_id not in seen_items and weight > 0:
                # Score = how much they interacted × how similar they are to us
                scores[item_id] = scores.get(item_id, 0) + (weight * similarity_score)

    return normalize(scores)


# ─────────────────────────────────────────
# SOURCE 3 — Regional Trending (20%)
# ─────────────────────────────────────────
def get_regional_scores(region: str) -> dict:
    """
    Finds the most interacted-with items in the user's region.
    Returns: {item_id: regional_score}
    """
    if not region:
        return {}

    interactions = Interaction.query.filter_by(region=region).all()

    scores = {}
    for interaction in interactions:
        item = interaction.item_id
        scores[item] = scores.get(item, 0) + interaction.weight

    return normalize(scores)


# ─────────────────────────────────────────
# SOURCE 4 — Global Trending (10%)
# ─────────────────────────────────────────
def get_global_scores() -> dict:
    """
    Finds the most interacted-with items across all users and regions.
    Returns: {item_id: global_score}
    """
    interactions = Interaction.query.all()

    scores = {}
    for interaction in interactions:
        item = interaction.item_id
        scores[item] = scores.get(item, 0) + interaction.weight

    return normalize(scores)


# ─────────────────────────────────────────
# BLENDER — Combine all 4 sources
# ─────────────────────────────────────────
def blend_scores(history, collaborative, regional, global_scores) -> dict:
    """
    Merges all 4 score sources using their weights:
        History       → 40%
        Collaborative → 30%
        Regional      → 20%
        Global        → 10%

    For each item, final_score = sum of (source_score × source_weight)
    """
    weights = {
        "history":       0.40,
        "collaborative": 0.30,
        "regional":      0.20,
        "global":        0.10,
    }

    # Collect all unique item_ids across all sources
    all_items = set(history) | set(collaborative) | set(regional) | set(global_scores)

    blended = {}
    for item_id in all_items:
        score = (
            history.get(item_id, 0)       * weights["history"]       +
            collaborative.get(item_id, 0) * weights["collaborative"] +
            regional.get(item_id, 0)      * weights["regional"]      +
            global_scores.get(item_id, 0) * weights["global"]
        )
        blended[item_id] = round(score, 4)

    return blended


# ─────────────────────────────────────────
# MAIN — Generate & Save Recommendations
# ─────────────────────────────────────────
def generate_recommendations(user_id: str, limit: int = 10) -> list:
    """
    Full pipeline:
    1. Fetch user
    2. Get scores from all 4 sources
    3. Blend scores
    4. Sort by final score
    5. Save to recommendations table
    6. Return top N results

    Returns: list of dicts [{"item_id": ..., "score": ...}]
    """

    # Step 1 — get the user's region for regional trending
    user = User.query.filter_by(user_id=user_id).first()
    region = user.region if user else None

    # Step 2 — collect scores from all sources
    history_scores       = get_history_scores(user_id)
    collaborative_scores = get_collaborative_scores(user_id)
    regional_scores      = get_regional_scores(region)
    global_scores        = get_global_scores()

    # Step 3 — blend into one final score per item
    blended = blend_scores(
        history_scores,
        collaborative_scores,
        regional_scores,
        global_scores
    )

    if not blended:
        return []

    # Step 4 — sort descending by score, take top N
    sorted_items = sorted(blended.items(), key=lambda x: x[1], reverse=True)[:limit]

    # Step 5 — save to database (replace old recommendations for this user)
    Recommendation.query.filter_by(user_id=user_id).delete()

    for item_id, score in sorted_items:
        rec = Recommendation(
            user_id=user_id,
            item_id=item_id,
            score=score,
            generated_at=datetime.utcnow()
        )
        db.session.add(rec)

    db.session.commit()

    # Step 6 — return as list of dicts
    return [{"item_id": item_id, "score": score} for item_id, score in sorted_items]