<?php
/**
 * Plugin Name: External Featured Images
 * Description: Allows setting external URLs as featured images without downloading to media library
 * Version: 1.0.0
 * Author: Your Name
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class ExternalFeaturedImages {
    
    public function __construct() {
        add_action('init', array($this, 'init'));
    }
    
    public function init() {
        // Add meta box for external featured images
        add_action('add_meta_boxes', array($this, 'add_external_featured_image_meta_box'));
        
        // Save external featured image data
        add_action('save_post', array($this, 'save_external_featured_image'));
        
        // Display external featured image in admin
        add_filter('admin_post_thumbnail_html', array($this, 'display_external_featured_image'), 10, 2);
        
        // Display external featured image on frontend
        add_filter('post_thumbnail_html', array($this, 'display_external_featured_image_frontend'), 10, 5);
        
        // Add REST API support for external featured images
        add_action('rest_api_init', array($this, 'register_rest_fields'));
    }
    
    public function add_external_featured_image_meta_box() {
        add_meta_box(
            'external_featured_image',
            'External Featured Image',
            array($this, 'external_featured_image_meta_box_callback'),
            array('post', 'page'),
            'side',
            'high'
        );
    }
    
    public function external_featured_image_meta_box_callback($post) {
        wp_nonce_field('external_featured_image_nonce', 'external_featured_image_nonce');
        
        $external_url = get_post_meta($post->ID, '_featured_image_url', true);
        $use_external = get_post_meta($post->ID, '_use_external_featured_image', true);
        
        ?>
        <p>
            <label>
                <input type="checkbox" name="use_external_featured_image" value="1" <?php checked($use_external, '1'); ?> />
                Use external featured image
            </label>
        </p>
        <p>
            <label for="external_featured_image_url">External Image URL:</label><br>
            <input type="url" id="external_featured_image_url" name="external_featured_image_url" 
                   value="<?php echo esc_url($external_url); ?>" style="width: 100%;" />
        </p>
        <?php if ($external_url): ?>
        <p>
            <img src="<?php echo esc_url($external_url); ?>" style="max-width: 100%; height: auto;" 
                 alt="External featured image preview" />
        </p>
        <?php endif; ?>
        <?php
    }
    
    public function save_external_featured_image($post_id) {
        // Check nonce
        if (!isset($_POST['external_featured_image_nonce']) || 
            !wp_verify_nonce($_POST['external_featured_image_nonce'], 'external_featured_image_nonce')) {
            return;
        }
        
        // Check permissions
        if (!current_user_can('edit_post', $post_id)) {
            return;
        }
        
        // Save external featured image data
        if (isset($_POST['use_external_featured_image'])) {
            update_post_meta($post_id, '_use_external_featured_image', '1');
        } else {
            delete_post_meta($post_id, '_use_external_featured_image');
        }
        
        if (isset($_POST['external_featured_image_url']) && !empty($_POST['external_featured_image_url'])) {
            $url = esc_url_raw($_POST['external_featured_image_url']);
            update_post_meta($post_id, '_featured_image_url', $url);
        } else {
            delete_post_meta($post_id, '_featured_image_url');
        }
    }
    
    public function display_external_featured_image($content, $post_id) {
        $use_external = get_post_meta($post_id, '_use_external_featured_image', true);
        $external_url = get_post_meta($post_id, '_featured_image_url', true);
        
        if ($use_external && $external_url) {
            $content = '<div class="external-featured-image">';
            $content .= '<p><strong>External Featured Image:</strong></p>';
            $content .= '<img src="' . esc_url($external_url) . '" style="max-width: 100%; height: auto;" alt="External featured image" />';
            $content .= '<p><small>URL: ' . esc_url($external_url) . '</small></p>';
            $content .= '</div>';
        }
        
        return $content;
    }
    
    public function display_external_featured_image_frontend($html, $post_id, $post_thumbnail_id, $size, $attr) {
        $use_external = get_post_meta($post_id, '_use_external_featured_image', true);
        $external_url = get_post_meta($post_id, '_featured_image_url', true);
        
        if ($use_external && $external_url) {
            // Generate HTML for external featured image
            $attr = wp_parse_args($attr, array(
                'alt' => get_the_title($post_id),
                'loading' => 'lazy'
            ));
            
            $attr_string = '';
            foreach ($attr as $key => $value) {
                $attr_string .= ' ' . $key . '="' . esc_attr($value) . '"';
            }
            
            $html = '<img src="' . esc_url($external_url) . '"' . $attr_string . ' data-external-source="true" />';
        }
        
        return $html;
    }
    
    public function register_rest_fields() {
        register_rest_field('post', 'external_featured_image', array(
            'get_callback' => array($this, 'get_external_featured_image'),
            'update_callback' => array($this, 'update_external_featured_image'),
            'schema' => array(
                'description' => 'External featured image URL',
                'type' => 'string',
                'context' => array('view', 'edit')
            )
        ));
    }
    
    public function get_external_featured_image($post) {
        $use_external = get_post_meta($post['id'], '_use_external_featured_image', true);
        $external_url = get_post_meta($post['id'], '_featured_image_url', true);
        
        if ($use_external && $external_url) {
            return array(
                'url' => $external_url,
                'use_external' => true
            );
        }
        
        return null;
    }
    
    public function update_external_featured_image($value, $post) {
        if (isset($value['url']) && !empty($value['url'])) {
            update_post_meta($post->ID, '_featured_image_url', esc_url_raw($value['url']));
            update_post_meta($post->ID, '_use_external_featured_image', '1');
        } else {
            delete_post_meta($post->ID, '_featured_image_url');
            delete_post_meta($post->ID, '_use_external_featured_image');
        }
    }
}

// Initialize the plugin
new ExternalFeaturedImages();

// Add CSS for admin styling
add_action('admin_head', function() {
    ?>
    <style>
    .external-featured-image {
        border: 1px solid #ddd;
        padding: 10px;
        background: #f9f9f9;
        margin: 10px 0;
    }
    </style>
    <?php
});
?>
