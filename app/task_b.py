# from app.llm import call_llm
# from app.persona import build_nigerian_persona
# import json
# import random


# def recommend_items(user_history: list, available_items: list, top_n: int = 5) -> dict:
#     """
#     Given a user's review history and a pool of available items,
#     recommend the top N items they would most likely enjoy.

#     available_items is a list of dicts with:
#         - item_id: str
#         - item_name: str
#         - item_category: str
#         - item_description: str (optional)
#         - avg_rating: float (optional, overall rating from all users)
#     """

#     persona = build_nigerian_persona(user_history)

#     # Limit items sent to LLM to avoid token overflow
#     # Pick a smart subset - prioritize categories user already likes
#     filtered_items = _smart_filter(available_items, persona, limit=20)

#     prompt = f"""
# You are a personalized recommendation engine that thinks before recommending.

# HERE IS WHO YOU ARE RECOMMENDING FOR:
# - Average rating they give: {persona['avg_rating']} out of 5
# - Rating tendency: {persona['rating_tendency']}
# - They care most about: {", ".join(persona['key_priorities'])}
# - Categories they frequent: {", ".join(persona['top_categories'][:5])}
# - They commonly praise: {", ".join(persona['common_praises'])}
# - They commonly complain about: {", ".join(persona['common_complaints'])}
# - Personality: {persona['personality_summary']}

# VOICE CONTEXT:
# {persona.get('nigerian_voice_context', '')}

# AVAILABLE ITEMS TO RECOMMEND FROM:
# {json.dumps(filtered_items, indent=2)}

# YOUR TASK:
# 1. Think about what this specific person would enjoy based on their history
# 2. Pick the top {top_n} items from the list above
# 3. For each recommendation explain WHY it fits this person specifically
# 4. Do not give generic reasons. Tie each reason back to their actual preferences

# Return ONLY this JSON, nothing else:
# {{
#     "recommendations": [
#         {{
#             "item_id": "<id from the list>",
#             "item_name": "<name from the list>",
#             "item_category": "<category>",
#             "relevance_score": <float between 0 and 1, how confident you are>,
#             "reason": "<specific reason why THIS person would enjoy this, reference their history>"
#         }}
#     ],
#     "recommendation_reasoning": "<2-3 sentences explaining your overall recommendation strategy for this user>"
# }}
# """

#     try:
#         response = call_llm(prompt, temperature=0.5)
#         clean = response.strip().replace("```json", "").replace("```", "").strip()
#         result = json.loads(clean)

#         # Attach persona summary for transparency
#         result["persona_used"] = {
#             "avg_rating": persona["avg_rating"],
#             "top_categories": persona["top_categories"][:3],
#             "key_priorities": persona["key_priorities"],
#             "nigerian_contextualized": persona.get("contextualized", False)
#         }

#         return result

#     except Exception as e:
#         print(f"Recommendation failed: {e}")
#         return _fallback_recommendations(filtered_items, top_n)


# def recommend_cold_start(persona_input: dict, available_items: list, top_n: int = 5) -> dict:
#     """
#     Cold start version - no review history available.
#     Works from a described persona instead.

#     persona_input example:
#     {
#         "description": "A young Nigerian professional in Lagos",
#         "preferences": "Loves trying new cuisines, values ambience, mid-range budget",
#         "context": "Looking for a dinner spot for a first date"
#     }
#     """

#     filtered_items = available_items[:20]

#     prompt = f"""
# You are a personalized recommendation engine.

# WHO YOU ARE RECOMMENDING FOR:
# {persona_input.get('description', 'A new user with no history')}

# THEIR PREFERENCES:
# {persona_input.get('preferences', 'No preferences specified')}

# CURRENT CONTEXT:
# {persona_input.get('context', 'General recommendation')}

# VOICE CONTEXT:
# This person is Nigerian. Factor in Nigerian sensibilities around
# value for money, food quality, and social experience.

# AVAILABLE ITEMS:
# {json.dumps(filtered_items[:20], indent=2)}

# Recommend the top {top_n} items. Think carefully before choosing.
# Tie every reason back to their specific preferences and context.

# Return ONLY this JSON, nothing else:
# {{
#     "recommendations": [
#         {{
#             "item_id": "<id>",
#             "item_name": "<name>",
#             "item_category": "<category>",
#             "relevance_score": <float between 0 and 1>,
#             "reason": "<specific reason for this person>"
#         }}
#     ],
#     "recommendation_reasoning": "<2-3 sentences on your strategy>",
#     "cold_start": true
# }}
# """

