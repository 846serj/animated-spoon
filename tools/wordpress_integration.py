"""WordPress utilities that keep recipe images hotlinked instead of reuploaded.

The original implementation wrapped everything in a fairly stateful class that
duplicated logic for processing HTML and creating API payloads.  The goal of
this refactor is to make the behaviour easier to audit: we expose small helper
functions that

1. normalise every ``<img>`` element so the ``src`` attribute is left untouched,
2. add metadata that flags the tag as a hotlink (helpful for WordPress
   side filters), and
3. provide a single place that performs authenticated REST calls.

Because these helpers are pure functions, there is no hidden code path that can
decide to download or mirror remote images.  The exposed convenience class is
now a very light wrapper around those helpers so existing imports continue to
work without modification.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import re
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import requests


def _is_remote_url(url: str) -> bool:
    """Return ``True`` when *url* points at an http(s) resource."""

    if not isinstance(url, str):
        return False

    candidate = url.strip()
    if not candidate:
        return False

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False

    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalise_img_tag(tag: str) -> Tuple[str, str | None]:
    """Return a cleaned ``<img>`` element and its remote ``src`` URL.

    The function keeps attribute ordering stable while appending the metadata
    that our WordPress plugin expects.  We explicitly avoid touching the ``src``
    attribute so WordPress will not attempt to sideload the asset.
    """

    src_match = re.search(r'src="([^"]+)"', tag, flags=re.IGNORECASE)
    if not src_match:
        return tag, None

    src = src_match.group(1)
    if not _is_remote_url(src):
        # Non remote URLs (e.g. data URIs or relative paths) are returned as-is.
        return tag, None

    attributes: Dict[str, str] = {}
    for match in re.finditer(r'(\w[\w-]*)="([^"]*)"', tag):
        attr, value = match.groups()
        attributes[attr.lower()] = value

    # Ensure we mark the image as a hotlink without overwriting existing attrs.
    if 'data-image-hotlink' not in attributes:
        tag = tag.replace('<img', '<img data-image-hotlink="true"', 1)
    if 'data-external-source' not in attributes:
        tag = tag.replace('<img', '<img data-external-source="remote"', 1)
    if 'loading' not in attributes:
        tag = tag.replace('<img', '<img loading="lazy"', 1)
    if 'decoding' not in attributes:
        tag = tag.replace('<img', '<img decoding="async"', 1)

    return tag, src


def ensure_hotlinked_images(content: str) -> Tuple[str, List[str]]:
    """Return *content* with hotlink metadata and the list of remote URLs."""

    if not isinstance(content, str) or not content:
        return "", []

    image_urls: List[str] = []

    def _rewrite(match: re.Match[str]) -> str:
        tag = match.group(0)
        rewritten, src = _normalise_img_tag(tag)
        if src:
            image_urls.append(src)
        return rewritten

    processed = re.sub(r'<img[^>]*?>', _rewrite, content, flags=re.IGNORECASE)
    return processed, image_urls


def _build_auth_headers(username: str, password: str) -> Dict[str, str]:
    """Return HTTP headers for WordPress Basic Auth."""

    credentials = f"{username}:{password}".encode()
    token = base64.b64encode(credentials).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _create_post(
    api_base: str,
    auth_headers: Dict[str, str],
    *,
    title: str,
    content: str,
    status: str = "draft",
) -> Dict:
    payload = {"title": title, "content": content, "status": status, "format": "standard"}
    response = requests.post(f"{api_base}/posts", headers=auth_headers, json=payload)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create WordPress post: {response.text}")
    return response.json()


@dataclass(frozen=True)
class WordPressHotlinkIntegration:
    """Small convenience wrapper that preserves the public API from v1."""

    wp_site_url: str
    wp_username: str
    wp_password: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "wp_site_url", self.wp_site_url.rstrip("/"))

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def api_base(self) -> str:
        return f"{self.wp_site_url}/wp-json/wp/v2"

    @property
    def _auth_headers(self) -> Dict[str, str]:
        return _build_auth_headers(self.wp_username, self.wp_password)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def process_content_for_hotlinking(self, content: str) -> str:
        processed, _ = ensure_hotlinked_images(content)
        return processed

    def get_image_hotlinks_from_content(self, content: str) -> List[str]:
        _, urls = ensure_hotlinked_images(content)
        return urls

    def validate_image_url(self, image_url: str) -> bool:
        if not _is_remote_url(image_url):
            return False
        try:
            response = requests.head(image_url, timeout=10, allow_redirects=True)
            return response.status_code == 200
        except Exception:
            return False

    def create_post_with_hotlinked_images(self, title: str, content: str, *, status: str = "draft") -> Dict:
        processed, _ = ensure_hotlinked_images(content)
        return _create_post(self.api_base, self._auth_headers, title=title, content=processed, status=status)


def create_wordpress_post_with_hotlinks(
    wp_site_url: str,
    wp_username: str,
    wp_password: str,
    title: str,
    content: str,
    status: str = "draft",
) -> Dict:
    """Convenience wrapper that mirrors the class-based helper."""

    integration = WordPressHotlinkIntegration(wp_site_url, wp_username, wp_password)
    return integration.create_post_with_hotlinked_images(title=title, content=content, status=status)


def validate_wordpress_hotlinking_setup(wp_site_url: str, wp_username: str, wp_password: str) -> bool:
    """Return ``True`` when credentials can query the posts endpoint."""

    try:
        integration = WordPressHotlinkIntegration(wp_site_url, wp_username, wp_password)
        response = requests.get(f"{integration.api_base}/posts", headers=integration._auth_headers, params={"per_page": 1})
        return response.status_code == 200
    except Exception:
        return False
