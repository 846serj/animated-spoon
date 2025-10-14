"""Utility helpers for working with recipe imagery.

These helpers intentionally keep image handling lightweight so that the
system never downloads or re-hosts assets. Instead we surface the remote
URLs that already live in Airtable and return them in a consistent format
for downstream HTML generation or validation.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple
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
