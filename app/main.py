from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.loaders import normalize_yelp, load_all_businesses, get_user_history
from app.task_a import simulate_review, simulate_review_cold_start
from app.task_b import recommend_items, recommend_cold_start, recommend_cross_domain
import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ── App Setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="BCT Hackathon — LLM User Modeling & Recommendation API",
    description="An agentic system that understands users deeply enough to simulate their reviews and deliver personalized recommendations.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/ui")
def serve_ui():
    return FileResponse("app/static/index.html")

# ── Data Loading ───────────────────────────────────────────────────────────────
# Load dataset once at startup so every request doesn't reload from disk

# DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DATA_DIR = Path(os.getenv("DATA_DIR", "./data/dataset"))

print("Loading Yelp dataset into memory...")
try:

    BUSINESSES_YELP, USERS, REVIEWS = normalize_yelp(DATA_DIR)
    BUSINESSES = load_all_businesses(DATA_DIR, BUSINESSES_YELP)
    print(f"Loaded {len(BUSINESSES)} businesses, {len(USERS)} users, {len(REVIEWS)} reviews")
except Exception as e:
    print(f"Warning: Could not load dataset: {e}")
    print("API will still run but data-dependent endpoints will fail.")
    BUSINESSES, USERS, REVIEWS = {}, {}, []


# ── Request Models ─────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    user_id: str
    item: dict  # must have item_name, item_category, optional item_description


class ReviewColdStartRequest(BaseModel):
    persona: dict  # description, preferences
    item: dict     # item_name, item_category, optional item_description


class RecommendRequest(BaseModel):
    user_id: str
    top_n: Optional[int] = 5


class RecommendColdStartRequest(BaseModel):
    persona: dict       # description, preferences, context
    top_n: Optional[int] = 5


class RecommendCrossRequest(BaseModel):
    user_id: str
    target_category: str
    top_n: Optional[int] = 5


# ── Health Check ───────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status": "running",
        "dataset_loaded": len(REVIEWS) > 0,
        "businesses": len(BUSINESSES),
        "users": len(USERS),
        "reviews": len(REVIEWS),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Task A Endpoints ───────────────────────────────────────────────────────────

@app.post("/task-a/simulate-review")
def simulate_review_endpoint(request: ReviewRequest):
    """
    Task A — Main endpoint.
    Takes a user_id and an unseen item.
    Returns simulated review and rating based on user history.
    """
    user_history = get_user_history(request.user_id, REVIEWS, BUSINESSES)

    if not user_history:
        raise HTTPException(
            status_code=404,
            detail=f"No review history found for user_id: {request.user_id}. Use /task-a/simulate-review/cold-start instead."
        )

    result = simulate_review(user_history, request.item)
    result["user_id"] = request.user_id
    result["history_size"] = len(user_history)
    return result


@app.post("/task-a/simulate-review/cold-start")
def simulate_review_cold_start_endpoint(request: ReviewColdStartRequest):
    """
    Task A — Cold start variant.
    No user history available. Works from a described persona instead.
    """
    result = simulate_review_cold_start(request.item, request.persona)
    return result


# ── Task B Endpoints ───────────────────────────────────────────────────────────

@app.post("/task-b/recommend")
def recommend_endpoint(request: RecommendRequest):
    """
    Task B — Main endpoint.
    Takes a user_id and returns personalized recommendations
    from the loaded dataset.
    """
    user_history = get_user_history(request.user_id, REVIEWS, BUSINESSES)

    if not user_history:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for user_id: {request.user_id}. Use /task-b/recommend/cold-start instead."
        )

    # Build item pool from businesses user hasn't reviewed yet
    reviewed_ids = {r["item_id"] for r in user_history}
    available_items = [
        b for bid, b in BUSINESSES.items()
        if bid not in reviewed_ids
    ]

    # Sample to keep things fast - no need to pass 50k businesses to LLM
    import random
    item_pool = random.sample(available_items, min(100, len(available_items)))

    result = recommend_items(user_history, item_pool, request.top_n)
    result["user_id"] = request.user_id
    result["history_size"] = len(user_history)
    return result


