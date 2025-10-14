#!/usr/bin/env python3
"""Quick CLI for drafting recipe roundup articles with hotlinked imagery."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import embeddings, retrieval, vector_store  # noqa: E402
from tools.drafting import (  # noqa: E402
    DEFAULT_BLOCKED_IMAGE_DOMAINS,
    prepare_article_payload,
)


def _load_index() -> Tuple[list, object, dict]:
    """Return recipes, FAISS index, and id->recipe mapping."""

    recipes = embeddings.load_embeddings()
    index = vector_store.load_faiss_index()
    id_to_recipe = vector_store.get_id_to_recipe(recipes)
    return recipes, index, id_to_recipe


def _determine_k(query: str, default: int = 5) -> int:
    import re

    matches = re.findall(r"\d+", query)
    if matches:
        try:
            return max(1, int(matches[0]))
        except ValueError:
            pass
    return default


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Draft a recipe roundup article without ever uploading imagery."
    )
    parser.add_argument("query", help="Human friendly prompt, e.g. '7 cozy fall soups'")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the full payload as JSON instead of pretty text",
    )

    args = parser.parse_args()

    recipes, index, id_to_recipe = _load_index()
    k = _determine_k(args.query)

    top_recipes = retrieval.search_recipes(args.query, index, id_to_recipe, k=k)
    if not top_recipes:
        print("No recipes found for query.")
        return 1

    payload, removed = prepare_article_payload(
        args.query,
        top_recipes,
        blocked_domains=DEFAULT_BLOCKED_IMAGE_DOMAINS,
    )

    if not payload:
        print("No recipes with accessible imagery were available.")
        if removed:
            print("Removed recipes:")
            for entry in removed:
                print(f" - {entry.get('title')} ({entry.get('reason')})")
        return 2

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("=== Article HTML ===")
        print(payload["article"])
        print("\n=== Sources ===")
        for src in payload["sources"]:
            print(f" - {src}")
        print("\n=== Hotlinked Images ===")
        for item in payload["image_hotlinks"]:
            print(f" - {item['title']}: {item['image_url']}")
        if removed:
            print("\nSkipped recipes (imagery not safe to hotlink):")
            for entry in removed:
                print(
                    f" - {entry.get('title')} -> {entry.get('image_url')} ({entry.get('reason')})"
                )

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

