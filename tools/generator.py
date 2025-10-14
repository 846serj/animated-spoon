"""Recipe article generation that preserves original Airtable image links."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

import openai

from config import *
from .image_utils import build_remote_image_figure, extract_remote_image_url
from .prompt_templates import (
    INTRO_TEMPLATE,
    RECIPE_SECTION_TEMPLATE,
    extract_context,
)

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
            if title or url:
                identifier = (title, url)
            else:
                identifier = id(recipe)

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

    return "\n\n".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)


def _truncate_words(text: str, limit: int = 100) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + "..."


@dataclass
class RecipeArticleBuilder:
    """Coordinator that assembles article sections while preserving remote images."""

    query: str
    recipes: Sequence[Dict]

    def __post_init__(self) -> None:
        self.recipes = _deduplicate_recipes(self.recipes)
        self.context = extract_context(self.query)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build(self) -> str:
        if not self.recipes:
            return "No recipes found."

        sections: List[str] = []

        intro = self._build_intro()
        if intro:
            sections.append(intro)

        for recipe in self.recipes:
            section_html = self._build_recipe_section(recipe)
            if section_html:
                sections.append(section_html)

        return "\n\n".join(part.strip() for part in sections if part and part.strip())

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------
    def _build_intro(self) -> str:
        content = self._chat_template(
            INTRO_TEMPLATE.format(
                query=self.query,
                cuisine=self.context["cuisine"],
                number=self.context["number"],
            ),
            max_tokens=400,
        )

        if not content:
            return (
                f"<p>Explore {self.context['number']} {self.context['cuisine']} recipes "
                "that bring the spirit of the request to your kitchen.</p>"
            )

        return _ensure_paragraphs(content)

    def _build_recipe_section(self, recipe: Dict) -> str:
        title = recipe.get("title") or "Untitled Recipe"
        description = recipe.get("description") or (
            f"{recipe.get('ingredients', '')} {recipe.get('instructions', '')}"
        )

        response = self._chat_template(
            RECIPE_SECTION_TEMPLATE.format(
                cuisine=self.context["cuisine"],
                title=title,
                description=description,
            ),
            max_tokens=380,
        )

        image_url, airtable_field = extract_remote_image_url(recipe)
        figure = build_remote_image_figure(title, image_url, airtable_field)

        if response:
            body = _ensure_paragraphs(response)
        else:
            fallback_text = f"{recipe.get('ingredients', '')} {recipe.get('instructions', '')}".strip()
            fallback_text = _truncate_words(fallback_text)
            if not fallback_text:
                fallback_text = "This recipe is a reader favourite straight from our Airtable collection."
            body = f"<p>{fallback_text}</p>"

        parts = [f"<h2>{title}</h2>"]
        if figure:
            parts.append(figure)
        parts.append(body)

        source_url = recipe.get("url")
        if source_url:
            parts.append(f'<p><a href="{source_url}">View Full Recipe</a></p>')

        return "\n".join(part for part in parts if part)

    # ------------------------------------------------------------------
    # LLM helper
    # ------------------------------------------------------------------
    def _chat_template(self, user_prompt: str, *, max_tokens: int) -> Optional[str]:
        try:
            response = openai.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.7,
            )
        except Exception as exc:
            print(f"Error contacting language model: {exc}")
            return None

        if not response.choices:
            return None

        content = response.choices[0].message.content or ""
        return content.strip()


def generate_article(query: str, recipes_list: Sequence[Dict]) -> str:
    """Generate a complete article that hotlinks Airtable-hosted imagery."""
    builder = RecipeArticleBuilder(query, recipes_list)
    return builder.build()


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