#     try:
#         response = call_llm(prompt, temperature=0.5)
#         clean = response.strip().replace("```json", "").replace("```", "").strip()
#         result = json.loads(clean)
#         return result

#     except Exception as e:
#         print(f"Cold start recommendation failed: {e}")
#         return _fallback_recommendations(filtered_items, top_n)


# def recommend_cross_domain(user_history: list, target_category: str, available_items: list, top_n: int = 5) -> dict:
#     """
#     Cross-domain version - user has history in one category
#     but wants recommendations in a completely different one.

#     Example: user mostly reviews restaurants but wants book recommendations.
#     We transfer their behavioral patterns across domains.
#     """

#     persona = build_nigerian_persona(user_history)

#     prompt = f"""
# You are a cross-domain recommendation engine.

# The user has history in: {", ".join(persona['top_categories'][:3])}
# They now want recommendations in: {target_category}

# THE CHALLENGE:
# Transfer what you know about their personality and preferences
# into this new domain they have no history in.

# WHO THEY ARE:
# - Rating tendency: {persona['rating_tendency']}
# - They care most about: {", ".join(persona['key_priorities'])}
# - Personality: {persona['personality_summary']}
# - They praise: {", ".join(persona['common_praises'])}
# - They complain about: {", ".join(persona['common_complaints'])}

# VOICE CONTEXT:
# {persona.get('nigerian_voice_context', '')}

# AVAILABLE ITEMS IN TARGET CATEGORY:
# {json.dumps(available_items[:20], indent=2)}

# Think carefully:
# - A person who values service in restaurants likely values responsiveness in other domains
# - A person who complains about value for money will apply that lens everywhere
# - Transfer their core personality, not just their category preferences

# Return ONLY this JSON, nothing else:
# {{
#     "recommendations": [
#         {{
#             "item_id": "<id>",
#             "item_name": "<name>",
#             "item_category": "<category>",
#             "relevance_score": <float between 0 and 1>,
#             "reason": "<how this fits their personality transferred to new domain>"
#         }}
#     ],
#     "cross_domain_reasoning": "<explain how you transferred their preferences across domains>",
#     "source_domain": "{", ".join(persona['top_categories'][:2])}",
#     "target_domain": "{target_category}"
# }}
# """

#     try:
#         response = call_llm(prompt, temperature=0.5)
#         clean = response.strip().replace("```json", "").replace("```", "").strip()
#         result = json.loads(clean)
#         return result

#     except Exception as e:
#         print(f"Cross domain recommendation failed: {e}")
#         return _fallback_recommendations(available_items, top_n)


# def _smart_filter(items: list, persona: dict, limit: int = 20) -> list:
#     """
#     Before sending items to LLM, do a smart pre-filter.
#     Prioritize items in categories the user already likes.
#     This improves recommendation quality and reduces token usage.
#     """
#     top_cats = [c.lower() for c in persona.get("top_categories", [])]

#     preferred = []
#     others = []

#     for item in items:
#         # item_cats = item.get("item_category", "").lower()
#         item_cats = (item.get("item_category") or "").lower()
#         if any(cat in item_cats for cat in top_cats):
#             preferred.append(item)
#         else:
#             others.append(item)

#     # Fill up to limit with preferred first, then others
#     combined = preferred[:limit] + others[:max(0, limit - len(preferred))]
#     return combined[:limit]


# def _fallback_recommendations(items: list, top_n: int) -> dict:
#     """Safe fallback if LLM call fails"""
#     sample = random.sample(items, min(top_n, len(items)))
#     return {
#         "recommendations": [
#             {
#                 "item_id": item.get("item_id", ""),
#                 "item_name": item.get("item_name", "Unknown"),
#                 "item_category": item.get("item_category", ""),
#                 "relevance_score": 0.5,
#                 "reason": "Recommended based on general popularity."
#             }
#             for item in sample
#         ],
#         "recommendation_reasoning": "Fallback recommendations due to generation error.",
#         "error": True
#     }


import json
import random
from app.llm import call_llm
from app.persona import build_nigerian_persona


