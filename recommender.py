"""
PFEFLIX Hybrid Recommendation Engine
=====================================
Combines Content-Based Filtering (CBF) and Collaborative Filtering (CF)
into a weighted hybrid that degrades gracefully to pure CBF when user
rating data is too sparse.

Entry point for Django views:
    from recommender import recommend_for_user
    titles = recommend_for_user(user_id=request.user.id, n=10)

Caching strategy (Django cache framework):
    - CBF matrix (content_df + tfidf_matrix): 6 hours  — content rarely changes
    - Ratings + CF model (ratings_df + predicted_df): 15 minutes — ratings change often
    - Per-user recommendations: 30 minutes — busted on new rating or preference save
"""

import os
import django
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import MinMaxScaler

# ── Django setup (safe to call multiple times) ───────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PFE.settings")
django.setup()

from core.models import Content, Rating  # noqa: E402

# ── Cache keys and timeouts ──────────────────────────────────────────────────
CACHE_CBF_KEY      = "pfeflix_cbf"
CACHE_RATINGS_KEY  = "pfeflix_ratings"
CACHE_REC_PREFIX   = "pfeflix_rec_"

CACHE_CBF_TIMEOUT      = 6 * 3600   # 6 hours  — content data rarely changes
CACHE_RATINGS_TIMEOUT  = 15 * 60    # 15 mins  — new ratings should propagate quickly
CACHE_REC_TIMEOUT      = 30 * 60    # 30 mins  — per-user results


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_content_df():
    """Load all Content rows from the DB into a DataFrame."""
    qs = Content.objects.values(
        "id", "title", "genres", "cast", "director", "description",
        "type", "platform", "release_year", "rating", "duration_minutes"
    )
    df = pd.DataFrame.from_records(qs)
    if df.empty:
        return df
    for col in ["genres", "cast", "director", "description"]:
        df[col] = df[col].fillna("")
    df = df.reset_index(drop=True)
    return df


def load_ratings_df():
    """Load all Rating rows from the DB into a DataFrame."""
    qs = Rating.objects.values("user_id", "title", "score")
    return pd.DataFrame.from_records(qs)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — CACHED DATA ACCESSORS
# ─────────────────────────────────────────────────────────────────────────────

def get_cbf_data():
    """
    Return (content_df, tfidf_matrix), building and caching them if needed.
    Cache lifetime: 6 hours (CACHE_CBF_TIMEOUT).
    """
    from django.core.cache import cache

    try:
        cached = cache.get(CACHE_CBF_KEY)
    except Exception:
        cached = None

    if cached is not None:
        return cached

    content_df = load_content_df()
    if content_df.empty:
        return content_df, None

    tfidf_matrix, _ = build_cbf_matrix(content_df)

    try:
        cache.set(CACHE_CBF_KEY, (content_df, tfidf_matrix), CACHE_CBF_TIMEOUT)
    except Exception:
        pass  # caching is best-effort; never crash because of it

    return content_df, tfidf_matrix


def get_cf_data():
    """
    Return (ratings_df, predicted_df, cf_valid), building and caching if needed.
    Cache lifetime: 15 minutes (CACHE_RATINGS_TIMEOUT).
    """
    from django.core.cache import cache

    try:
        cached = cache.get(CACHE_RATINGS_KEY)
    except Exception:
        cached = None

    if cached is not None:
        return cached

    ratings_df = load_ratings_df()
    predicted_df, cf_valid = build_cf_model(ratings_df)
    result = (ratings_df, predicted_df, cf_valid)

    try:
        cache.set(CACHE_RATINGS_KEY, result, CACHE_RATINGS_TIMEOUT)
    except Exception:
        pass

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — CONTENT-BASED FILTERING (CBF)
# ─────────────────────────────────────────────────────────────────────────────

def build_soup(row):
    """
    Combine metadata fields into a single text 'soup' for TF-IDF.
    Director and cast are repeated to give them extra weight.
    """
    director = " ".join(row["director"].split(",")[:1])
    cast_top = " ".join(row["cast"].split(",")[:5])
    genres   = row["genres"].replace(",", " ")
    desc     = row["description"]
    return f"{genres} {director} {director} {cast_top} {cast_top} {desc}"


