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


def _split_heading(line: str) -> tuple[str | None, str]:
    """Split a line into (section kind, text after the heading).

    Accepts the shapes models actually emit: any heading level, **bold**, a
    trailing colon, any case, and content on the same line ("## Revised Text
    Fixed."). Returns (None, "") for an ordinary line of body text.
    """
    text = line.strip()
    if not text:
        return None, ""
    body = text.lstrip("#").strip().lstrip("*").strip()
    for kind, label in (("revised", "revised text"),
                        ("explanations", "paragraph explanations")):
        if body[:len(label)].casefold() != label:
            continue
        rest = body[len(label):]
        if rest[:1].isalnum():  # "Revised Textbook" is not the heading
            continue
        return kind, rest.lstrip("*: ").strip()
    return None, ""


def split_sections(reply: str) -> tuple[str, str]:
    """Split the AI reply at the two headings the system prompt demands.

    The headings belong to the model, but the text in between may quote the
    author's markdown - including these very lines. So the revision ends at the
    LAST "Paragraph Explanations" heading, not the first: a quoted heading
    inside the comment cannot cut the revision in half.

    An empty revised section is an error, not a success: it used to be saved as
    a blank submission.
    """
    lines = reply.splitlines()
    first_revised = None
    last_explanations = None
    revised_inline = ""
    explanations_inline = ""
    for index, line in enumerate(lines):
        kind, rest = _split_heading(line)
        if kind == "revised" and first_revised is None:
            first_revised, revised_inline = index, rest
        elif kind == "explanations":
            last_explanations, explanations_inline = index, rest

    if first_revised is None or last_explanations is None or last_explanations <= first_revised:
        raise LLMError(
            "AI reply did not contain the expected "
            f"'{HEADING_REVISED}' / '{HEADING_EXPLANATIONS}' sections."
        )

    revised = "\n".join(([revised_inline] if revised_inline else [])
                        + lines[first_revised + 1:last_explanations]).strip()
    if not revised:
        raise LLMError(f"AI reply had an empty '{HEADING_REVISED}' section.")
    explanations = "\n".join(([explanations_inline] if explanations_inline else [])
                             + lines[last_explanations + 1:]).strip()
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
