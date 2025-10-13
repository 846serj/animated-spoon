"""Recipe search and retrieval functionality."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import openai
import faiss

from config import *


# Common filler words that should not be treated as required search terms.
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "any",
    "are",
    "best",
    "bright",
    "by",
    "cozy",
    "day",
    "delicious",
    "dinner",
    "dish",
    "dishes",
    "easy",
    "for",
    "from",
    "guide",
    "ideas",
    "in",
    "incredible",
    "keeper",
    "list",
    "make",
    "meal",
    "must",
    "of",
    "on",
    "our",
    "perfect",
    "recipes",
    "simple",
    "that",
    "the",
    "their",
    "these",
    "this",
    "those",
    "to",
    "ultimate",
    "way",
    "week",
    "weekday",
    "weekend",
    "with",
}


# Phrases that should be matched exactly when present in the query.
_SPECIAL_PHRASES: Tuple[str, ...] = (
    "air fryer",
    "instant pot",
    "pressure cooker",
    "slow cooker",
    "sheet pan",
    "one pan",
    "one-pot",
    "one pot",
    "meal prep",
    "no-bake",
    "no bake",
    "gluten-free",
    "gluten free",
    "dairy-free",
    "dairy free",
    "vegan",
    "vegetarian",
    "keto",
    "paleo",
    "low-carb",
    "low carb",
    "high-protein",
    "high protein",
    "sugar-free",
    "sugar free",
    "kid-friendly",
    "kid friendly",
    "date night",
)


def _normalize_text(text: str) -> str:
    """Lower-case text and collapse whitespace for reliable searching."""

    if not text:
        return ""

    # Replace non-alphanumeric characters with spaces, lower-case, collapse spaces.
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_required_terms(query: str) -> List[str]:
    """Derive the important terms from the query that recipes must satisfy."""

    query_lower = query.lower()
    reserved_tokens: set[str] = set()
    required_terms: List[str] = []

    for phrase in _SPECIAL_PHRASES:
        if phrase in query_lower:
            required_terms.append(phrase)
            reserved_tokens.update(phrase.split())

    tokens = re.findall(r"[a-z0-9']+", query_lower)

    for token in tokens:
        if token.isdigit():
            continue
        if token in _STOP_WORDS:
            continue
        if token in reserved_tokens:
            continue
        required_terms.append(token)

    return required_terms


def _recipe_text(recipe: Dict) -> str:
    """Aggregate searchable text from a recipe record."""

    parts: List[str] = []
    for key in (
        "title",
        "description",
        "category",
        "cuisine",
        "notes",
        "summary",
        "ingredients",
        "instructions",
        "tags",
    ):
        value = recipe.get(key)
        if not value:
            continue
        if isinstance(value, (list, tuple, set)):
            parts.append(" ".join(str(item) for item in value))
        else:
            parts.append(str(value))

    return " ".join(parts)


def _count_term_matches(required_terms: Sequence[str], normalized_text: str, tokens: Iterable[str]) -> int:
    """Return how many required terms are present in the recipe text."""

    token_set = set(tokens)
    match_count = 0
    for term in required_terms:
        if " " in term:
            if term in normalized_text:
                match_count += 1
        else:
            if term in token_set:
                match_count += 1

    return match_count


def search_recipes(query, index, id_to_recipe, category=None, tags=None, k=5):
    """Search for recipes using vector similarity augmented with keyword filtering."""

    # Generate query embedding
    response = openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[query],
    )
    query_embedding = np.array([response.data[0].embedding]).astype("float32")

    # Normalize for cosine similarity
    faiss.normalize_L2(query_embedding)

    # Fetch more than required so we can enforce stricter keyword matching.
    search_k = max(k * 6, TOP_K)
    scores, indices = index.search(query_embedding, search_k)

    required_terms = _extract_required_terms(query)

    # Aggregate candidate recipes along with their similarity scores and match counts.
    candidates = []
    recipe_ids = list(id_to_recipe.keys())
    seen_recipe_ids = set()

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1 or idx >= len(recipe_ids):
            continue

        recipe_id = recipe_ids[idx]
        if recipe_id in seen_recipe_ids:
            continue

        recipe = id_to_recipe[recipe_id]

        # Apply metadata filters first.
        if category and recipe.get("category", "").lower() != category.lower():
            continue
        if tags:
            recipe_tags = [tag.lower() for tag in recipe.get("tags", [])]
            if not any(tag.lower() in recipe_tags for tag in tags):
                continue

        searchable_text = _recipe_text(recipe)
        normalized_text = _normalize_text(searchable_text)
        token_list = re.findall(r"[a-z0-9']+", normalized_text)

        if required_terms:
            match_count = _count_term_matches(required_terms, normalized_text, token_list)
            match_ratio = match_count / len(required_terms)
        else:
            match_count = 0
            match_ratio = 1.0

        candidates.append(
            {
                "recipe": recipe,
                "score": float(score),
                "match_count": match_count,
                "match_ratio": match_ratio,
            }
        )
        seen_recipe_ids.add(recipe_id)

    if not candidates:
        return []

    # Prioritize candidates that satisfy all required terms and have higher similarity.
    candidates.sort(
        key=lambda item: (
            item["match_ratio"],
            item["match_count"],
            item["score"],
        ),
        reverse=True,
    )

    strict_matches = [c for c in candidates if c["match_ratio"] >= 0.999]
    partial_matches = [c for c in candidates if c["match_ratio"] < 0.999]

    results: List[Dict] = [c["recipe"] for c in strict_matches[:k]]

    if len(results) < k:
        # Allow strong partial matches if we still need more results.
        for candidate in partial_matches:
            if len(results) >= k:
                break

            # Require at least half of the important terms to match to avoid irrelevant picks.
            if required_terms and candidate["match_ratio"] < 0.5:
                continue

            results.append(candidate["recipe"])

    if len(results) < k:
        # Fall back to any remaining candidates (already sorted by relevance).
        for candidate in candidates:
            if len(results) >= k:
                break
            recipe = candidate["recipe"]
            if recipe in results:
                continue
            results.append(recipe)

    return results[:k]
