# WordPress Content Image Hotlinking Solution

This guide explains how to fix the image downloading issue in your WordPress integration. The solution ensures that images within article content are hotlinked (embedded as external URLs) rather than downloaded and stored in WordPress media library.

## Problem

Currently, when drafting to WordPress, images within the article content are being downloaded from the original source and stored on the destination site. This causes:
- Duplicate storage across multiple sites
- Unnecessary bandwidth usage
- Storage space waste
- Potential copyright issues

## Solution Overview

The solution implements a **content image hotlinking system** that:
1. ✅ Preserves original image URLs from your database
2. ✅ Embeds images directly via `<img src="original_url">` in article content
3. ✅ Processes content to ensure all images use hotlinking
4. ✅ Avoids `media_sideload_image()` and `wp_upload_bits()` entirely
5. ✅ Validates image accessibility before posting

## Files Created/Modified

### New Files
- `tools/wordpress_integration.py` - WordPress API integration with content image hotlinking
- `wordpress-content-hotlinking.php` - WordPress plugin for content image hotlinking
- `scripts/wordpress_hotlink_example.py` - Usage examples
- `WORDPRESS_HOTLINKING_GUIDE.md` - This guide

### Modified Files
- `api_server.py` - Added image validation and content processing endpoints

## Implementation Steps

### 1. Install WordPress Plugin

Copy the contents of `wordpress-content-hotlinking.php` into a new WordPress plugin file:

```php
// Create: wp-content/plugins/content-image-hotlinking/content-image-hotlinking.php
// Copy the entire content from wordpress-content-hotlinking.php
```

Activate the plugin in your WordPress admin.

### 2. Configure WordPress Credentials

Update your WordPress integration with proper credentials:

```python
# In your application
WP_SITE_URL = "https://your-wordpress-site.com"
WP_USERNAME = "your-username" 
WP_PASSWORD = "your-app-password"  # Use Application Password, not regular password
```

**Important**: Use WordPress Application Passwords, not your regular login password.

### 3. Use the WordPress Integration

```python
from tools.wordpress_integration import create_wordpress_post_with_hotlinks

# Create a post with hotlinked images in content
result = create_wordpress_post_with_hotlinks(
    wp_site_url="https://your-site.com",
    wp_username="your-username",
    wp_password="your-app-password",
    title="Your Article Title",
    content=article_content  # HTML with <img src="external_url"> tags
)
```

### 4. Process Content for Hotlinking

Your existing content generation already creates hotlinked images, but you can ensure proper processing:

```python
from tools.wordpress_integration import WordPressHotlinkIntegration

wp_integration = WordPressHotlinkIntegration(wp_site_url, wp_username, wp_password)

# Process content to ensure hotlinking
processed_content = wp_integration.process_content_for_hotlinking(content)

# Validate image URLs
for image_url in wp_integration.get_image_hotlinks_from_content(content):
    if wp_integration.validate_image_url(image_url):
        print(f"✅ Image accessible: {image_url}")
    else:
        print(f"❌ Image not accessible: {image_url}")
```

## API Endpoints

Your server now provides these endpoints for WordPress integration:

### Validate Image
```bash
POST /api/wordpress/validate-image
Content-Type: application/json

{
  "url": "https://example.com/image.jpg"
}
```

### Process Content for Hotlinking
```bash
POST /api/wordpress/hotlink-content
Content-Type: application/json

{
  "content": "<img src=\"https://example.com/image.jpg\" alt=\"Image\" />"
}
```

## How It Works

### 1. Image URL Extraction
Your existing `extract_remote_image_url()` function already extracts URLs from your database without downloading.

### 2. HTML Generation
The `build_remote_image_figure()` function creates HTML with external URLs:

```html
<figure data-image-hotlink="true" data-external-source="airtable">
  <img src="https://original-url.com/image.jpg" alt="Recipe Title" />
  <figcaption>Image credit: original-url.com</figcaption>
</figure>
```

### 3. WordPress Post Creation
The integration creates WordPress posts with:
- Content containing `<img src="external_url">` tags
- All images processed for hotlinking
- Validation of all image URLs before posting
- No proxying or rewriting that would trigger WordPress uploads

### 4. WordPress Display
The WordPress plugin:
- Processes content to ensure external images display properly
- Adds data attributes to identify external images
- Handles broken external images gracefully

## Key Features

### ✅ No Downloads
- Images are never downloaded to WordPress
- All images remain on original servers
- No media library storage used

### ✅ Validation
- Image URLs are validated before posting
- Accessibility checks ensure images load properly
- Blocked domains are filtered out

### ✅ Content Processing
- All images in content are processed for hotlinking
- Data attributes added for tracking external images
- Graceful handling of broken external images
- HTML content is processed to ensure hotlinking
- Image URLs extracted for validation

## Testing

Run the example script to test the integration:

```bash
python scripts/wordpress_hotlink_example.py
```

This will:
1. Validate your WordPress setup
2. Test image URL validation
3. Process sample content for hotlinking
4. Show how to create posts with external images

## Troubleshooting

### Images Not Displaying
1. Check if image URLs are accessible
2. Verify WordPress plugin is active
3. Check for CORS issues (use proxy endpoint if needed)

### WordPress API Errors
1. Verify credentials and permissions
2. Check if REST API is enabled
3. Ensure Application Password is used

### Content Processing Issues
1. Verify HTML content has proper `<img>` tags
2. Check that URLs are absolute (http/https)
3. Test image validation endpoint

## Benefits

- **Storage Savings**: No duplicate images across sites
- **Bandwidth Efficiency**: Images served from original sources
- **Copyright Compliance**: Original attribution preserved
- **Performance**: Faster posting (no downloads)
- **Scalability**: Works with any number of images

## Migration

If you have existing posts with downloaded images, you can:

1. Update post content to use external URLs instead of media library images
2. Remove downloaded images from media library (optional)
3. The plugin will automatically process external images in content

The solution is backward compatible and won't affect existing functionality.
