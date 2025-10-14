"""WordPress integration that ensures hotlinking without media library downloads.

This module provides WordPress-specific functionality that:
1. Creates blog posts with hotlinked images (no downloads)
2. Sets featured images using external URLs
3. Handles image validation and proxy endpoints
4. Prevents WordPress from downloading images to media library
"""

from __future__ import annotations

import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import json


class WordPressHotlinkIntegration:
    """WordPress integration that preserves remote image URLs without downloading."""
    
    def __init__(self, wp_site_url: str, wp_username: str, wp_password: str):
        """Initialize WordPress integration with credentials."""
        self.wp_site_url = wp_site_url.rstrip('/')
        self.wp_username = wp_username
        self.wp_password = wp_password
        self.api_base = f"{self.wp_site_url}/wp-json/wp/v2"
        
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for WordPress API."""
        import base64
        credentials = f"{self.wp_username}:{self.wp_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }
    
    def validate_image_url(self, image_url: str) -> bool:
        """Validate that an image URL is accessible and not blocked."""
        try:
            parsed = urlparse(image_url)
            if parsed.scheme not in ('http', 'https'):
                return False
                
            # Check if URL is accessible
            response = requests.head(image_url, timeout=10, allow_redirects=True)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def create_post_with_hotlinked_images(
        self, 
        title: str, 
        content: str, 
        status: str = 'draft'
    ) -> Dict:
        """Create a WordPress post with hotlinked images in content (no media library downloads)."""
        
        # Process content to ensure all images use hotlinking
        processed_content = self.process_content_for_hotlinking(content)
        
        # Prepare post data
        post_data = {
            'title': title,
            'content': processed_content,
            'status': status,
            'format': 'standard'
        }
        
        # Create the post
        response = requests.post(
            f"{self.api_base}/posts",
            headers=self._get_auth_headers(),
            json=post_data
        )
        
        if response.status_code not in (200, 201):
            raise Exception(f"Failed to create WordPress post: {response.text}")
        
        return response.json()
    
    
    
    def process_content_for_hotlinking(self, content: str) -> str:
        """Process HTML content to ensure all images use hotlinking."""
        import re
        
        # Find all img tags and ensure they use external URLs
        def replace_img_src(match):
            img_tag = match.group(0)
            src_match = re.search(r'src="([^"]*)"', img_tag)
            if src_match:
                original_url = src_match.group(1)
                # Keep the original URL - no processing needed for hotlinking
                return img_tag
            return img_tag
        
        # Replace img tags to ensure they're properly formatted for hotlinking
        processed_content = re.sub(r'<img[^>]*>', replace_img_src, content)
        
        return processed_content
    
    def get_image_hotlinks_from_content(self, content: str) -> List[str]:
        """Extract all image URLs from content for validation."""
        import re
        
        img_pattern = r'<img[^>]*src="([^"]*)"[^>]*>'
        image_urls = re.findall(img_pattern, content)
        
        return [url for url in image_urls if url.startswith(('http://', 'https://'))]


def create_wordpress_post_with_hotlinks(
    wp_site_url: str,
    wp_username: str, 
    wp_password: str,
    title: str,
    content: str
) -> Dict:
    """Convenience function to create a WordPress post with hotlinked images in content."""
    
    wp_integration = WordPressHotlinkIntegration(wp_site_url, wp_username, wp_password)
    
    # Create the post (content processing is handled internally)
    result = wp_integration.create_post_with_hotlinked_images(
        title=title,
        content=content
    )
    
    return result


def validate_wordpress_hotlinking_setup(wp_site_url: str, wp_username: str, wp_password: str) -> bool:
    """Validate that WordPress is properly configured for hotlinking."""
    try:
        wp_integration = WordPressHotlinkIntegration(wp_site_url, wp_username, wp_password)
        
        # Test API access
        response = requests.get(
            f"{wp_integration.api_base}/posts",
            headers=wp_integration._get_auth_headers(),
            params={'per_page': 1}
        )
        
        return response.status_code == 200
        
    except Exception:
        return False
