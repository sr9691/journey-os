<?php
/**
 * AI Content Controller Extension - Iteration 9
 * 
 * Extends the existing DR_AI_Content_Controller class with endpoints for
 * outline generation, content generation, revision, and asset CRUD.
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Add these routes and methods to the existing DR_AI_Content_Controller class
 * in /includes/api/class-ai-content-controller.php
 * 
 * Add the route registrations to the existing register_routes() method.
 */

// ============================================================================
// ROUTE REGISTRATIONS - Add to register_routes() method
// ============================================================================

/*
 * Add these route registrations to your existing register_routes() method:
 */

// Outline generation
register_rest_route($this->namespace, '/ai/generate-outline', array(
    'methods'             => WP_REST_Server::CREATABLE,
    'callback'            => array($this, 'generate_outline'),
    'permission_callback' => array($this, 'check_permissions'),
    'args'                => $this->get_outline_args(),
));

// Outline revision
register_rest_route($this->namespace, '/ai/revise-outline', array(
    'methods'             => WP_REST_Server::CREATABLE,
    'callback'            => array($this, 'revise_outline'),
    'permission_callback' => array($this, 'check_permissions'),
    'args'                => array(
        'asset_id' => array(
            'required'          => true,
            'type'              => 'integer',
            'sanitize_callback' => 'absint',
        ),
        'current_outline' => array(
            'required'          => true,
            'type'              => 'string',
            'sanitize_callback' => 'sanitize_textarea_field',
        ),
        'feedback' => array(
            'required'          => true,
            'type'              => 'string',
            'sanitize_callback' => 'sanitize_textarea_field',
        ),
    ),
));

// Content generation
register_rest_route($this->namespace, '/ai/generate-content', array(
    'methods'             => WP_REST_Server::CREATABLE,
    'callback'            => array($this, 'generate_content'),
    'permission_callback' => array($this, 'check_permissions'),
    'args'                => array(
        'asset_id' => array(
            'required'          => true,
            'type'              => 'integer',
            'sanitize_callback' => 'absint',
        ),
        'outline' => array(
            'required'          => true,
            'type'              => 'string',
            'sanitize_callback' => 'sanitize_textarea_field',
        ),
    ),
));

// Content revision
register_rest_route($this->namespace, '/ai/revise-content', array(
    'methods'             => WP_REST_Server::CREATABLE,
    'callback'            => array($this, 'revise_content'),
    'permission_callback' => array($this, 'check_permissions'),
    'args'                => array(
        'asset_id' => array(
            'required'          => true,
            'type'              => 'integer',
            'sanitize_callback' => 'absint',
        ),
        'current_content' => array(
            'required'          => true,
            'type'              => 'string',
            // Don't sanitize - preserve HTML
        ),
        'feedback' => array(
            'required'          => true,
            'type'              => 'string',
            'sanitize_callback' => 'sanitize_textarea_field',
        ),
    ),
));

// Asset CRUD routes
register_rest_route($this->namespace, '/journey-circles/(?P<circle_id>\d+)/assets', array(
    array(
        'methods'             => WP_REST_Server::READABLE,
        'callback'            => array($this, 'get_assets'),
        'permission_callback' => array($this, 'check_permissions'),
        'args'                => array(
            'circle_id' => array(
                'required'          => true,
                'type'              => 'integer',
                'sanitize_callback' => 'absint',
            ),
        ),
    ),
    array(
        'methods'             => WP_REST_Server::CREATABLE,
        'callback'            => array($this, 'create_asset'),
        'permission_callback' => array($this, 'check_permissions'),
        'args'                => $this->get_create_asset_args(),
    ),
));

register_rest_route($this->namespace, '/journey-circles/(?P<circle_id>\d+)/assets/(?P<asset_id>\d+)', array(
    array(
        'methods'             => WP_REST_Server::READABLE,
        'callback'            => array($this, 'get_asset'),
        'permission_callback' => array($this, 'check_permissions'),
    ),
    array(
        'methods'             => WP_REST_Server::EDITABLE,
        'callback'            => array($this, 'update_asset'),
        'permission_callback' => array($this, 'check_permissions'),
        'args'                => $this->get_update_asset_args(),
    ),
    array(
        'methods'             => WP_REST_Server::DELETABLE,
        'callback'            => array($this, 'delete_asset'),
        'permission_callback' => array($this, 'check_permissions'),
    ),
));

