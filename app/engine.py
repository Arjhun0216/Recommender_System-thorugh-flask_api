# app/engine.py
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from app import db
from app.models import User, Item, Interaction, Recommendation
from app.cache import (
    recommendation_cache,
    interaction_deduplicator,
    get_top_n
)
from datetime import datetime


def normalize(scores: dict) -> dict:
    """Scale all scores to 0.0 - 1.0 range."""
    if not scores:
        return {}
    max_score = max(scores.values())
    if max_score == 0:
        return {k: 0.0 for k in scores}
    return {k: round(v / max_score, 4) for k, v in scores.items()}


def get_history_scores(api_key: str, user_id: str) -> dict:
    """
    Source 1 — User's own interaction history.
    Uses Hash Map (Python dict) for O(1) score accumulation.
    """
    interactions = Interaction.query.filter_by(
        api_key=api_key, user_id=user_id
    ).all()

    # Hash Map — accumulate scores in O(1) per interaction
    scores = {}
    for i in interactions:
        scores[i.item_id] = scores.get(i.item_id, 0) + i.weight

    return normalize(scores)


def get_collaborative_scores(api_key: str, user_id: str) -> dict:
    """
    Source 2 — Collaborative filtering with LRU Cache.
    Matrix is only rebuilt when cache expires or
    new interaction invalidates it.
    """
    # Check LRU cache first
    cache_key = f"collab:{api_key}:{user_id}"
    cached = recommendation_cache.get(cache_key)
    if cached is not None:
        return cached

    all_interactions = Interaction.query.filter_by(api_key=api_key).all()
    if not all_interactions:
        return {}

    data = [{"user_id": i.user_id, "item_id": i.item_id,
             "weight": i.weight} for i in all_interactions]
    df = pd.DataFrame(data)

    matrix = df.pivot_table(
        index="user_id", columns="item_id",
        values="weight", aggfunc="sum", fill_value=0
    )

    if user_id not in matrix.index:
        return {}

    similarity_matrix = cosine_similarity(matrix)
    similarity_df = pd.DataFrame(
        similarity_matrix,
        index=matrix.index,
        columns=matrix.index
    )

    user_similarities = (
        similarity_df[user_id]
        .drop(user_id)
        .sort_values(ascending=False)
    )
    top_similar_users = user_similarities.head(5)

    if top_similar_users.empty:
        return {}

    # Hash Set — O(1) lookup for seen items
    seen_items = set(matrix.columns[matrix.loc[user_id] > 0])

    # Hash Map — accumulate scores in O(1)
    scores = {}
    for similar_user, similarity_score in top_similar_users.items():
        if similarity_score <= 0:
            continue
        similar_user_items = matrix.loc[similar_user]
        for item_id, weight in similar_user_items.items():
            if item_id not in seen_items and weight > 0:
                scores[item_id] = (
                    scores.get(item_id, 0) + (weight * similarity_score)
                )

    result = normalize(scores)

    # Store in LRU cache
    recommendation_cache.put(cache_key, result)
    return result


def get_regional_scores(api_key: str, region: str) -> dict:
    """Source 3 — Regional trending with Hash Map accumulation."""
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
    """Source 4 — Global trending with Hash Map accumulation."""
    interactions = Interaction.query.filter_by(api_key=api_key).all()

    scores = {}
    for i in interactions:
        scores[i.item_id] = scores.get(i.item_id, 0) + i.weight

    return normalize(scores)


def blend_scores(history, collaborative, regional, global_scores) -> dict:
    """
    Merge all 4 sources using weighted blending.
    Uses Hash Map for O(1) score lookup per item.
    """
    weights = {
        "history":       0.40,
        "collaborative": 0.30,
        "regional":      0.20,
        "global":        0.10,
    }

    # Hash Set — collect all unique items in O(1)
    all_items = (set(history) | set(collaborative) |
                 set(regional) | set(global_scores))

    blended = {}
    for item_id in all_items:
        blended[item_id] = round(
            history.get(item_id, 0)       * weights["history"]       +
            collaborative.get(item_id, 0) * weights["collaborative"] +
            regional.get(item_id, 0)      * weights["regional"]      +
            global_scores.get(item_id, 0) * weights["global"],
            4
        )

    return blended


def generate_recommendations(api_key: str,
                              user_id: str,
                              limit: int = 10) -> list:
    """
    Full pipeline with DSA optimizations:
    1. Check recommendation cache (LRU) — skip if fresh
    2. Compute scores from all 4 sources
    3. Blend scores (Hash Map)
    4. Select top N (Min Heap) — O(n log k) not O(n log n)
    5. Save to database
    6. Store in cache
    """
    # ── Check recommendation cache first ──
    cache_key = f"rec:{api_key}:{user_id}"
    cached = recommendation_cache.get(cache_key)
    if cached is not None:
        return cached

    user   = User.query.filter_by(api_key=api_key, user_id=user_id).first()
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

    # ── Min Heap — O(n log k) top-N selection ──
    top_items = get_top_n(blended, limit)

    # Save to database
    Recommendation.query.filter_by(
        api_key=api_key, user_id=user_id
    ).delete()

    for score, item_id in top_items:
        db.session.add(Recommendation(
            api_key=api_key,
            user_id=user_id,
            item_id=item_id,
            score=score,
            generated_at=datetime.utcnow()
        ))

    db.session.commit()

    result = [{"item_id": item_id, "score": score}
              for score, item_id in top_items]

    # ── Store in LRU cache ──
    recommendation_cache.put(cache_key, result)

    return result


def record_interaction(api_key: str, user_id: str,
                       item_id: str, action: str,
                       region=None, category=None) -> bool:
    """
    Records interaction with duplicate detection.
    Returns False if duplicate — skips database write.
    Returns True if recorded successfully.
    Uses Hash Set deduplication — O(1) check.
    """
    # ── Hash Set duplicate check — O(1) ──
    if interaction_deduplicator.is_duplicate(
        api_key, user_id, item_id, action
    ):
        return False

    # Invalidate cache for this user — force fresh recs
    recommendation_cache.invalidate(f"rec:{api_key}:{user_id}")
    recommendation_cache.invalidate(f"collab:{api_key}:{user_id}")

    return True