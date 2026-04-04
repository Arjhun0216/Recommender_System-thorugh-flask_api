# app/engine.py
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app import db
from app.models import User, Item, Interaction, Recommendation
from datetime import datetime


def normalize(scores: dict) -> dict:
    if not scores:
        return {}
    max_score = max(scores.values())
    if max_score == 0:
        return {k: 0.0 for k in scores}
    return {k: round(v / max_score, 4) for k, v in scores.items()}


def get_history_scores(api_key: str, user_id: str) -> dict:
    interactions = Interaction.query.filter_by(
        api_key=api_key, user_id=user_id
    ).all()

    scores = {}
    for i in interactions:
        scores[i.item_id] = scores.get(i.item_id, 0) + i.weight
    return normalize(scores)


def get_collaborative_scores(api_key: str, user_id: str) -> dict:
    # Only pull interactions belonging to THIS developer
    all_interactions = Interaction.query.filter_by(api_key=api_key).all()

    if not all_interactions:
        return {}

    data = [{"user_id": i.user_id, "item_id": i.item_id, "weight": i.weight}
            for i in all_interactions]
    df = pd.DataFrame(data)

    matrix = df.pivot_table(
        index="user_id",
        columns="item_id",
        values="weight",
        aggfunc="sum",
        fill_value=0
    )

    if user_id not in matrix.index:
        return {}

    similarity_matrix = cosine_similarity(matrix)
    similarity_df = pd.DataFrame(
        similarity_matrix,
        index=matrix.index,
        columns=matrix.index
    )

    user_similarities = similarity_df[user_id].drop(user_id).sort_values(ascending=False)
    top_similar_users = user_similarities.head(5)

    if top_similar_users.empty:
        return {}

    seen_items = set(matrix.columns[matrix.loc[user_id] > 0])

    scores = {}
    for similar_user, similarity_score in top_similar_users.items():
        if similarity_score <= 0:
            continue
        similar_user_items = matrix.loc[similar_user]
        for item_id, weight in similar_user_items.items():
            if item_id not in seen_items and weight > 0:
                scores[item_id] = scores.get(item_id, 0) + (weight * similarity_score)

    return normalize(scores)


def get_regional_scores(api_key: str, region: str) -> dict:
    if not region:
        return {}

    interactions = Interaction.query.filter_by(
        api_key=api_key, region=region
    ).all()

    scores = {}
    for i in interactions:
        scores[i.item_id] = scores.get(i.item_id, 0) + i.weight
    return normalize(scores)


def get_global_scores(api_key: str) -> dict:
    interactions = Interaction.query.filter_by(api_key=api_key).all()

    scores = {}
    for i in interactions:
        scores[i.item_id] = scores.get(i.item_id, 0) + i.weight
    return normalize(scores)


def blend_scores(history, collaborative, regional, global_scores) -> dict:
    weights = {
        "history":       0.40,
        "collaborative": 0.30,
        "regional":      0.20,
        "global":        0.10,
    }

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


def generate_recommendations(api_key: str, user_id: str, limit: int = 10) -> list:
    user = User.query.filter_by(api_key=api_key, user_id=user_id).first()
    region = user.region if user else None

    history_scores       = get_history_scores(api_key, user_id)
    collaborative_scores = get_collaborative_scores(api_key, user_id)
    regional_scores      = get_regional_scores(api_key, region)
    global_scores        = get_global_scores(api_key)

    blended = blend_scores(
        history_scores,
        collaborative_scores,
        regional_scores,
        global_scores
    )

    if not blended:
        return []

    sorted_items = sorted(blended.items(), key=lambda x: x[1], reverse=True)[:limit]

    # Replace old recommendations for this user under this api_key
    Recommendation.query.filter_by(api_key=api_key, user_id=user_id).delete()

    for item_id, score in sorted_items:
        rec = Recommendation(
            api_key=api_key,
            user_id=user_id,
            item_id=item_id,
            score=score,
            generated_at=datetime.utcnow()
        )
        db.session.add(rec)

    db.session.commit()

    return [{"item_id": item_id, "score": score} for item_id, score in sorted_items]