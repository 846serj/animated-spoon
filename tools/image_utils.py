"""Utility helpers for working with recipe imagery.

The goal is to hotlink Airtable-hosted assets without ever downloading or
re-uploading them. WordPress automation scripts can therefore embed the
returned URLs directly (for example by writing ``<img src="...">`` into the
post body or storing the URL as the featured image meta) and avoid filling the
destination media library with duplicates.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

# Fields that Airtable uses to store the original image URL. The order
# reflects our preference when looking up links so we always favor the
# original source over Airtable hosted attachments.
PREFERRED_IMAGE_FIELDS: Tuple[str, ...] = (
    "image_link",
    "image_url",
    "image",
    "photo",
    "picture",
    "Image",
    "Photo",
    "Picture",
    "Image URL",
    "Image Link",
)


def _normalise_remote_url(value: Optional[str]) -> Optional[str]:
    """Return a trimmed remote URL when the input looks valid."""
    if not value:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None

    if parsed.scheme not in ("http", "https"):
        return None

    if not parsed.netloc:
        return None

    return candidate


def extract_remote_image_url(recipe: Dict) -> Tuple[Optional[str], Optional[str]]:
    """Return the first usable remote image URL for a recipe.

    The tuple contains the resolved URL and the Airtable field that it
    originated from. Downstream consumers can use this to make logging or
    debugging clearer without ever downloading the asset locally.
    """
    for field in PREFERRED_IMAGE_FIELDS:
        value = recipe.get(field)
        if isinstance(value, str):
            url = _normalise_remote_url(value)
            if url:
                return url, field

    attachments = recipe.get("attachments")
    if isinstance(attachments, (list, tuple)):
        for attachment in attachments:
            url: Optional[str] = None
            if isinstance(attachment, dict):
                url = _normalise_remote_url(attachment.get("url"))
            elif isinstance(attachment, str):
                url = _normalise_remote_url(attachment)

            if url:
                return url, "attachments"

    return None, None


def collect_image_hotlinks(recipes: Iterable[Dict]) -> List[Dict[str, object]]:
    """Return metadata describing every hotlinkable image in ``recipes``."""

    hotlinks: List[Dict[str, object]] = []

    for recipe in recipes:
        image_url, airtable_field = extract_remote_image_url(recipe)
        if not image_url:
            continue

        hotlinks.append(
            {
                "title": recipe.get("title", "Untitled Recipe"),
                "image_url": image_url,
                "airtable_field": airtable_field,
                "hotlink": True,
            }
        )

    return hotlinks


def build_image_credit(image_url: str) -> str:
    """Generate a human friendly credit line for the remote image."""
    try:
        parsed = urlparse(image_url)
    except ValueError:
        return "Image credit: Source"

    domain = parsed.netloc
    if not domain:
        return "Image credit: Source"

    return f"Image credit: {domain}"


def build_remote_image_figure(
    title: str,
    image_url: Optional[str],
    airtable_field: Optional[str],
) -> str:
    """Return a HTML figure element that hotlinks the remote Airtable image."""
    if not image_url:
        return ""

    caption = build_image_credit(image_url)
    source_field = airtable_field or "unknown"
    return (
        '\n<figure style="margin: 10px 0; text-align: center;" '
        'data-image-hosting="remote" '
        'data-image-hotlink="true" '
        f'data-image-source-field="{source_field}">'
        f'\n<img src="{image_url}" alt="{title}" '
        'width="1280" height="720" '
        'style="width: 100%; max-width: 1280px; height: auto; border-radius: 8px; object-fit: cover;" '
        'loading="lazy" '
        f'data-original-image-url="{image_url}">'
        f'\n<figcaption style="font-size: 0.9em; color: #666; margin-top: 5px; font-style: italic;">{caption}</figcaption>'
        '\n</figure>'
    )
