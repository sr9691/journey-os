<?php
/**
 * Journey Circle Page Controller
 * 
 * Handles the Journey Circle Creator admin page
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0
 */

if (!defined('ABSPATH')) {
    exit;
}

class DR_Journey_Circle_Page {
    
    /**
     * Constructor
     */
    public function __construct() {
        add_action('admin_menu', array($this, 'register_page'), 20);
        add_action('admin_enqueue_scripts', array($this, 'enqueue_assets'));
        add_action('wp_ajax_dr_upload_brain_content', array($this, 'handle_brain_content_upload'));
    }
    
    /**
     * Register admin page
     */
    public function register_page() {
        add_submenu_page(
            'dr-campaign-builder',
            __('Journey Circle Creator', 'directreach-campaign-builder'),
            __('Journey Circle', 'directreach-campaign-builder'),
            'manage_campaigns',
            'dr-journey-circle',
            array($this, 'render_page'),
            15
        );
    }
    
    /**
     * Enqueue assets
     */
    public function enqueue_assets($hook) {
        // Only load on Journey Circle page
        if ('directreach-campaign-builder_page_dr-journey-circle' !== $hook) {
            return;
        }
        
        // CSS
        wp_enqueue_style(
            'dr-journey-circle',
            plugins_url('admin/css/journey-circle.css', dirname(__FILE__, 2)),
            array(),
            '2.0.0'
        );
        
        // JavaScript - Core workflow
        wp_enqueue_script(
            'dr-journey-circle-workflow',
            plugins_url('admin/js/modules/journey-circle-workflow.js', dirname(__FILE__, 2)),
            array('jquery'),
            '2.0.0',
            true
        );
        
        // JavaScript - Brain Content Manager
        wp_enqueue_script(
            'dr-brain-content-manager',
            plugins_url('admin/js/modules/brain-content-manager.js', dirname(__FILE__, 2)),
            array('jquery', 'dr-journey-circle-workflow'),
            '2.0.0',
            true
        );
        
        // JavaScript - Service Area Manager
        wp_enqueue_script(
            'dr-service-area-manager',
            plugins_url('admin/js/modules/service-area-manager.js', dirname(__FILE__, 2)),
            array('jquery', 'dr-journey-circle-workflow'),
            '2.0.0',
            true
        );
        
        // JavaScript - Journey Circle Renderer (canvas visualization)
        wp_enqueue_script(
            'dr-journey-circle-renderer',
            plugins_url('admin/js/modules/journey-circle-renderer.js', dirname(__FILE__, 2)),
            array('jquery', 'dr-journey-circle-workflow'),
            '2.0.0',
            true
        );
        
        // Font Awesome (if not already loaded)
        wp_enqueue_style(
            'font-awesome',
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
            array(),
            '6.4.0'
        );
    }
    
    /**
     * Render page
     */
    public function render_page() {
        // Check user capabilities
        if (!current_user_can('manage_campaigns')) {
            wp_die(__('You do not have sufficient permissions to access this page.'));
        }
        
        // Load the template
        $template_path = plugin_dir_path(dirname(__FILE__)) . 'admin/views/journey-circle/journey-circle-creator.php';
        
        if (file_exists($template_path)) {
            include $template_path;
        } else {
            echo '<div class="wrap">';
            echo '<h1>' . esc_html__('Journey Circle Creator', 'directreach-campaign-builder') . '</h1>';
            echo '<p>' . esc_html__('Template file not found.', 'directreach-campaign-builder') . '</p>';
            echo '</div>';
        }
    }
    
    /**
     * Handle brain content file upload
     */
    public function handle_brain_content_upload() {
        // Check nonce
        check_ajax_referer('dr_journey_circle_nonce', 'nonce');
        
        // Check user capabilities
        if (!current_user_can('manage_campaigns')) {
            wp_send_json_error(array('message' => __('Permission denied', 'directreach-campaign-builder')));
        }
        
        // Check if file was uploaded
        if (empty($_FILES['file'])) {
            wp_send_json_error(array('message' => __('No file uploaded', 'directreach-campaign-builder')));
        }
        
        $file = $_FILES['file'];
        $client_id = isset($_POST['client_id']) ? absint($_POST['client_id']) : 0;
        
        if (!$client_id) {
            wp_send_json_error(array('message' => __('Invalid client ID', 'directreach-campaign-builder')));
        }
        
        // Validate file type
        $allowed_types = array(
            'pdf'  => 'application/pdf',
            'doc'  => 'application/msword',
            'docx' => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'txt'  => 'text/plain'
        );
        
        $file_type = wp_check_filetype($file['name'], $allowed_types);
        
        if (!in_array($file_type['type'], $allowed_types)) {
            wp_send_json_error(array(
                'message' => __('File type not allowed', 'directreach-campaign-builder')
            ));
        }
        
        // Validate file size
        $max_size = wp_max_upload_size();
        if ($file['size'] > $max_size) {
            wp_send_json_error(array(
                'message' => sprintf(
                    __('File size exceeds maximum allowed size of %s', 'directreach-campaign-builder'),
                    size_format($max_size)
                )
            ));
        }
        
        // Upload file
        require_once(ABSPATH . 'wp-admin/includes/file.php');
        require_once(ABSPATH . 'wp-admin/includes/media.php');
        require_once(ABSPATH . 'wp-admin/includes/image.php');
        
        $upload = wp_handle_upload($file, array('test_form' => false));
        
        if (isset($upload['error'])) {
            wp_send_json_error(array('message' => $upload['error']));
        }
        
        // Create attachment
        $attachment_data = array(
            'post_title'     => sanitize_file_name($file['name']),
            'post_content'   => '',
            'post_status'    => 'inherit',
            'post_mime_type' => $file_type['type']
        );
        
        $attachment_id = wp_insert_attachment($attachment_data, $upload['file']);
        
        if (is_wp_error($attachment_id)) {
            wp_send_json_error(array('message' => $attachment_id->get_error_message()));
        }
        
        // Generate attachment metadata
        $attachment_metadata = wp_generate_attachment_metadata($attachment_id, $upload['file']);
        wp_update_attachment_metadata($attachment_id, $attachment_metadata);
        
        // Return success
        wp_send_json_success(array(
            'id'  => $attachment_id,
            'url' => $upload['url'],
            'file' => $upload['file'],
            'type' => $file_type['type']
        ));
    }
}

// Initialize
new DR_Journey_Circle_Page();
