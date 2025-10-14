"""Lightweight recipe article generator.

This module keeps the drafting flow intentionally small and predictable so it
mirrors the simple Google Sheets workflow the editorial team is used to.  We
only make two kinds of language-model calls: one for the roundup introduction
and one for each selected recipe blurb.  The rest of the work is straightforward
string assembly with gentle HTML escaping to avoid surprises when the copy is
pasted into WordPress.
"""

from __future__ import annotations

from html import escape
from typing import Dict, Iterable, List, Optional, Sequence

import openai

from config import LLM_MODEL
from .image_utils import build_remote_image_figure, extract_remote_image_url

SYSTEM_PROMPT = (
    "You are a warm, professional food writer. Draft friendly, down-to-earth "
    "copy that sounds like it belongs in a recipe roundup."
)


def _call_llm(prompt: str, *, max_tokens: int = 400) -> Optional[str]:
    """Send a minimal chat completion request and return trimmed content."""

    try:
        response = openai.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
    except Exception as exc:  # pragma: no cover - network failure fallback
        print(f"Error contacting language model: {exc}")
        return None

    if not response.choices:
        return None

    content = response.choices[0].message.content or ""
    return content.strip() or None


def _as_paragraphs(text: str) -> str:
    """Convert plain text into HTML paragraphs with escaping."""

    if not text:
        return ""

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    return "\n".join(f"<p>{escape(line)}</p>" for line in lines)


def _fallback_intro(headline: str, recipe_count: int) -> str:
    """Provide a deterministic introduction when the LLM is unavailable."""

    headline_text = escape(headline) if headline else "This Week's Recipes"
    if recipe_count == 1:
        body = "Dig into this handpicked dish and make tonight special."
    else:
        body = (
            f"Explore {recipe_count} reader-loved recipes that bring this roundup "
            "to life."
        )
    return f"<p>{headline_text}</p>\n<p>{escape(body)}</p>"


def _fallback_blurb(recipe: Dict) -> str:
    """Create a short blurb directly from stored recipe fields."""

    description = recipe.get("description") or ""
    if description:
        return f"<p>{escape(description)}</p>"

    ingredients = recipe.get("ingredients") or ""
    instructions = recipe.get("instructions") or ""
    combined = " ".join(part for part in (ingredients, instructions) if part)
    combined = combined.strip() or "This reader favourite is a staple from our archive."
    return f"<p>{escape(combined)}</p>"


def _sanitize_link(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    url = url.strip()
    return url or None


def generate_article(headline: str, recipes_list: Sequence[Dict]) -> str:
    """Generate a roundup article using simple, predictable steps."""

    recipes: List[Dict] = [recipe for recipe in recipes_list if recipe]
    if not recipes:
        return "No recipes selected."

    headline_text = (headline or "").strip() or "Recipe Roundup"

    intro_prompt = (
        "Write an engaging introduction (4-5 sentences) for a recipe roundup "
        f"titled: \"{headline_text}\". Sound warm, clear, and inviting."
    )
    intro_text = _call_llm(intro_prompt, max_tokens=320)
    intro_html = _as_paragraphs(intro_text) if intro_text else _fallback_intro(headline_text, len(recipes))

    sections: List[str] = [intro_html]

    for recipe in recipes:
        title = (recipe.get("title") or "Untitled Recipe").strip()
        description = recipe.get("description") or ""
        if not description:
            description = " ".join(
                part
                for part in (
                    recipe.get("summary"),
                    recipe.get("notes"),
                    recipe.get("ingredients"),
                    recipe.get("instructions"),
                )
                if part
            )

        prompt = (
            "Rewrite this recipe description to be warm, clear, and inviting. "
            "Limit the copy to 3-4 sentences.\n"
            f"\"{description}\""
        )
        blurb_text = _call_llm(prompt, max_tokens=280)
        blurb_html = _as_paragraphs(blurb_text) if blurb_text else _fallback_blurb(recipe)

        image_url, airtable_field = extract_remote_image_url(recipe)
        figure_html = build_remote_image_figure(title, image_url, airtable_field)

        section_parts = [f"<h2>{escape(title)}</h2>"]
        if figure_html:
            section_parts.append(figure_html)
        section_parts.append(blurb_html)

        link = _sanitize_link(recipe.get("url"))
        if link:
            section_parts.append(
                f'<p><a href="{escape(link)}" target="_blank" rel="noopener">Get the recipe.</a></p>'
            )

        sections.append("\n".join(part for part in section_parts if part))

    return "\n\n".join(section for section in sections if section)


def generate_summary(recipes_list: Iterable[Dict]) -> str:
    """Legacy helper that lists recipe titles for quick previews."""

    recipes = [recipe for recipe in recipes_list if recipe]
    if not recipes:
        return "No recipes selected."

    items = [f"<li>{escape(recipe.get('title', 'Untitled Recipe'))}</li>" for recipe in recipes]
    return "<h2>Found Recipes</h2><ul>" + "".join(items) + "</ul>"
