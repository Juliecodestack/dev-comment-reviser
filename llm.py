# llm.py — call the AI (DeepSeek, OpenAI-compatible API) and parse its reply.
import os

from dotenv import load_dotenv
from openai import OpenAI

from prompts import SYSTEM_PROMPT

load_dotenv()  # reads .env if present; real environment variables take precedence

MODEL = os.getenv("DS_MODEL", "deepseek-flash")
BASE_URL = os.getenv("DS_BASE_URL", "https://api.deepseek.com")

HEADING_REVISED = "## Revised Text"
HEADING_EXPLANATIONS = "## Paragraph Explanations"


class LLMError(RuntimeError):
    """Raised when the AI call fails or the reply is not in the expected format."""


def _client() -> OpenAI:
    api_key = os.getenv("DS_API_KEY")
    if not api_key:
        raise LLMError(
            "DS_API_KEY is not set. Put it in a .env file next to main.py "
            "(see .env.example) or export it as an environment variable."
        )
    return OpenAI(api_key=api_key, base_url=BASE_URL)


def split_sections(reply: str) -> tuple[str, str]:
    """Split the AI reply at the two headings the system prompt demands."""
    i = reply.find(HEADING_REVISED)
    j = reply.find(HEADING_EXPLANATIONS)
    if i == -1 or j == -1 or j < i:
        raise LLMError(
            "AI reply did not contain the expected "
            f"'{HEADING_REVISED}' / '{HEADING_EXPLANATIONS}' sections."
        )
    revised = reply[i + len(HEADING_REVISED):j].strip()
    explanations = reply[j + len(HEADING_EXPLANATIONS):].strip()
    return revised, explanations


def revise_comment(text: str) -> tuple[str, str]:
    """Send the comment to the AI, return (revised_text, explanations)."""
    try:
        resp = _client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
    except LLMError:
        raise
    except Exception as e:  # network errors, auth errors, SDK errors...
        raise LLMError(f"AI request failed: {e}") from e

    reply = resp.choices[0].message.content or ""
    return split_sections(reply)