def build_cbf_matrix(content_df):
    """
    Build a TF-IDF matrix over all Content items.
    Returns (tfidf_matrix, vectorizer).
    """
    content_df = content_df.copy()
    content_df["soup"] = content_df.apply(build_soup, axis=1)
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=10_000,
        ngram_range=(1, 2),
        min_df=1,
    )
    tfidf_matrix = vectorizer.fit_transform(content_df["soup"])
    return tfidf_matrix, vectorizer


def cbf_scores_for_user(user_id, content_df, tfidf_matrix, ratings_df):
    """
    Compute a CBF score for every Content item for this user.
    Returns a numpy array of shape (n_content,) with scores in [0, 1].
    """
    n = len(content_df)
    user_ratings = ratings_df[ratings_df["user_id"] == user_id]
    liked = user_ratings[user_ratings["score"] >= 3.0]

    if liked.empty:
        return np.zeros(n)

    title_to_pos = {title: pos for pos, title in enumerate(content_df["title"])}

    liked_indices = []
    liked_weights = []
    for _, row in liked.iterrows():
        if row["title"] in title_to_pos:
            liked_indices.append(int(title_to_pos[row["title"]]))
            liked_weights.append(float(row["score"]))

    if not liked_indices:
        return np.zeros(n)

    weights = np.array(liked_weights, dtype=float)
    weights /= weights.sum()
    user_profile = np.asarray(
        tfidf_matrix[liked_indices].multiply(weights[:, None]).sum(axis=0)
    )

    scores = cosine_similarity(user_profile, tfidf_matrix).flatten()

    all_rated_titles = set(user_ratings["title"].tolist())
    for i, title in enumerate(content_df["title"]):
        if title in all_rated_titles:
            scores[i] = 0.0

    return scores


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — COLLABORATIVE FILTERING (CF) via SVD
# ─────────────────────────────────────────────────────────────────────────────

CF_MIN_USERS   = 5
CF_MIN_RATINGS = 20
SVD_COMPONENTS = 20


def build_cf_model(ratings_df):
    """
    Build an SVD-based CF model from the ratings DataFrame.
    Returns (predicted_df, is_valid).
    """
    if ratings_df.empty:
        return None, False

    n_users   = ratings_df["user_id"].nunique()
    n_ratings = len(ratings_df)

    if n_users < CF_MIN_USERS or n_ratings < CF_MIN_RATINGS:
        return None, False

    matrix = ratings_df.pivot_table(
        index="user_id", columns="title", values="score", aggfunc="mean"
    )
    matrix_filled = matrix.apply(lambda col: col.fillna(col.mean()), axis=0)
    matrix_filled = matrix_filled.fillna(0)

    n_components = min(SVD_COMPONENTS, min(matrix_filled.shape) - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=42)
    U  = svd.fit_transform(matrix_filled)
    Vt = svd.components_
    predicted = np.dot(U, Vt)

    predicted_df = pd.DataFrame(
        predicted,
        index=matrix_filled.index,
        columns=matrix_filled.columns,
    )
    return predicted_df, True


def cf_scores_for_user(user_id, content_df, predicted_df, ratings_df):
    """
    Extract CF predicted scores for this user across all Content items.
    Returns a numpy array of shape (n_content,) with scores in [0, 1].
    """
    n = len(content_df)

    if predicted_df is None or user_id not in predicted_df.index:
        return np.zeros(n)

    user_row = predicted_df.loc[user_id]
    scores = np.zeros(n)
    for i, title in enumerate(content_df["title"]):
        if title in user_row.index:
            scores[i] = float(user_row[title])

    user_ratings  = ratings_df[ratings_df["user_id"] == user_id]
    rated_titles  = set(user_ratings["title"].tolist())
    for i, title in enumerate(content_df["title"]):
        if title in rated_titles:
            scores[i] = 0.0

    return scores


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — HYBRID BLENDING
# ─────────────────────────────────────────────────────────────────────────────

CBF_WEIGHT = 0.4
CF_WEIGHT  = 0.6


def blend_scores(cbf_scores, cf_scores, cf_valid):
    """
    Normalise both score arrays to [0, 1] and blend them.
    Falls back to pure CBF if CF is not valid.
    """
    scaler = MinMaxScaler()

    def safe_normalize(arr):
        if arr.max() == arr.min():
            return arr
        return scaler.fit_transform(arr.reshape(-1, 1)).flatten()

    cbf_norm = safe_normalize(cbf_scores)

    if cf_valid and cf_scores.max() > 0:
        cf_norm = safe_normalize(cf_scores)
        return CBF_WEIGHT * cbf_norm + CF_WEIGHT * cf_norm
    else:
        return cbf_norm


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — USER PREFERENCE BOOST
# ─────────────────────────────────────────────────────────────────────────────

