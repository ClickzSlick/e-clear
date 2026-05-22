# # import os
# # from dotenv import load_dotenv
# # from litellm import completion

# # load_dotenv()

# # LLM_MODEL = os.getenv("LLM_MODEL")
# # print(f"Using LLM model: {LLM_MODEL}")
# # LLM_API_KEY = os.getenv("LLM_API_KEY")
# # LLM_API_BASE = os.getenv("LLM_API_BASE", None)


# # def call_llm(prompt: str, system: str = None, temperature: float = 0.7) -> str:
# #     """
# #     Single entry point for all LLM calls.
# #     """
# #     messages = []

# #     if system:
# #         messages.append({"role": "system", "content": system})

# #     messages.append({"role": "user", "content": prompt})

# #     response = completion(
# #         model=LLM_MODEL,
# #         messages=messages,
# #         api_key=LLM_API_KEY,
# #         api_base=LLM_API_BASE,
# #         temperature=temperature,
# #     )

# #     return response.choices[0].message.content


# import os
# from dotenv import load_dotenv
# from litellm import completion

# load_dotenv()

# LLM_MODEL = os.getenv("LLM_MODEL")
# LLM_API_KEY = os.getenv("LLM_API_KEY")
# LLM_API_BASE = os.getenv("LLM_API_BASE", None)

# # Print model on startup so we can confirm what's being used
# print(f"Using LLM model: {LLM_MODEL}")


# def call_llm(prompt: str, system: str = None, temperature: float = 0.7) -> str:
#     messages = []
#     if system:
#         messages.append({"role": "system", "content": system})
#     messages.append({"role": "user", "content": prompt})

#     response = completion(
#         model=LLM_MODEL,
#         messages=messages,
#         api_key=LLM_API_KEY,
#         api_base=LLM_API_BASE,
#         temperature=temperature,
#         extra_headers={
#             "HTTP-Referer": "https://bct-hackathon.com",
#             "X-Title": "BCT LLM Agent"
#         }
#     )

#     return response.choices[0].message.content

import os
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE", None)

FALLBACK_MODEL = os.getenv("FALLBACK_MODEL")
FALLBACK_API_KEY = os.getenv("FALLBACK_API_KEY")
FALLBACK_API_BASE = os.getenv("FALLBACK_API_BASE", None)

print(f"Using LLM model: {LLM_MODEL}")


def call_llm(prompt: str, system: str = None, temperature: float = 0.7) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Try primary (Groq)
    try:
        response = completion(
            model=LLM_MODEL,
            messages=messages,
            api_key=LLM_API_KEY,
            api_base=LLM_API_BASE,
            temperature=temperature,
        )
        return response.choices[0].message.content

    except Exception as primary_error:
        print(f"Primary LLM failed: {primary_error}")

        # Try fallback (OpenRouter)
        if FALLBACK_MODEL and FALLBACK_API_KEY:
            try:
                print(f"Trying fallback: {FALLBACK_MODEL}")
                response = completion(
                    model=FALLBACK_MODEL,
                    messages=messages,
                    api_key=FALLBACK_API_KEY,
                    api_base=FALLBACK_API_BASE,
                    temperature=temperature,
                    extra_headers={
                        "HTTP-Referer": "https://bct-hackathon.com",
                        "X-Title": "BCT LLM Agent"
                    }
                )
                return response.choices[0].message.content
            except Exception as fallback_error:
                print(f"Fallback LLM also failed: {fallback_error}")
                raise fallback_error

        raise primary_error