def recommend_items(user_history: list, available_items: list, top_n: int = 5) -> dict:
    """
    Given a user's review history and a pool of available items,
    recommend the top N items they would most likely enjoy.
    """
    persona = build_nigerian_persona(user_history)

    filtered_items = _smart_filter(available_items, persona, limit=20)

    prompt = f"""
You are a personalized recommendation engine that thinks before recommending.

HERE IS WHO YOU ARE RECOMMENDING FOR:
- Average rating they give: {persona['avg_rating']} out of 5
- Recency-weighted average: {persona.get('weighted_avg_rating', persona['avg_rating'])} out of 5
- Rating tendency: {persona['rating_tendency']}
- Rating consistency (stdev): {persona.get('rating_consistency', 'unknown')} (lower = more predictable)
- They care most about: {", ".join(persona['key_priorities'])}
- Categories they frequent: {", ".join(persona['top_categories'][:5])}
- Explorer vs loyal: {persona.get('explorer_vs_loyal', 'unknown')}
- Sentiment trend: {persona.get('sentiment_trend', 'stable')} (are their ratings improving or declining over time)
- They commonly praise: {", ".join(persona['common_praises'])}
- They commonly complain about: {", ".join(persona['common_complaints'])}
- Personality: {persona['personality_summary']}

NIGERIAN VOICE CONTEXT:
{persona.get('nigerian_voice_context', '')}

AVAILABLE ITEMS TO RECOMMEND FROM:
{json.dumps(filtered_items, indent=2)}

YOUR TASK:
1. Think about what this specific person would enjoy based on their history
2. Pick the top {top_n} items from the list above
3. For each recommendation explain WHY it fits this person specifically
4. Do not give generic reasons — tie each reason back to their actual preferences
5. If this person is an explorer, lean toward variety. If loyal, stick to their proven categories.
6. If their sentiment is declining, prioritize items likely to genuinely impress them.

Return ONLY this JSON, nothing else:
{{
    "recommendations": [
        {{
            "item_id": "<id from the list>",
            "item_name": "<name from the list>",
            "item_category": "<category>",
            "relevance_score": <float between 0 and 1>,
            "reason": "<specific reason why THIS person would enjoy this, reference their preferences>"
        }}
    ],
    "recommendation_reasoning": "<2-3 sentences explaining your overall recommendation strategy for this user>"
}}
"""

    try:
        response = call_llm(prompt, temperature=0.5)
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        result = json.loads(clean)

        result["persona_used"] = {
            "avg_rating": persona["avg_rating"],
            "weighted_avg_rating": persona.get("weighted_avg_rating"),
            "top_categories": persona["top_categories"][:3],
            "key_priorities": persona["key_priorities"],
            "explorer_vs_loyal": persona.get("explorer_vs_loyal"),
            "sentiment_trend": persona.get("sentiment_trend"),
            "nigerian_contextualized": persona.get("contextualized", False),
        }

        return result

    except Exception as e:
        print(f"Recommendation failed: {e}")
        return _fallback_recommendations(filtered_items, top_n)


def recommend_cold_start(persona_input: dict, available_items: list, top_n: int = 5) -> dict:
    """
    Cold start version - no review history available.
    Works from a described persona instead.
    """
    # Smart sample — prefer items with higher avg_rating for cold start
    # since we have no user signal, surface quality items
    sorted_items = sorted(
        available_items,
        key=lambda x: x.get("avg_rating") or 0,
        reverse=True
    )
    filtered_items = sorted_items[:20]

    prompt = f"""
You are a personalized recommendation engine.

WHO YOU ARE RECOMMENDING FOR:
{persona_input.get('description', 'A new user with no history')}

THEIR PREFERENCES:
{persona_input.get('preferences', 'No preferences specified')}

CURRENT CONTEXT:
{persona_input.get('context', 'General recommendation')}

NIGERIAN VOICE CONTEXT:
This person is Nigerian. Factor in Nigerian sensibilities:
- Strong value-for-money awareness
- Food quality and portion size matter
- Ambience and social experience are important
- They appreciate warmth and good service

AVAILABLE ITEMS:
{json.dumps(filtered_items, indent=2)}

Recommend the top {top_n} items. Think carefully before choosing.
Tie every reason back to their specific preferences and context.

Return ONLY this JSON, nothing else:
{{
    "recommendations": [
        {{
            "item_id": "<id>",
            "item_name": "<name>",
            "item_category": "<category>",
            "relevance_score": <float between 0 and 1>,
            "reason": "<specific reason for this person>"
        }}
    ],
    "recommendation_reasoning": "<2-3 sentences on your strategy>",
    "cold_start": true
}}
"""

    try:
        response = call_llm(prompt, temperature=0.5)
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        result = json.loads(clean)
        return result

    except Exception as e:
        print(f"Cold start recommendation failed: {e}")
        return _fallback_recommendations(filtered_items, top_n)