def apply_preference_boost(hybrid_scores, content_df, user_id):
    """
    Boost scores for items matching the user's saved preferences.
    Additive so it nudges but does not override the model.
    """
    try:
        from core.models import UserPreference
        pref = UserPreference.objects.get(user_id=user_id)
    except Exception:
        return hybrid_scores

    boosted = hybrid_scores.copy()

    pref_genres   = [g.strip().lower() for g in pref.genres.split(",") if g.strip()]
    pref_type     = pref.content_type.strip().lower()
    pref_platform = pref.platform.strip().lower()

    for i, row in content_df.iterrows():
        boost = 0.0
        item_genres = row["genres"].lower()
        if any(g in item_genres for g in pref_genres):
            boost += 0.1
        if pref_type and pref_type in row["type"].lower():
            boost += 0.05
        if pref_platform and pref_platform in row["platform"].lower():
            boost += 0.05
        boosted[i] += boost

    return boosted


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def recommend_for_user(user_id, n=10):
    """
    Return the top-n recommended Content objects for the given user_id.

    Usage in a Django view:
        from recommender import recommend_for_user
        recommendations = recommend_for_user(request.user.id, n=10)

    Cold-start behaviour:
        - If the user has no ratings, falls back to top-rated popular content.
        - If CF data is insufficient, runs pure CBF.

    Caching:
        - Per-user results are cached for 30 minutes.
        - Cache is invalidated by views.py when the user saves a rating
          or updates their preferences.
    """
    from django.core.cache import cache

    # ── Per-user result cache ─────────────────────────────────────────────────
    rec_key = f"{CACHE_REC_PREFIX}{user_id}"
    try:
        cached_recs = cache.get(rec_key)
    except Exception:
        cached_recs = None

    if cached_recs is not None:
        return cached_recs

    # ── Load data (both use their own cache layers) ───────────────────────────
    content_df, tfidf_matrix = get_cbf_data()
    if content_df.empty or tfidf_matrix is None:
        return []

    ratings_df, predicted_df, cf_valid = get_cf_data()

    # ── CBF ───────────────────────────────────────────────────────────────────
    cbf_scores = cbf_scores_for_user(user_id, content_df, tfidf_matrix, ratings_df)

    # ── CF ────────────────────────────────────────────────────────────────────
    cf_scores = cf_scores_for_user(user_id, content_df, predicted_df, ratings_df)

    # ── Hybrid blend ──────────────────────────────────────────────────────────
    hybrid_scores = blend_scores(cbf_scores, cf_scores, cf_valid)

    # ── Preference boost ──────────────────────────────────────────────────────
    hybrid_scores = apply_preference_boost(hybrid_scores, content_df, user_id)

    # ── Cold-start fallback ───────────────────────────────────────────────────
    if hybrid_scores.max() == 0:
        popular_titles = (
            ratings_df.groupby("title")["score"]
            .agg(["mean", "count"])
            .query("count >= 2")
            .sort_values("mean", ascending=False)
            .index.tolist()
        )
        if popular_titles:
            mask = content_df["title"].isin(popular_titles[: n * 3])
            fallback_ids = content_df[mask]["id"].tolist()[:n]
        else:
            fallback_ids = content_df["id"].tolist()[:n]
        results = list(Content.objects.filter(id__in=fallback_ids))
        try:
            cache.set(rec_key, results, CACHE_REC_TIMEOUT)
        except Exception:
            pass
        return results

    # ── Pick top-n ────────────────────────────────────────────────────────────
    top_indices = np.argsort(hybrid_scores)[::-1][:n]
    top_ids = content_df.iloc[top_indices]["id"].tolist()

    content_map = {c.id: c for c in Content.objects.filter(id__in=top_ids)}
    results = [content_map[cid] for cid in top_ids if cid in content_map]

    # ── Cache results ─────────────────────────────────────────────────────────
    try:
        cache.set(rec_key, results, CACHE_REC_TIMEOUT)
    except Exception:
        pass

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — QUICK TEST (run directly: python recommender.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    uid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"\n🎬 Recommendations for user_id={uid}:\n")
    results = recommend_for_user(uid, n=10)
    if not results:
        print("  No recommendations returned.")
    for i, item in enumerate(results, 1):
        print(f"  {i:2}. {item.title} ({item.type} | {item.genres})")