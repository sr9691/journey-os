<?php
/**
 * Brain Content Manager
 *
 * Handles all operations for brain content (URLs, text, files).
 *
 * @package Journey_Circle
 */

class Brain_Content_Manager {

    /**
     * Add brain content to a service area.
     *
     * @since 1.0.0
     * @param int   $service_area_id Service area ID.
     * @param array $args            Brain content arguments.
     * @return int|WP_Error Content ID on success, WP_Error on failure.
     */
    public function add_content( $service_area_id, $args ) {
        // Validate required fields
        if ( empty( $args['type'] ) ) {
            return new WP_Error( 'missing_type', 'Content type is required' );
        }
        
        if ( empty( $args['value'] ) ) {
            return new WP_Error( 'missing_value', 'Content value is required' );
        }
        
        // Validate content type
        $allowed_types = array( 'url', 'text', 'file' );
        if ( ! in_array( $args['type'], $allowed_types ) ) {
            return new WP_Error( 'invalid_type', 'Invalid content type' );
        }
        
        // Validate URL if type is url
        if ( $args['type'] === 'url' && ! filter_var( $args['value'], FILTER_VALIDATE_URL ) ) {
            return new WP_Error( 'invalid_url', 'Invalid URL format' );
        }
        
        // Default values
        $defaults = array(
            'type'  => '',
            'value' => '',
            'title' => '',
        );
        
        $args = wp_parse_args( $args, $defaults );
        
        // Generate title if not provided
        if ( empty( $args['title'] ) ) {
            $args['title'] = $this->generate_title( $args['type'], $args['value'] );
        }
        
        // Create brain content post
        $post_data = array(
            'post_title'   => sanitize_text_field( $args['title'] ),
            'post_content' => $args['type'] === 'text' ? wp_kses_post( $args['value'] ) : '',
            'post_type'    => 'jc_brain_content',
            'post_status'  => 'publish',
        );
        
        $content_id = wp_insert_post( $post_data );
        
        if ( is_wp_error( $content_id ) ) {
            return $content_id;
        }
        
        // Set meta data
        update_post_meta( $content_id, '_jc_service_area_id', absint( $service_area_id ) );
        update_post_meta( $content_id, '_jc_content_type', sanitize_text_field( $args['type'] ) );
        
        if ( $args['type'] === 'url' ) {
            update_post_meta( $content_id, '_jc_url', esc_url_raw( $args['value'] ) );
        } elseif ( $args['type'] === 'file' ) {
            update_post_meta( $content_id, '_jc_file_path', sanitize_text_field( $args['value'] ) );
        }
        
        // Also store in custom table for better querying
        $this->store_in_table( $service_area_id, $args['type'], $args['value'] );
        
        return $content_id;
    }
    
    /**
     * Get all brain content for a service area.
     *
     * @since 1.0.0
     * @param int $service_area_id Service area ID.
     * @return array Array of brain content items.
     */
    public function get_by_service_area( $service_area_id ) {
        $args = array(
            'post_type'      => 'jc_brain_content',
            'posts_per_page' => -1,
            'post_status'    => 'publish',
            'meta_query'     => array(
                array(
                    'key'     => '_jc_service_area_id',
                    'value'   => absint( $service_area_id ),
                    'compare' => '='
                )
            )
        );
        
        $query = new WP_Query( $args );
        $content_items = array();
        
        if ( $query->have_posts() ) {
            while ( $query->have_posts() ) {
                $query->the_post();
                $post = get_post();
                $type = get_post_meta( $post->ID, '_jc_content_type', true );
                
                $value = '';
                if ( $type === 'url' ) {
                    $value = get_post_meta( $post->ID, '_jc_url', true );
                } elseif ( $type === 'text' ) {
                    $value = $post->post_content;
                } elseif ( $type === 'file' ) {
                    $value = get_post_meta( $post->ID, '_jc_file_path', true );
                }
                
                $content_items[] = array(
                    'id'    => $post->ID,
                    'title' => $post->post_title,
                    'type'  => $type,
                    'value' => $value,
                );
            }
            wp_reset_postdata();
        }
        
        return $content_items;
    }
    
    /**
     * Delete brain content.
     *
     * @since 1.0.0
     * @param int $content_id Content ID.
     * @return bool True on success, false on failure.
     */
    public function delete( $content_id ) {
        $post = get_post( $content_id );
        
        if ( ! $post || $post->post_type !== 'jc_brain_content' ) {
            return false;
        }
        
        // If it's a file, delete the file
        $type = get_post_meta( $content_id, '_jc_content_type', true );
        if ( $type === 'file' ) {
            $file_path = get_post_meta( $content_id, '_jc_file_path', true );
            if ( file_exists( $file_path ) ) {
                @unlink( $file_path );
            }
        }
        
        $result = wp_delete_post( $content_id, true );
        
        return $result !== false;
    }
    