// Approve asset
register_rest_route($this->namespace, '/journey-circles/(?P<circle_id>\d+)/assets/(?P<asset_id>\d+)/approve', array(
    'methods'             => WP_REST_Server::CREATABLE,
    'callback'            => array($this, 'approve_asset'),
    'permission_callback' => array($this, 'check_permissions'),
));

// Publish asset (add URL)
register_rest_route($this->namespace, '/journey-circles/(?P<circle_id>\d+)/assets/(?P<asset_id>\d+)/publish', array(
    'methods'             => WP_REST_Server::CREATABLE,
    'callback'            => array($this, 'publish_asset'),
    'permission_callback' => array($this, 'check_permissions'),
    'args'                => array(
        'url' => array(
            'required'          => true,
            'type'              => 'string',
            'sanitize_callback' => 'esc_url_raw',
        ),
    ),
));


// ============================================================================
// CALLBACK METHODS
// ============================================================================

/**
 * Generate outline endpoint callback.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response|WP_Error Response object.
 */
public function generate_outline($request) {
    $generator = new DR_AI_Content_Generator();
    
    $args = array(
        'journey_circle_id' => $request->get_param('journey_circle_id'),
        'linked_to_type'    => $request->get_param('linked_to_type'),
        'linked_to_id'      => $request->get_param('linked_to_id'),
        'asset_type'        => $request->get_param('asset_type'),
        'brain_content'     => $request->get_param('brain_content') ?: array(),
        'industries'        => $request->get_param('industries') ?: array(),
        'service_area_name' => $request->get_param('service_area_name') ?: '',
        'problem_title'     => $request->get_param('problem_title') ?: '',
        'solution_title'    => $request->get_param('solution_title') ?: '',
    );
    
    $result = $generator->generate_outline($args);
    
    if (is_wp_error($result)) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => $result->get_error_message(),
            'code'    => $result->get_error_code(),
        ), 400);
    }
    
    return new WP_REST_Response(array(
        'success'  => true,
        'outline'  => $result['outline'],
        'title'    => $result['title'],
        'asset_id' => $result['asset_id'],
        'cached'   => $result['cached'] ?? false,
    ), 200);
}

/**
 * Revise outline endpoint callback.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response|WP_Error Response object.
 */
public function revise_outline($request) {
    $generator = new DR_AI_Content_Generator();
    
    $args = array(
        'asset_id'        => $request->get_param('asset_id'),
        'current_outline' => $request->get_param('current_outline'),
        'feedback'        => $request->get_param('feedback'),
    );
    
    $result = $generator->revise_outline($args);
    
    if (is_wp_error($result)) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => $result->get_error_message(),
            'code'    => $result->get_error_code(),
        ), 400);
    }
    
    return new WP_REST_Response(array(
        'success'        => true,
        'outline'        => $result['outline'],
        'title'          => $result['title'],
        'revision_notes' => $result['revision_notes'] ?? '',
    ), 200);
}

/**
 * Generate content endpoint callback.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response|WP_Error Response object.
 */
public function generate_content($request) {
    $generator = new DR_AI_Content_Generator();
    
    $args = array(
        'asset_id' => $request->get_param('asset_id'),
        'outline'  => $request->get_param('outline'),
    );
    
    $result = $generator->generate_content($args);
    
    if (is_wp_error($result)) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => $result->get_error_message(),
            'code'    => $result->get_error_code(),
        ), 400);
    }
    
    return new WP_REST_Response(array(
        'success' => true,
        'content' => $result['content'],
        'title'   => $result['title'],
    ), 200);
}

/**
 * Revise content endpoint callback.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response|WP_Error Response object.
 */