@app.post("/task-b/recommend/cold-start")
def recommend_cold_start_endpoint(request: RecommendColdStartRequest):
    """
    Task B — Cold start variant.
    No user history. Works from a described persona and context.
    """
    import random
    item_pool = random.sample(
        list(BUSINESSES.values()),
        min(50, len(BUSINESSES))
    )

    result = recommend_cold_start(request.persona, item_pool, request.top_n)
    return result


@app.post("/task-b/recommend/cross-domain")
def recommend_cross_domain_endpoint(request: RecommendCrossRequest):
    """
    Task B — Cross domain variant.
    User has history in one category but wants recommendations
    in a completely different domain.
    """
    user_history = get_user_history(request.user_id, REVIEWS, BUSINESSES)

    if not user_history:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for user_id: {request.user_id}."
        )


    # Filter businesses to target category only
    target_items = [
        b for b in BUSINESSES.values()
        if request.target_category.lower() in (b.get("item_category") or "").lower()
    ]

    if not target_items:
        raise HTTPException(
            status_code=404,
            detail=f"No businesses found in category: {request.target_category}"
        )

    import random
    item_pool = random.sample(target_items, min(30, len(target_items)))

    result = recommend_cross_domain(
        user_history,
        request.target_category,
        item_pool,
        request.top_n
    )
    result["user_id"] = request.user_id
    return result


# ── User Lookup Utility ────────────────────────────────────────────────────────

@app.get("/users/{user_id}/history")
def get_user_history_endpoint(user_id: str, limit: int = 10):
    """
    Utility endpoint — inspect a user's review history.
    Useful for testing and for judges to verify the system works.
    """
    history = get_user_history(user_id, REVIEWS, BUSINESSES, limit=limit)
    if not history:
        raise HTTPException(status_code=404, detail="User not found or no history.")
    return {
        "user_id": user_id,
        "history_count": len(history),
        "history": history
    }


@app.get("/businesses/sample")
def sample_businesses(limit: int = 10, category: Optional[str] = None):
    """
    Utility endpoint — browse available businesses.
    Useful for finding item inputs to test Task A and B.
    """
    import random
    businesses = list(BUSINESSES.values())

    if category:
        businesses = [
            b for b in businesses
            # if category.lower() in b.get("item_category", "").lower()
            if category.lower() in (b.get("item_category") or "").lower()
        ]

    sample = random.sample(businesses, min(limit, len(businesses)))
    return {"count": len(sample), "businesses": sample}

@app.get("/sample-users")
def get_sample_users():
    """
    Returns a curated list of real users from the dataset for the UI dropdown.
    Picks users with varied review counts and rating patterns.
    """
    from collections import Counter
    import random

    # Count reviews per user
    user_review_counts = Counter(r["user_id"] for r in REVIEWS)
    
    # Get users with at least 5 reviews
    eligible = [(uid, cnt) for uid, cnt in user_review_counts.items() if cnt >= 5]
    
    if not eligible:
        return {"users": []}

    # Sort by count descending, take top 50, then sample 8 for variety
    eligible.sort(key=lambda x: -x[1])
    pool = eligible[:50]
    selected = random.sample(pool, min(8, len(pool)))

    result = []
    for uid, cnt in selected:
        # Get their reviews to compute avg rating
        user_reviews = [r for r in REVIEWS if r["user_id"] == uid]
        avg = round(sum(r["rating"] for r in user_reviews) / len(user_reviews), 1)
        
        # Get their top categories
        cats = []
        for r in user_reviews:
            b = BUSINESSES.get(r["item_id"], {})
            cat = b.get("item_category", "")
            if cat:
                cats.extend([c.strip() for c in cat.split(",")][:2])
        from collections import Counter as C
        top_cats = ", ".join([c for c, _ in C(cats).most_common(2)])

        # Build a descriptive label
        tendency = "Generous" if avg >= 4.0 else "Harsh Critic" if avg <= 2.5 else "Balanced Reviewer"
        label = f"{tendency} — {avg}★ avg, {cnt} reviews"

        result.append({
            "user_id": uid,
            "label": label,
            "avg_rating": avg,
            "review_count": cnt,
            "top_cats": top_cats or "Various"
        })

    # Sort by avg rating for nice variety in the dropdown
    result.sort(key=lambda x: x["avg_rating"])
    return {"users": result}