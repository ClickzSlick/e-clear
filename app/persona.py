# from app.llm import call_llm
# import json


# def build_persona(user_history: list) -> dict:
#     """
#     Takes a user's review history and extracts a structured persona.
#     This persona drives both Task A and Task B.
#     """
#     if not user_history:
#         return _default_persona()

#     # Calculate basic stats from history
#     ratings = [r["rating"] for r in user_history]
#     avg_rating = sum(ratings) / len(ratings)
#     rating_distribution = {
#         "5_star": ratings.count(5),
#         "4_star": ratings.count(4),
#         "3_star": ratings.count(3),
#         "2_star": ratings.count(2),
#         "1_star": ratings.count(1),
#     }

#     # Extract categories they visit
#     categories = []
#     for r in user_history:
#         if r.get("item_category"):
#             cats = [c.strip() for c in r["item_category"].split(",")]
#             categories.extend(cats)

#     top_categories = list(set(categories))[:10]

#     # Average review length tells us if they're detailed or brief
#     avg_review_length = sum(len(r["review_text"]) for r in user_history) / len(user_history)

#     # Build a sample of their actual reviews for the LLM to read
#     sample_reviews = []
#     for r in user_history[:5]:  # take 5 most recent
#         sample_reviews.append({
#             "place": r["item_name"],
#             "category": r["item_category"],
#             "rating": r["rating"],
#             "review": r["review_text"][:300],  # trim long reviews
#         })

#     # Now ask the LLM to extract deeper behavioral patterns
#     prompt = f"""
# You are analyzing a user's review history to build a behavioral persona.

# Here are their recent reviews:
# {json.dumps(sample_reviews, indent=2)}

# Their stats:
# - Average rating they give: {avg_rating:.1f} out of 5
# - Rating breakdown: {json.dumps(rating_distribution)}
# - Categories they frequent: {", ".join(top_categories)}
# - Average review length: {int(avg_review_length)} characters

# Extract a persona in this exact JSON format and return ONLY the JSON, nothing else:
# {{
#     "rating_tendency": "harsh|balanced|generous",
#     "writing_style": "brief|moderate|detailed",
#     "tone": "formal|casual|humorous|emotional",
#     "key_priorities": ["list of 3 things this user cares about most e.g. service, value, quality"],
#     "common_complaints": ["list of 2-3 things they commonly complain about"],
#     "common_praises": ["list of 2-3 things they commonly praise"],
#     "personality_summary": "2 sentence summary of this reviewer's personality and standards"
# }}
# """

#     try:
#         response = call_llm(prompt, temperature=0.3)
#         # Clean response in case LLM adds markdown backticks
#         clean = response.strip().replace("```json", "").replace("```", "").strip()
#         persona_llm = json.loads(clean)
#     except Exception as e:
#         print(f"LLM persona extraction failed: {e}")
#         persona_llm = _default_persona_llm()

#     # Merge stats with LLM insights into one complete persona
#     persona = {
#         "avg_rating": round(avg_rating, 2),
#         "rating_distribution": rating_distribution,
#         "top_categories": top_categories,
#         "writing_style_length": "brief" if avg_review_length < 200 else "detailed" if avg_review_length > 500 else "moderate",
#         "review_count_in_history": len(user_history),
#         **persona_llm  # merge LLM extracted fields
#     }

#     return persona


# def build_nigerian_persona(user_history: list) -> dict:
#     """
#     Extends the base persona with Nigerian voice contextualization.
#     This is our differentiation angle for bonus marks.
#     """
#     base_persona = build_persona(user_history)

#     nigerian_context = """
# Nigerian reviewers typically:
# - Are direct and expressive, they do not sugarcoat
# - Use natural Nigerian English phrases without forcing it
# - Reference value for money strongly, they notice when they are being cheated
# - Are warm and appreciative when service genuinely impresses them
# - Use contrast naturally: acknowledge good before hitting the bad
# - May code-switch subtly, phrases like 'this place did not disappoint at all' or 'the service stress me small'
# - Judge food by taste, freshness, and portion size above everything else
# """

#     base_persona["nigerian_voice_context"] = nigerian_context
#     base_persona["contextualized"] = True

#     return base_persona


# def _default_persona() -> dict:
#     """Fallback when user has no history - cold start case"""
#     return {
#         "avg_rating": 3.5,
#         "rating_distribution": {},
#         "top_categories": [],
#         "writing_style_length": "moderate",
#         "review_count_in_history": 0,
#         **_default_persona_llm(),
#         "nigerian_voice_context": "",
#         "contextualized": False,
#     }