public function revise_content($request) {
    $generator = new DR_AI_Content_Generator();
    
    // Get raw content to preserve HTML
    $params = $request->get_json_params();
    $current_content = isset($params['current_content']) ? $params['current_content'] : '';
    
    $args = array(
        'asset_id'        => $request->get_param('asset_id'),
        'current_content' => $current_content,
        'feedback'        => $request->get_param('feedback'),
    );
    
    $result = $generator->revise_content($args);
    
    if (is_wp_error($result)) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => $result->get_error_message(),
            'code'    => $result->get_error_code(),
        ), 400);
    }
    
    return new WP_REST_Response(array(
        'success' => true,
        'content' => $result['content'],
    ), 200);
}

/**
 * Get all assets for a journey circle.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response Response object.
 */
public function get_assets($request) {
    global $wpdb;
    
    $circle_id = $request->get_param('circle_id');
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    $assets = $wpdb->get_results($wpdb->prepare(
        "SELECT * FROM {$table} WHERE journey_circle_id = %d ORDER BY linked_to_type, linked_to_id",
        $circle_id
    ));
    
    // Format for response
    $formatted = array();
    foreach ($assets as $asset) {
        $formatted[] = $this->format_asset_for_response($asset);
    }
    
    return new WP_REST_Response(array(
        'success' => true,
        'assets'  => $formatted,
        'count'   => count($formatted),
    ), 200);
}

/**
 * Get single asset.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response Response object.
 */
public function get_asset($request) {
    global $wpdb;
    
    $asset_id = $request->get_param('asset_id');
    $circle_id = $request->get_param('circle_id');
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    $asset = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$table} WHERE id = %d AND journey_circle_id = %d",
        $asset_id,
        $circle_id
    ));
    
    if (!$asset) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => __('Asset not found.', 'directreach'),
        ), 404);
    }
    
    return new WP_REST_Response(array(
        'success' => true,
        'asset'   => $this->format_asset_for_response($asset),
    ), 200);
}

/**
 * Create new asset.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response Response object.
 */
public function create_asset($request) {
    global $wpdb;
    
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    $data = array(
        'journey_circle_id' => absint($request->get_param('circle_id')),
        'linked_to_type'    => sanitize_text_field($request->get_param('linked_to_type')),
        'linked_to_id'      => absint($request->get_param('linked_to_id')),
        'asset_type'        => sanitize_text_field($request->get_param('asset_type')),
        'title'             => sanitize_text_field($request->get_param('title') ?: ''),
        'status'            => 'outline',
        'created_at'        => current_time('mysql'),
        'updated_at'        => current_time('mysql'),
    );
    
    // Validate linked_to_type
    if (!in_array($data['linked_to_type'], array('problem', 'solution'), true)) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => __('Invalid linked_to_type.', 'directreach'),
        ), 400);
    }
    
    // Validate asset_type
    if (!in_array($data['asset_type'], array('article_long', 'article_short', 'infographic', 'other'), true)) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => __('Invalid asset_type.', 'directreach'),
        ), 400);
    }
    
    // Check for existing asset with same parameters
    $existing = $wpdb->get_var($wpdb->prepare(
        "SELECT id FROM {$table} 
         WHERE journey_circle_id = %d 
         AND linked_to_type = %s 
         AND linked_to_id = %d 
         AND asset_type = %s",
        $data['journey_circle_id'],
        $data['linked_to_type'],
        $data['linked_to_id'],
        $data['asset_type']
    ));
    
    if ($existing) {
        return new WP_REST_Response(array(
            'success'  => false,
            'message'  => __('An asset with these parameters already exists.', 'directreach'),
            'asset_id' => (int) $existing,
        ), 409);
    }
    
    $result = $wpdb->insert($table, $data);
    
    if (!$result) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => __('Failed to create asset.', 'directreach'),
        ), 500);
    }
    
    $asset_id = $wpdb->insert_id;
    $asset = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$table} WHERE id = %d",
        $asset_id
    ));
    
    return new WP_REST_Response(array(
        'success' => true,
        'asset'   => $this->format_asset_for_response($asset),
    ), 201);
}

/**
 * Update asset.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response Response object.
 */
