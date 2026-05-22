from app.llm import call_llm
from app.persona import build_nigerian_persona
import json


def simulate_review(user_history: list, item: dict) -> dict:
    """
    Given a user's review history and an item they haven't reviewed,
    simulate what their review and rating would look like.

    item dict should have:
        - item_name: str
        - item_category: str
        - item_description: str (optional, any extra context)
    """

    # Build the full Nigerian-contextualized persona
    persona = build_nigerian_persona(user_history)

    # Construct the prompt
    prompt = f"""
You are simulating how a specific person would review a place they just visited.

HERE IS WHO THIS PERSON IS:
- They average {persona['avg_rating']} stars out of 5
- Their rating tendency is: {persona['rating_tendency']} (harsh/balanced/generous)
- Their writing style: {persona['writing_style']} and {persona['writing_style_length']}
- Their tone is usually: {persona['tone']}
- They care most about: {", ".join(persona['key_priorities'])}
- They commonly praise: {", ".join(persona['common_praises'])}
- They commonly complain about: {", ".join(persona['common_complaints'])}
- Personality: {persona['personality_summary']}

VOICE CONTEXT:
{persona.get('nigerian_voice_context', '')}

THE PLACE THEY VISITED:
- Name: {item.get('item_name', 'Unknown')}
- Category: {item.get('item_category', 'Unknown')}
- Additional context: {item.get('item_description', 'No additional context')}

YOUR TASK:
Simulate this exact person's review of this place. Stay true to their personality.
Do not sound generic. Sound like them specifically.

Return ONLY this JSON, nothing else:
{{
    "simulated_rating": <integer between 1 and 5>,
    "simulated_review": "<the review text as this person would write it>",
    "rating_reasoning": "<one sentence explaining why this rating fits this person's history>"
}}
"""

    try:
        response = call_llm(prompt, temperature=0.7)
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)

        # Validate rating is within bounds
        result["simulated_rating"] = max(1, min(5, int(result["simulated_rating"])))

        # Attach persona summary for transparency
        result["persona_used"] = {
            "avg_rating": persona["avg_rating"],
            "rating_tendency": persona["rating_tendency"],
            "tone": persona["tone"],
            "top_categories": persona["top_categories"][:3],
            "nigerian_contextualized": persona.get("contextualized", False)
        }

        return result

    except Exception as e:
        print(f"Review simulation failed: {e}")
        return _fallback_review(item, persona)


def simulate_review_cold_start(item: dict, persona_input: dict) -> dict:
    """
    Cold start version - when we have no review history.
    Instead of history, accepts a manually described persona.

    persona_input example:
    {
        "description": "A young Nigerian professional who loves trying new restaurants",
        "preferences": "Loves spicy food, values quick service, budget conscious"
    }
    """

    prompt = f"""
You are simulating how a specific person would review a place they just visited.

WHO THIS PERSON IS:
{persona_input.get('description', 'A regular customer')}

THEIR PREFERENCES:
{persona_input.get('preferences', 'No specific preferences known')}

VOICE CONTEXT:
This person is Nigerian. Write in natural Nigerian English.
Be direct, expressive, and genuine. Not forced, not stereotyped.

THE PLACE THEY VISITED:
- Name: {item.get('item_name', 'Unknown')}
- Category: {item.get('item_category', 'Unknown')}
- Additional context: {item.get('item_description', 'No additional context')}

Simulate their review. Sound like a real person, not a template.

Return ONLY this JSON, nothing else:
{{
    "simulated_rating": <integer between 1 and 5>,
    "simulated_review": "<the review text>",
    "rating_reasoning": "<one sentence explaining the rating>"
}}
"""

    try:
        response = call_llm(prompt, temperature=0.7)
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
        result["simulated_rating"] = max(1, min(5, int(result["simulated_rating"])))
        result["cold_start"] = True
        return result

    except Exception as e:
        print(f"Cold start simulation failed: {e}")
        return _fallback_review(item, {})


def _fallback_review(item: dict, persona: dict) -> dict:
    """Returns a safe fallback if LLM call fails"""
    return {
        "simulated_rating": round(persona.get("avg_rating", 3.5)),
        "simulated_review": f"Visited {item.get('item_name', 'this place')}. It was an average experience overall.",
        "rating_reasoning": "Fallback response due to generation error.",
        "error": True
    }