# def _default_persona_llm() -> dict:
#     return {
#         "rating_tendency": "balanced",
#         "writing_style": "moderate",
#         "tone": "casual",
#         "key_priorities": ["quality", "service", "value"],
#         "common_complaints": ["slow service", "poor value"],
#         "common_praises": ["good food", "friendly staff"],
#         "personality_summary": "A balanced reviewer with moderate standards."
#     }


import json
import statistics
from datetime import datetime
from app.llm import call_llm


# ── Helpers ────────────────────────────────────────────────────────────────────

def _recency_weight(date_str: str) -> float:
    """
    Returns a weight between 0.1 and 1.0 based on how recent the review is.
    Reviews decay in weight over ~3 years. More recent = more influential.
    """
    try:
        date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        days_ago = (datetime.now() - date).days
        return max(0.1, 1.0 - (days_ago / 1000))
    except Exception:
        return 0.5


def _sentiment_trend(sorted_history: list) -> str:
    """
    Compares avg rating in first half vs second half of history.
    Tells us if the user is becoming more positive, negative, or stable over time.
    """
    mid = len(sorted_history) // 2
    if mid == 0:
        return "stable"
    early_avg = sum(r["rating"] for r in sorted_history[:mid]) / mid
    recent_avg = sum(r["rating"] for r in sorted_history[mid:]) / (len(sorted_history) - mid)
    if recent_avg > early_avg + 0.3:
        return "improving"
    elif recent_avg < early_avg - 0.3:
        return "declining"
    return "stable"


# ── Core Persona Builder ───────────────────────────────────────────────────────

def build_persona(user_history: list) -> dict:
    """
    Takes a user's review history and extracts a structured persona.
    This persona drives both Task A and Task B.
    """
    if not user_history:
        return _default_persona()

    # Sort history by date for trend analysis
    sorted_history = sorted(user_history, key=lambda x: x.get("date", ""), reverse=False)

    # ── Rating stats ──
    ratings = [r["rating"] for r in user_history]
    avg_rating = sum(ratings) / len(ratings)

    # Recency-weighted average — recent behavior matters more
    weights = [_recency_weight(r.get("date", "")) for r in user_history]
    weighted_avg = sum(r["rating"] * w for r, w in zip(user_history, weights)) / sum(weights)

    rating_distribution = {
        "5_star": ratings.count(5),
        "4_star": ratings.count(4),
        "3_star": ratings.count(3),
        "2_star": ratings.count(2),
        "1_star": ratings.count(1),
    }

    # Rating consistency — low stdev = predictable rater, high = mood-dependent
    rating_consistency = round(statistics.stdev(ratings), 2) if len(ratings) > 1 else 0.0

    # ── Category analysis ──
    categories = []
    category_counts = {}
    for r in user_history:
        if r.get("item_category"):
            cats = [c.strip() for c in r["item_category"].split(",")]
            categories.extend(cats)
            for cat in cats:
                category_counts[cat] = category_counts.get(cat, 0) + 1

    top_categories = sorted(category_counts, key=category_counts.get, reverse=True)[:10]

    # Explorer vs loyal — does this person try new things or stick to what they know?
    max_visits = max(category_counts.values()) if category_counts else 1
    loyalty_score = max_visits / len(user_history)
    explorer_vs_loyal = "loyal" if loyalty_score > 0.4 else "explorer"

    # ── Review style ──
    avg_review_length = sum(len(r["review_text"]) for r in user_history) / len(user_history)
    writing_style_length = (
        "brief" if avg_review_length < 200
        else "detailed" if avg_review_length > 500
        else "moderate"
    )

    # ── Sentiment trend ──
    trend = _sentiment_trend(sorted_history)

    # ── Sample reviews for LLM ──
    sample_reviews = []
    for r in sorted_history[-5:]:  # 5 most recent
        sample_reviews.append({
            "place": r["item_name"],
            "category": r["item_category"],
            "rating": r["rating"],
            "review": r["review_text"][:300],
        })

    # ── LLM behavioral extraction ──
    prompt = f"""
You are analyzing a user's review history to build a behavioral persona.

Here are their recent reviews:
{json.dumps(sample_reviews, indent=2)}

Their stats:
- Simple average rating: {avg_rating:.1f} out of 5
- Recency-weighted average rating: {round(weighted_avg, 2)} out of 5
- Rating breakdown: {json.dumps(rating_distribution)}
- Rating consistency (stdev): {rating_consistency} (lower = more consistent)
- Categories they frequent: {", ".join(top_categories)}
- Average review length: {int(avg_review_length)} characters
- Behavior pattern: {explorer_vs_loyal} (do they try new things or stick to favorites)
- Sentiment trend over time: {trend} (are their ratings improving, declining, or stable)

Extract a persona in this exact JSON format and return ONLY the JSON, nothing else:
{{
    "rating_tendency": "harsh|balanced|generous",
    "writing_style": "brief|moderate|detailed",
    "tone": "formal|casual|humorous|emotional",
    "key_priorities": ["list of 3 things this user cares about most e.g. service, value, quality"],
    "common_complaints": ["list of 2-3 things they commonly complain about"],
    "common_praises": ["list of 2-3 things they commonly praise"],
    "personality_summary": "2 sentence summary of this reviewer's personality and standards"
}}
"""

    # try:
    #     response = call_llm(prompt, temperature=0.3)
    #     clean = response.strip().replace("```json", "").replace("```", "").strip()
    #     persona_llm = json.loads(clean)
    # except Exception as e:
    #     print(f"LLM persona extraction failed: {e}")
    #     persona_llm = _default_persona_llm()
    try:
        response = call_llm(prompt, temperature=0.3)
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        # Extract just the JSON object in case LLM adds text before/after
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        persona_llm = json.loads(clean)
    except Exception as e:
        print(f"LLM persona extraction failed: {e}")
        persona_llm = _default_persona_llm()

    # ── Merge everything ──
    persona = {
        "avg_rating": round(avg_rating, 2),
        "weighted_avg_rating": round(weighted_avg, 2),
        "rating_distribution": rating_distribution,
        "rating_consistency": rating_consistency,
        "top_categories": top_categories,
        "category_counts": category_counts,
        "explorer_vs_loyal": explorer_vs_loyal,
        "sentiment_trend": trend,
        "writing_style_length": writing_style_length,
        "review_count_in_history": len(user_history),
        **persona_llm,
    }

    return persona