    /**
     * Upload a file and add it as brain content.
     *
     * @since 1.0.0
     * @param int   $service_area_id Service area ID.
     * @param array $file            $_FILES array element.
     * @return int|WP_Error Content ID on success, WP_Error on failure.
     */
    public function upload_file( $service_area_id, $file ) {
        // Validate file
        if ( ! isset( $file['tmp_name'] ) || ! is_uploaded_file( $file['tmp_name'] ) ) {
            return new WP_Error( 'invalid_file', 'Invalid file upload' );
        }
        
        // Check file size (10MB max)
        $max_size = 10 * 1024 * 1024; // 10MB
        if ( $file['size'] > $max_size ) {
            return new WP_Error( 'file_too_large', 'File size exceeds 10MB limit' );
        }
        
        // Allowed file types
        $allowed_types = array(
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/html',
        );
        
        $finfo = finfo_open( FILEINFO_MIME_TYPE );
        $mime_type = finfo_file( $finfo, $file['tmp_name'] );
        finfo_close( $finfo );
        
        if ( ! in_array( $mime_type, $allowed_types ) ) {
            return new WP_Error( 'invalid_file_type', 'File type not allowed' );
        }
        
        // Use WordPress upload handler
        require_once( ABSPATH . 'wp-admin/includes/file.php' );
        
        $upload_overrides = array(
            'test_form' => false,
            'test_type' => true,
        );
        
        $uploaded_file = wp_handle_upload( $file, $upload_overrides );
        
        if ( isset( $uploaded_file['error'] ) ) {
            return new WP_Error( 'upload_error', $uploaded_file['error'] );
        }
        
        // Add file as brain content
        return $this->add_content( $service_area_id, array(
            'type'  => 'file',
            'value' => $uploaded_file['file'],
            'title' => $file['name'],
        ) );
    }
    
    /**
     * Extract text content from a file.
     *
     * @since 1.0.0
     * @param string $file_path File path.
     * @return string|WP_Error Extracted text or WP_Error on failure.
     */
    public function extract_file_content( $file_path ) {
        if ( ! file_exists( $file_path ) ) {
            return new WP_Error( 'file_not_found', 'File not found' );
        }
        
        $mime_type = mime_content_type( $file_path );
        
        switch ( $mime_type ) {
            case 'text/plain':
            case 'text/html':
                return file_get_contents( $file_path );
                
            case 'application/pdf':
                // Note: PDF extraction requires additional library (e.g., pdftotext)
                // For now, return a placeholder
                return '[PDF content - extraction not yet implemented]';
                
            case 'application/msword':
            case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                // Note: DOCX extraction requires additional library
                return '[DOCX content - extraction not yet implemented]';
                
            default:
                return new WP_Error( 'unsupported_type', 'Unsupported file type for content extraction' );
        }
    }
    
    /**
     * Fetch content from a URL.
     *
     * @since 1.0.0
     * @param string $url URL to fetch.
     * @return string|WP_Error Fetched content or WP_Error on failure.
     */
    public function fetch_url_content( $url ) {
        $response = wp_remote_get( $url, array(
            'timeout' => 30,
        ) );
        
        if ( is_wp_error( $response ) ) {
            return $response;
        }
        
        $body = wp_remote_retrieve_body( $response );
        
        // Strip HTML tags for text content
        $body = wp_strip_all_tags( $body );
        
        return $body;
    }
    
    /**
     * Store content in custom database table.
     *
     * @since 1.0.0
     * @param int    $service_area_id Service area ID.
     * @param string $type            Content type.
     * @param string $value           Content value.
     * @return int|false Insert ID on success, false on failure.
     */
    private function store_in_table( $service_area_id, $type, $value ) {
        global $wpdb;
        
        $table_name = $wpdb->prefix . 'jc_brain_content_data';
        
        $result = $wpdb->insert(
            $table_name,
            array(
                'service_area_id' => absint( $service_area_id ),
                'content_type'    => sanitize_text_field( $type ),
                'content_value'   => $type === 'text' ? wp_kses_post( $value ) : sanitize_text_field( $value ),
            ),
            array( '%d', '%s', '%s' )
        );
        
        if ( $result === false ) {
            return false;
        }
        
        return $wpdb->insert_id;
    }
    
    /**
     * Generate a title for brain content based on type and value.
     *
     * @since 1.0.0
     * @param string $type  Content type.
     * @param string $value Content value.
     * @return string Generated title.
     */
    private function generate_title( $type, $value ) {
        switch ( $type ) {
            case 'url':
                $parsed = parse_url( $value );
                return isset( $parsed['host'] ) ? $parsed['host'] : 'Untitled URL';
                
            case 'text':
                $excerpt = wp_trim_words( $value, 10 );
                return ! empty( $excerpt ) ? $excerpt : 'Untitled Text';
                
            case 'file':
                return basename( $value );
                
            default:
                return 'Untitled Content';
        }
    }
}