public function update_asset($request) {
    global $wpdb;
    
    $asset_id = $request->get_param('asset_id');
    $circle_id = $request->get_param('circle_id');
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    // Verify asset exists and belongs to circle
    $asset = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$table} WHERE id = %d AND journey_circle_id = %d",
        $asset_id,
        $circle_id
    ));
    
    if (!$asset) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => __('Asset not found.', 'directreach'),
        ), 404);
    }
    
    $update_data = array(
        'updated_at' => current_time('mysql'),
    );
    
    // Only update fields that were provided
    $params = $request->get_json_params();
    
    if (isset($params['title'])) {
        $update_data['title'] = sanitize_text_field($params['title']);
    }
    if (isset($params['outline'])) {
        $update_data['outline'] = sanitize_textarea_field($params['outline']);
    }
    if (isset($params['content'])) {
        $update_data['content'] = $params['content']; // HTML, sanitized on output
    }
    if (isset($params['url'])) {
        $update_data['url'] = esc_url_raw($params['url']);
    }
    if (isset($params['status'])) {
        $valid_statuses = array('outline', 'draft', 'approved', 'published');
        if (in_array($params['status'], $valid_statuses, true)) {
            $update_data['status'] = $params['status'];
        }
    }
    
    $result = $wpdb->update(
        $table,
        $update_data,
        array('id' => $asset_id)
    );
    
    if ($result === false) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => __('Failed to update asset.', 'directreach'),
        ), 500);
    }
    
    // Get updated asset
    $updated_asset = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$table} WHERE id = %d",
        $asset_id
    ));
    
    return new WP_REST_Response(array(
        'success' => true,
        'asset'   => $this->format_asset_for_response($updated_asset),
    ), 200);
}

/**
 * Delete asset.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response Response object.
 */
public function delete_asset($request) {
    global $wpdb;
    
    $asset_id = $request->get_param('asset_id');
    $circle_id = $request->get_param('circle_id');
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    // Verify asset exists and belongs to circle
    $asset = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$table} WHERE id = %d AND journey_circle_id = %d",
        $asset_id,
        $circle_id
    ));
    
    if (!$asset) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => __('Asset not found.', 'directreach'),
        ), 404);
    }
    
    $result = $wpdb->delete(
        $table,
        array('id' => $asset_id),
        array('%d')
    );
    
    if (!$result) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => __('Failed to delete asset.', 'directreach'),
        ), 500);
    }
    
    return new WP_REST_Response(array(
        'success' => true,
        'message' => __('Asset deleted successfully.', 'directreach'),
    ), 200);
}

/**
 * Approve asset endpoint callback.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response Response object.
 */
public function approve_asset($request) {
    $generator = new DR_AI_Content_Generator();
    
    $asset_id = $request->get_param('asset_id');
    $result = $generator->approve_asset($asset_id);
    
    if (is_wp_error($result)) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => $result->get_error_message(),
        ), 400);
    }
    
    return new WP_REST_Response(array(
        'success' => true,
        'message' => __('Asset approved successfully.', 'directreach'),
    ), 200);
}

/**
 * Publish asset endpoint callback.
 *
 * @param WP_REST_Request $request Request object.
 * @return WP_REST_Response Response object.
 */
public function publish_asset($request) {
    $generator = new DR_AI_Content_Generator();
    
    $asset_id = $request->get_param('asset_id');
    $url = $request->get_param('url');
    
    $result = $generator->publish_asset($asset_id, $url);
    
    if (is_wp_error($result)) {
        return new WP_REST_Response(array(
            'success' => false,
            'message' => $result->get_error_message(),
        ), 400);
    }
    
    return new WP_REST_Response(array(
        'success' => true,
        'message' => __('Asset published successfully.', 'directreach'),
    ), 200);
}


// ============================================================================
// HELPER METHODS
// ============================================================================

/**
 * Get argument schema for outline generation.
 *
 * @return array Argument schema.
 */
