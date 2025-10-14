#!/usr/bin/env python3
"""
Example script demonstrating how to create WordPress posts with hotlinked images.

This script shows how to:
1. Generate article content with hotlinked images
2. Create WordPress posts without downloading images
3. Set external URLs as featured images
4. Validate image URLs before posting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.wordpress_integration import create_wordpress_post_with_hotlinks, validate_wordpress_hotlinking_setup
from tools.generator import generate_article
from tools.retrieval import search_recipes
import json


def example_wordpress_hotlinking():
    """Example of creating WordPress posts with hotlinked images."""
    
    # WordPress configuration
    WP_SITE_URL = "https://your-wordpress-site.com"
    WP_USERNAME = "your-username"
    WP_PASSWORD = "your-app-password"  # Use Application Password, not regular password
    
    # Validate WordPress setup
    print("Validating WordPress setup...")
    if not validate_wordpress_hotlinking_setup(WP_SITE_URL, WP_USERNAME, WP_PASSWORD):
        print("❌ WordPress setup validation failed!")
        print("Make sure you have:")
        print("1. Correct WordPress URL")
        print("2. Valid username and application password")
        print("3. WordPress REST API enabled")
        return False
    
    print("✅ WordPress setup validated!")
    
    # Example query
    query = "5 cozy fall soups to warm up chilly evenings"
    
    print(f"\nSearching for recipes: '{query}'")
    
    # Search for recipes (this would use your existing retrieval system)
    # For this example, we'll use mock data
    mock_recipes = [
        {
            "id": "recipe_1",
            "title": "Creamy Butternut Squash Soup",
            "description": "A warm and comforting soup perfect for fall evenings",
            "ingredients": "Butternut squash, cream, spices",
            "instructions": "Roast squash, blend with cream and spices",
            "image_url": "https://example.com/butternut-soup.jpg",
            "url": "https://example.com/recipe1"
        },
        {
            "id": "recipe_2", 
            "title": "Hearty Vegetable Stew",
            "description": "A robust stew with seasonal vegetables",
            "ingredients": "Mixed vegetables, broth, herbs",
            "instructions": "Simmer vegetables in broth with herbs",
            "image_url": "https://example.com/vegetable-stew.jpg",
            "url": "https://example.com/recipe2"
        }
    ]
    
    print(f"Found {len(mock_recipes)} recipes")
    
    # Generate article content with hotlinked images
    print("\nGenerating article content...")
    article_content = generate_article(query, mock_recipes)
    
    print("Article content generated!")
    print(f"Content length: {len(article_content)} characters")
    
    # Create WordPress post with hotlinked images in content
    print(f"\nCreating WordPress post with hotlinked images in content...")
    
    try:
        result = create_wordpress_post_with_hotlinks(
            wp_site_url=WP_SITE_URL,
            wp_username=WP_USERNAME,
            wp_password=WP_PASSWORD,
            title=f"Article: {query}",
            content=article_content
        )
        
        print("✅ WordPress post created successfully!")
        print(f"Post ID: {result.get('id')}")
        print(f"Post URL: {result.get('link')}")
        print(f"Status: {result.get('status')}")
        
        # Show information about external images in the post
        from tools.wordpress_integration import WordPressHotlinkIntegration
        wp_integration = WordPressHotlinkIntegration(WP_SITE_URL, WP_USERNAME, WP_PASSWORD)
        image_urls = wp_integration.get_image_hotlinks_from_content(article_content)
        print(f"External images in content: {len(image_urls)}")
        for url in image_urls:
            print(f"  - {url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create WordPress post: {e}")
        return False


def validate_image_urls_example():
    """Example of validating image URLs before posting."""
    
    # Example image URLs to validate
    test_urls = [
        "https://example.com/valid-image.jpg",
        "https://example.com/another-image.png",
        "https://invalid-url.com/missing-image.jpg"
    ]
    
    print("Validating image URLs...")
    
    from tools.wordpress_integration import WordPressHotlinkIntegration
    
    # Create integration instance (you'd use real credentials)
    wp_integration = WordPressHotlinkIntegration(
        wp_site_url="https://your-site.com",
        wp_username="username", 
        wp_password="password"
    )
    
    for url in test_urls:
        is_valid = wp_integration.validate_image_url(url)
        status = "✅ Valid" if is_valid else "❌ Invalid"
        print(f"{status}: {url}")


def process_content_example():
    """Example of processing content for hotlinking."""
    
    # Example HTML content with images
    sample_content = """
    <h2>Creamy Butternut Squash Soup</h2>
    <img src="https://example.com/butternut-soup.jpg" alt="Butternut squash soup" />
    <p>This warm and comforting soup is perfect for fall evenings.</p>
    
    <h2>Hearty Vegetable Stew</h2>
    <img src="https://example.com/vegetable-stew.jpg" alt="Vegetable stew" />
    <p>A robust stew with seasonal vegetables.</p>
    """
    
    print("Processing content for hotlinking...")
    print("Original content:")
    print(sample_content)
    
    from tools.wordpress_integration import WordPressHotlinkIntegration
    
    wp_integration = WordPressHotlinkIntegration(
        wp_site_url="https://your-site.com",
        wp_username="username",
        wp_password="password"
    )
    
    processed_content = wp_integration.process_content_for_hotlinking(sample_content)
    
    print("\nProcessed content:")
    print(processed_content)
    
    # Extract image URLs
    image_urls = wp_integration.get_image_hotlinks_from_content(processed_content)
    print(f"\nFound {len(image_urls)} image URLs:")
    for url in image_urls:
        print(f"  - {url}")


if __name__ == "__main__":
    print("WordPress Hotlinking Example")
    print("=" * 40)
    
    # Run examples
    print("\n1. WordPress Post Creation Example")
    print("-" * 30)
    # Uncomment to run with real credentials
    # example_wordpress_hotlinking()
    print("(Configure WP_SITE_URL, WP_USERNAME, WP_PASSWORD to run)")
    
    print("\n2. Image URL Validation Example")
    print("-" * 30)
    validate_image_urls_example()
    
    print("\n3. Content Processing Example")
    print("-" * 30)
    process_content_example()
    
    print("\n" + "=" * 40)
    print("Examples completed!")
    print("\nTo use with real WordPress:")
    print("1. Install the WordPress plugin snippet")
    print("2. Configure your WordPress credentials")
    print("3. Run the example_wordpress_hotlinking() function")
