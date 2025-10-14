<?php
/**
 * Plugin Name: Content Image Hotlinking
 * Description: Ensures external images in post content are displayed without downloading to media library
 * Version: 1.0.0
 * Author: Your Name
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class ContentImageHotlinking {
    
    public function __construct() {
        add_action('init', array($this, 'init'));
    }
    
    public function init() {
        // Add filters to ensure external images are displayed properly
        add_filter('the_content', array($this, 'process_content_images'), 10);
        add_filter('wp_get_attachment_image_src', array($this, 'handle_external_images'), 10, 4);
        
        // Add REST API support for external images
        add_action('rest_api_init', array($this, 'register_rest_fields'));
        
        // Add admin notice about hotlinking
        add_action('admin_notices', array($this, 'admin_notice'));
    }
    
    public function process_content_images($content) {
        // Process content to ensure external images are properly displayed
        // This function ensures that <img src="external_url"> tags work correctly
        
        // Add loading="lazy" to external images for better performance
        $content = preg_replace_callback(
            '/<img([^>]*?)src=["\']([^"\']*?)["\']([^>]*?)>/i',
            array($this, 'enhance_external_image_tag'),
            $content
        );
        
        return $content;
    }
    
    public function enhance_external_image_tag($matches) {
        $before_src = $matches[1];
        $src = $matches[2];
        $after_src = $matches[3];
        
        // Check if this is an external URL
        if (strpos($src, 'http') === 0 && strpos($src, home_url()) === false) {
            // Add data attributes to identify external images
            $enhanced_attributes = ' data-external-image="true" data-hotlink="true"';
            
            // Add loading="lazy" if not already present
            if (strpos($before_src . $after_src, 'loading=') === false) {
                $enhanced_attributes .= ' loading="lazy"';
            }
            
            // Add error handling for broken external images
            $enhanced_attributes .= ' onerror="this.style.display=\'none\'"';
            
            return '<img' . $before_src . 'src="' . esc_url($src) . '"' . $after_src . $enhanced_attributes . '>';
        }
        
        return $matches[0];
    }
    
    public function handle_external_images($image, $attachment_id, $size, $icon) {
        // This prevents WordPress from trying to process external URLs as attachments
        // External images should be handled directly in content
        return $image;
    }
    
    public function register_rest_fields() {
        // Add REST API field to identify posts with external images
        register_rest_field('post', 'has_external_images', array(
            'get_callback' => array($this, 'get_external_images_info'),
            'schema' => array(
                'description' => 'Information about external images in post content',
                'type' => 'object',
                'context' => array('view', 'edit')
            )
        ));
    }
    
    public function get_external_images_info($post) {
        $content = get_post_field('post_content', $post['id']);
        $external_images = $this->extract_external_image_urls($content);
        
        return array(
            'has_external_images' => !empty($external_images),
            'external_image_count' => count($external_images),
            'external_image_urls' => $external_images
        );
    }
    
    public function extract_external_image_urls($content) {
        $external_urls = array();
        
        // Find all img tags with external URLs
        preg_match_all('/<img[^>]*src=["\']([^"\']*?)["\'][^>]*>/i', $content, $matches);
        
        if (!empty($matches[1])) {
            foreach ($matches[1] as $url) {
                // Check if URL is external (not from this site)
                if (strpos($url, 'http') === 0 && strpos($url, home_url()) === false) {
                    $external_urls[] = esc_url($url);
                }
            }
        }
        
        return array_unique($external_urls);
    }
    
    public function admin_notice() {
        // Show admin notice about hotlinking functionality
        $screen = get_current_screen();
        if ($screen && $screen->base === 'post') {
            ?>
            <div class="notice notice-info">
                <p>
                    <strong>Content Image Hotlinking:</strong> 
                    External images in your content will be displayed directly from their original sources 
                    without being downloaded to your media library.
                </p>
            </div>
            <?php
        }
    }
}

// Initialize the plugin
new ContentImageHotlinking();

// Add CSS for better external image display
add_action('wp_head', function() {
    ?>
    <style>
    img[data-external-image="true"] {
        max-width: 100%;
        height: auto;
        border: 1px solid #ddd;
        border-radius: 4px;
    }
    
    img[data-external-image="true"]:hover {
        border-color: #0073aa;
    }
    </style>
    <?php
});

// Add JavaScript for better external image handling
add_action('wp_footer', function() {
    ?>
    <script>
    // Handle broken external images gracefully
    document.addEventListener('DOMContentLoaded', function() {
        const externalImages = document.querySelectorAll('img[data-external-image="true"]');
        
        externalImages.forEach(function(img) {
            img.addEventListener('error', function() {
                this.style.display = 'none';
                console.log('External image failed to load:', this.src);
            });
            
            img.addEventListener('load', function() {
                console.log('External image loaded successfully:', this.src);
            });
        });
    });
    </script>
    <?php
});
?>