def recommend_cross_domain(user_history: list, target_category: str, available_items: list, top_n: int = 5) -> dict:
    """
    Cross-domain version - user has history in one category
    but wants recommendations in a completely different one.
    """
    persona = build_nigerian_persona(user_history)

    prompt = f"""
You are a cross-domain recommendation engine.

The user has history in: {", ".join(persona['top_categories'][:3])}
They now want recommendations in: {target_category}

THE CHALLENGE:
Transfer what you know about their personality and preferences
into this new domain they have no history in.

WHO THEY ARE:
- Rating tendency: {persona['rating_tendency']}
- Rating consistency: {persona.get('rating_consistency', 'unknown')} (lower = more consistent standards)
- They care most about: {", ".join(persona['key_priorities'])}
- Personality: {persona['personality_summary']}
- Explorer vs loyal: {persona.get('explorer_vs_loyal', 'unknown')}
- Sentiment trend: {persona.get('sentiment_trend', 'stable')}
- They praise: {", ".join(persona['common_praises'])}
- They complain about: {", ".join(persona['common_complaints'])}

NIGERIAN VOICE CONTEXT:
{persona.get('nigerian_voice_context', '')}

AVAILABLE ITEMS IN TARGET CATEGORY:
{json.dumps(available_items[:20], indent=2)}

CROSS-DOMAIN TRANSFER RULES:
- A person who values service in restaurants likely values responsiveness in every domain
- A person who complains about value for money applies that lens everywhere
- An explorer personality will want variety and novelty even in new domains
- A loyal personality wants the "safe best" — highest quality in the new domain
- If their sentiment is declining, they need something genuinely impressive to win them over
- Transfer their core personality, not just their category preferences

Return ONLY this JSON, nothing else:
{{
    "recommendations": [
        {{
            "item_id": "<id>",
            "item_name": "<name>",
            "item_category": "<category>",
            "relevance_score": <float between 0 and 1>,
            "reason": "<how this fits their personality transferred to new domain>"
        }}
    ],
    "cross_domain_reasoning": "<explain how you transferred their preferences across domains>",
    "source_domain": "{", ".join(persona['top_categories'][:2])}",
    "target_domain": "{target_category}"
}}
"""

    try:
        response = call_llm(prompt, temperature=0.5)
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start != -1 and end > start:
            clean = clean[start:end]
        result = json.loads(clean)
        return result

    except Exception as e:
        print(f"Cross domain recommendation failed: {e}")
        return _fallback_recommendations(available_items, top_n)


def _smart_filter(items: list, persona: dict, limit: int = 20) -> list:
    """
    Smart pre-filter before sending items to LLM.
    Prioritizes categories the user already likes.
    For explorers, ensures variety by mixing preferred and new categories.
    """
    top_cats = [c.lower() for c in persona.get("top_categories", [])]
    is_explorer = persona.get("explorer_vs_loyal", "loyal") == "explorer"

    preferred = []
    others = []

    for item in items:
        item_cats = (item.get("item_category") or "").lower()
        if any(cat in item_cats for cat in top_cats):
            preferred.append(item)
        else:
            others.append(item)

    if is_explorer:
        # Explorers get a mix — half preferred, half new territory
        half = limit // 2
        combined = preferred[:half] + others[:limit - half]
    else:
        # Loyal users get mostly what they already like
        combined = preferred[:limit] + others[:max(0, limit - len(preferred))]

    return combined[:limit]


def _fallback_recommendations(items: list, top_n: int) -> dict:
    """Safe fallback if LLM call fails. Sorts by avg_rating instead of pure random."""
    sorted_items = sorted(items, key=lambda x: x.get("avg_rating") or 0, reverse=True)
    sample = sorted_items[:top_n]
    return {
        "recommendations": [
            {
                "item_id": item.get("item_id", ""),
                "item_name": item.get("item_name", "Unknown"),
                "item_category": (item.get("item_category") or ""),
                "relevance_score": 0.5,
                "reason": "Recommended based on general popularity."
            }
            for item in sample
        ],
        "recommendation_reasoning": "Fallback recommendations due to generation error.",
        "error": True
    }