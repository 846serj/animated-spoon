"""Simplified recipe article generator that mirrors the Sheets drafting flow.

Images are still hotlinked directly from Airtable via
``extract_remote_image_url`` so downstream uploads can keep the same
references without touching a media library.
"""

from __future__ import annotations

import html
from typing import Dict, Iterable, List, Optional, Sequence

import openai

from config import *
from .image_utils import build_remote_image_figure, extract_remote_image_url

SYSTEM_PROMPT = (
    "You are a professional food writer who creates engaging, appetizing content."
)


def _deduplicate_recipes(recipes_list: Sequence[Dict]) -> List[Dict]:
    """Remove duplicate recipe entries while preserving order."""
    unique_recipes: List[Dict] = []
    seen_identifiers = set()

    for recipe in recipes_list:
        identifier = recipe.get("id") or recipe.get("record_id")

        if not identifier:
            title = (recipe.get("title") or "").strip().lower()
            url = (recipe.get("url") or "").strip().lower()
            identifier = (title, url) if (title or url) else id(recipe)

        if identifier in seen_identifiers:
            continue

        seen_identifiers.add(identifier)
        unique_recipes.append(recipe)

    return unique_recipes


def _ensure_paragraphs(content: str) -> str:
    """Wrap plain text content in HTML paragraphs if needed."""
    if not content:
        return ""

    stripped = content.strip()
    if stripped.startswith("<p>") or stripped.startswith("<h2>"):
        return stripped

    paragraphs = [p.strip() for p in stripped.split("\n\n") if p.strip()]
    if not paragraphs:
        return ""

    return "\n\n".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in paragraphs)


def _call_model(prompt: str, *, max_tokens: int) -> Optional[str]:
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
    except Exception as exc:
        print(f"Error contacting language model: {exc}")
        return None

    if not response.choices:
        return None

    return (response.choices[0].message.content or "").strip()


def _format_intro(headline: str, recipe_count: int) -> str:
    prompt = (
        "Write an engaging introduction (4-5 sentences) for a recipe roundup "
        f"titled: \"{headline}\". Reference that it features {recipe_count} recipes "
        "and use warm, inviting language."
    )

    response = _call_model(prompt, max_tokens=320) or ""
    intro = _ensure_paragraphs(response)
    if intro:
        return intro

    return (
        f"<p>Welcome to {html.escape(headline)}, a hand-picked lineup of "
        f"{recipe_count} dishes our team can’t stop cooking.</p>"
    )


def _rewrite_description(description: str) -> str:
    prompt = (
        "Rewrite this recipe description to be warm, clear, and inviting. "
        "Limit to 3-4 sentences.\n"
        f'"{description}"'
    )

    response = _call_model(prompt, max_tokens=260) or ""
    rewritten = _ensure_paragraphs(response)
    if rewritten:
        return rewritten

    safe_description = html.escape(description.strip()) if description else ""
    if not safe_description:
        safe_description = (
            "This reader favorite brings together pantry staples for a reliable weeknight win."
        )
    return f"<p>{safe_description}</p>"


def generate_article(query: str, recipes_list: Sequence[Dict]) -> str:
    """Generate a roundup-style article with hotlinked recipe imagery."""
    recipes = _deduplicate_recipes(recipes_list)
    if not recipes:
        return "<p>No recipes found.</p>"

    headline = (query or "Recipe Roundup").strip() or "Recipe Roundup"
    safe_headline = html.escape(headline)

    sections: List[str] = [f"<h1>{safe_headline}</h1>"]
    sections.append(_format_intro(headline, len(recipes)))

    for recipe in recipes:
        title = (recipe.get("title") or "Untitled Recipe").strip() or "Untitled Recipe"
        safe_title = html.escape(title)
        description = (
            recipe.get("description")
            or f"{recipe.get('ingredients', '')} {recipe.get('instructions', '')}"
        ).strip()

        body_html = _rewrite_description(description)

        image_url, airtable_field = extract_remote_image_url(recipe)
        figure_html = build_remote_image_figure(title, image_url, airtable_field)

        section_parts = [f"<h2>{safe_title}</h2>"]
        if figure_html:
            section_parts.append(figure_html)
        section_parts.append(body_html)

        source_url = (recipe.get("url") or "").strip()
        if source_url:
            section_parts.append(
                f'<p><a href="{html.escape(source_url)}" target="_blank">Get the recipe.</a></p>'
            )

        sections.append("\n".join(part for part in section_parts if part))

    return "\n\n".join(part.strip() for part in sections if part)


# Legacy function for backward compatibility
def generate_summary(recipes_list: Iterable[Dict]) -> str:
    """Legacy function - now generates a simple summary."""
    recipes = list(recipes_list)
    if not recipes:
        return "No recipes found."

    recipe_titles = [recipe.get("title", "Untitled Recipe") for recipe in recipes]
    return (
        "<h2>Found Recipes</h2><ul>"
        + "".join([f"<li>{title}</li>" for title in recipe_titles])
        + "</ul>"
    )
