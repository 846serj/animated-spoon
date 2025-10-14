"""Helpers that generate ready-to-publish recipe article payloads.

The goal of these utilities is to keep the recipe drafting workflow
extremely lightweight: we never download or mirror imagery from
Airtable, and every entry point can rely on the same logic to prepare a
WordPress friendly response.  By sharing the implementation we avoid
subtle differences between Flask servers, CLIs, or serverless
functions, which previously made it unclear if images would be
re-uploaded downstream.
"""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from .generator import generate_article as _default_article_generator
from .image_utils import collect_image_hotlinks, extract_remote_image_url

# Domains that should never be hotlinked.  These are typically CDN mirrors
# that perform aggressive caching which breaks when referenced directly from
# WordPress.  Calling code can pass additional domains when required.
DEFAULT_BLOCKED_IMAGE_DOMAINS = {"smushcdn.com"}


def _is_blocked_domain(hostname: str, blocked_domains: Iterable[str]) -> bool:
    hostname = hostname.lower()
    for blocked in blocked_domains:
        blocked = blocked.lower().lstrip(".")
        if not blocked:
            continue
        if hostname.endswith(blocked):
            return True
    return False


def filter_recipes_for_hotlinking(
    recipes: Sequence[Dict],
    *,
    blocked_domains: Optional[Iterable[str]] = None,
) -> Tuple[List[Dict], List[Dict[str, object]]]:
    """Return recipes whose imagery can be safely hotlinked.

    The returned tuple contains:

    1. A list of recipes that either contain no imagery or reference a remote
       image URL that we can safely embed without downloading.
    2. Metadata describing recipes that were skipped because their imagery is
       blocked or invalid.  This is primarily surfaced for logging/debugging
       so operators understand why a recipe disappeared from a draft.
    """

    allowed_recipes: List[Dict] = []
    removed_recipes: List[Dict[str, object]] = []

    blocked_domains = list(blocked_domains or DEFAULT_BLOCKED_IMAGE_DOMAINS)

    for recipe in recipes:
        image_url, airtable_field = extract_remote_image_url(recipe)

        if not image_url:
            allowed_recipes.append(recipe)
            continue

        try:
            parsed = urlparse(image_url)
        except ValueError:
            parsed = None

        hostname = parsed.hostname if parsed else ""
        scheme = parsed.scheme if parsed else ""

        if scheme not in {"http", "https"} or not hostname:
            removed_recipes.append(
                {
                    "title": recipe.get("title", "Untitled Recipe"),
                    "image_url": image_url,
                    "airtable_field": airtable_field,
                    "reason": "invalid_url",
                }
            )
            continue

        if _is_blocked_domain(hostname, blocked_domains):
            removed_recipes.append(
                {
                    "title": recipe.get("title", "Untitled Recipe"),
                    "image_url": image_url,
                    "airtable_field": airtable_field,
                    "reason": "blocked_domain",
                }
            )
            continue

        allowed_recipes.append(recipe)

    return allowed_recipes, removed_recipes


def prepare_article_payload(
    query: str,
    recipes: Sequence[Dict],
    *,
    blocked_domains: Optional[Iterable[str]] = None,
    include_removed: bool = True,
    article_generator: Optional[Callable[[str, Sequence[Dict]], str]] = None,
) -> Tuple[Optional[Dict[str, object]], List[Dict[str, object]]]:
    """Return a serialized payload for WordPress/JSON based workflows.

    The helper centralises the most common pattern in the codebase:
    deduplicate recipes, ensure the imagery can be embedded without being
    uploaded, and return a single dictionary that downstream callers can send
    directly to editors or CMS endpoints.

    ``None`` is returned as the first element when no recipes are suitable for
    hotlinking.  In that case callers can inspect ``removed_recipes`` for the
    rejection reason and surface a helpful error message to the user.
    """

    filtered_recipes, removed_recipes = filter_recipes_for_hotlinking(
        recipes, blocked_domains=blocked_domains
    )

    if not filtered_recipes:
        return None, removed_recipes

    generator = article_generator or _default_article_generator
    article_html = generator(query, filtered_recipes)
    sources = [
        recipe.get("url")
        for recipe in filtered_recipes
        if recipe.get("url")
    ]

    payload: Dict[str, object] = {
        "article": article_html,
        "sources": sources,
        "recipe_count": len(filtered_recipes),
        "query": query,
        "image_hotlinks": collect_image_hotlinks(filtered_recipes),
    }

    if include_removed:
        payload["removed_recipes"] = removed_recipes

    return payload, removed_recipes


__all__ = [
    "DEFAULT_BLOCKED_IMAGE_DOMAINS",
    "filter_recipes_for_hotlinking",
    "prepare_article_payload",
]