# ── Nigerian Voice Layer ───────────────────────────────────────────────────────

def build_nigerian_persona(user_history: list) -> dict:
    """
    Extends the base persona with Nigerian voice contextualization.
    Unlike the old version which used a static string, this generates
    a dynamic voice context tailored to this specific user's patterns.
    """
    base_persona = build_persona(user_history)

    nigerian_prompt = f"""
You are helping an AI system write reviews that sound authentically Nigerian.

This specific user's behavioral profile:
- Rating tendency: {base_persona.get('rating_tendency', 'balanced')}
- Key priorities: {", ".join(base_persona.get('key_priorities', []))}
- Personality: {base_persona.get('personality_summary', '')}
- They commonly praise: {", ".join(base_persona.get('common_praises', []))}
- They commonly complain about: {", ".join(base_persona.get('common_complaints', []))}
- Behavior: {base_persona.get('explorer_vs_loyal', 'balanced')} — {'tries new places often' if base_persona.get('explorer_vs_loyal') == 'explorer' else 'sticks to trusted favorites'}
- Sentiment trend: {base_persona.get('sentiment_trend', 'stable')}

Write 3 sentences describing how THIS specific Nigerian user would express themselves
in a review. Describe their voice, what they would emphasize, what would make them
praise loudly or complain hard. Be specific to their rating tendency and priorities.

Reference natural Nigerian English patterns where appropriate:
- Direct and expressive, no sugarcoating
- Strong value-for-money awareness
- Warm appreciation when genuinely impressed
- Natural contrast: acknowledge good before hitting the bad
- Subtle code-switching where it fits their tone
"""

    try:
        dynamic_context = call_llm(nigerian_prompt, temperature=0.4)
        base_persona["nigerian_voice_context"] = dynamic_context.strip()
    except Exception as e:
        print(f"Nigerian voice context generation failed: {e}")
        base_persona["nigerian_voice_context"] = _static_nigerian_fallback()

    base_persona["contextualized"] = True
    return base_persona


# ── Fallbacks ──────────────────────────────────────────────────────────────────

def _default_persona() -> dict:
    """Fallback when user has no history — cold start case."""
    return {
        "avg_rating": 3.5,
        "weighted_avg_rating": 3.5,
        "rating_distribution": {},
        "rating_consistency": 0.0,
        "top_categories": [],
        "category_counts": {},
        "explorer_vs_loyal": "explorer",
        "sentiment_trend": "stable",
        "writing_style_length": "moderate",
        "review_count_in_history": 0,
        **_default_persona_llm(),
        "nigerian_voice_context": _static_nigerian_fallback(),
        "contextualized": False,
    }


def _default_persona_llm() -> dict:
    return {
        "rating_tendency": "balanced",
        "writing_style": "moderate",
        "tone": "casual",
        "key_priorities": ["quality", "service", "value"],
        "common_complaints": ["slow service", "poor value"],
        "common_praises": ["good food", "friendly staff"],
        "personality_summary": "A balanced reviewer with moderate standards."
    }


def _static_nigerian_fallback() -> str:
    return (
        "This Nigerian reviewer is direct and expressive — they do not sugarcoat. "
        "They notice value for money immediately and will call it out if they feel cheated. "
        "When genuinely impressed, they are warm and specific in their praise."
    )