private function get_outline_args() {
    return array(
        'journey_circle_id' => array(
            'required'          => true,
            'type'              => 'integer',
            'sanitize_callback' => 'absint',
        ),
        'linked_to_type' => array(
            'required'          => true,
            'type'              => 'string',
            'enum'              => array('problem', 'solution'),
            'sanitize_callback' => 'sanitize_text_field',
        ),
        'linked_to_id' => array(
            'required'          => true,
            'type'              => 'integer',
            'sanitize_callback' => 'absint',
        ),
        'asset_type' => array(
            'required'          => true,
            'type'              => 'string',
            'enum'              => array('article_long', 'article_short', 'infographic'),
            'sanitize_callback' => 'sanitize_text_field',
        ),
        'brain_content' => array(
            'required' => false,
            'type'     => 'array',
            'default'  => array(),
        ),
        'industries' => array(
            'required' => false,
            'type'     => 'array',
            'default'  => array(),
        ),
        'service_area_name' => array(
            'required'          => false,
            'type'              => 'string',
            'default'           => '',
            'sanitize_callback' => 'sanitize_text_field',
        ),
        'problem_title' => array(
            'required'          => false,
            'type'              => 'string',
            'default'           => '',
            'sanitize_callback' => 'sanitize_text_field',
        ),
        'solution_title' => array(
            'required'          => false,
            'type'              => 'string',
            'default'           => '',
            'sanitize_callback' => 'sanitize_text_field',
        ),
    );
}

/**
 * Get argument schema for asset creation.
 *
 * @return array Argument schema.
 */
private function get_create_asset_args() {
    return array(
        'linked_to_type' => array(
            'required'          => true,
            'type'              => 'string',
            'enum'              => array('problem', 'solution'),
            'sanitize_callback' => 'sanitize_text_field',
        ),
        'linked_to_id' => array(
            'required'          => true,
            'type'              => 'integer',
            'sanitize_callback' => 'absint',
        ),
        'asset_type' => array(
            'required'          => true,
            'type'              => 'string',
            'enum'              => array('article_long', 'article_short', 'infographic', 'other'),
            'sanitize_callback' => 'sanitize_text_field',
        ),
        'title' => array(
            'required'          => false,
            'type'              => 'string',
            'default'           => '',
            'sanitize_callback' => 'sanitize_text_field',
        ),
    );
}

/**
 * Get argument schema for asset update.
 *
 * @return array Argument schema.
 */
private function get_update_asset_args() {
    return array(
        'title' => array(
            'required'          => false,
            'type'              => 'string',
            'sanitize_callback' => 'sanitize_text_field',
        ),
        'outline' => array(
            'required'          => false,
            'type'              => 'string',
            'sanitize_callback' => 'sanitize_textarea_field',
        ),
        'content' => array(
            'required' => false,
            'type'     => 'string',
            // No sanitize - preserve HTML
        ),
        'url' => array(
            'required'          => false,
            'type'              => 'string',
            'sanitize_callback' => 'esc_url_raw',
        ),
        'status' => array(
            'required'          => false,
            'type'              => 'string',
            'enum'              => array('outline', 'draft', 'approved', 'published'),
            'sanitize_callback' => 'sanitize_text_field',
        ),
    );
}

/**
 * Format asset for API response.
 *
 * @param object $asset Asset database row.
 * @return array Formatted asset data.
 */
private function format_asset_for_response($asset) {
    return array(
        'id'                => (int) $asset->id,
        'journey_circle_id' => (int) $asset->journey_circle_id,
        'linked_to_type'    => $asset->linked_to_type,
        'linked_to_id'      => (int) $asset->linked_to_id,
        'asset_type'        => $asset->asset_type,
        'title'             => $asset->title,
        'outline'           => $asset->outline,
        'content'           => $asset->content,
        'url'               => $asset->url,
        'status'            => $asset->status,
        'created_at'        => $asset->created_at,
        'updated_at'        => $asset->updated_at,
    );
}

/**
 * Check permissions for AI content endpoints.
 *
 * @param WP_REST_Request $request Request object.
 * @return bool|WP_Error True if user can access, error otherwise.
 */
public function check_permissions($request) {
    // Verify nonce
    $nonce = $request->get_header('X-WP-Nonce');
    if (!$nonce || !wp_verify_nonce($nonce, 'wp_rest')) {
        return new WP_Error(
            'rest_forbidden',
            __('Invalid nonce.', 'directreach'),
            array('status' => 403)
        );
    }
    
    // Check capability
    if (!current_user_can('manage_campaigns')) {
        return new WP_Error(
            'rest_forbidden',
            __('You do not have permission to access this resource.', 'directreach'),
            array('status' => 403)
        );
    }
    
    return true;
}
