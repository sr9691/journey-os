<?php
/**
 * Journey Solutions REST Controller
 *
 * Handles REST API endpoints for journey circle solutions and offers.
 * Part of Iteration 6: Steps 7-8 (Solution Titles & Offer Mapping)
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Class DR_Journey_Solutions_Controller
 *
 * REST API controller for managing journey circle solutions and offers.
 * Provides CRUD operations with validation for 1:1 problem-solution mapping
 * and multiple offers per solution.
 */
class DR_Journey_Solutions_Controller extends WP_REST_Controller {

    /**
     * API namespace
     *
     * @var string
     */
    protected $namespace = 'directreach/v2';

    /**
     * Base route for solutions
     *
     * @var string
     */
    protected $rest_base = 'journey-circles';

    /**
     * Constructor
     */
    public function __construct() {
        // Initialize if needed
    }

    /**
     * Register REST API routes
     *
     * @return void
     */
    public function register_routes() {
        // Solutions routes
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<circle_id>\d+)/solutions', array(
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'get_solutions'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => array(
                    'circle_id' => array(
                        'required'          => true,
                        'validate_callback' => array($this, 'validate_positive_integer'),
                        'sanitize_callback' => 'absint',
                    ),
                ),
            ),
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array($this, 'create_solution'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => $this->get_solution_create_args(),
            ),
        ));

        // Single solution routes
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<circle_id>\d+)/solutions/(?P<solution_id>\d+)', array(
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'get_solution'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => array(
                    'circle_id'   => array(
                        'required'          => true,
                        'validate_callback' => array($this, 'validate_positive_integer'),
                        'sanitize_callback' => 'absint',
                    ),
                    'solution_id' => array(
                        'required'          => true,
                        'validate_callback' => array($this, 'validate_positive_integer'),
                        'sanitize_callback' => 'absint',
                    ),
                ),
            ),
            array(
                'methods'             => WP_REST_Server::EDITABLE,
                'callback'            => array($this, 'update_solution'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => $this->get_solution_update_args(),
            ),
            array(
                'methods'             => WP_REST_Server::DELETABLE,
                'callback'            => array($this, 'delete_solution'),
                'permission_callback' => array($this, 'check_permissions'),
            ),
        ));

        // Offers routes
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<circle_id>\d+)/offers', array(
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'get_offers'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => array(
                    'circle_id'   => array(
                        'required'          => true,
                        'validate_callback' => array($this, 'validate_positive_integer'),
                        'sanitize_callback' => 'absint',
                    ),
                    'solution_id' => array(
                        'required'          => false,
                        'validate_callback' => array($this, 'validate_positive_integer'),
                        'sanitize_callback' => 'absint',
                    ),
                ),
            ),
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array($this, 'create_offer'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => $this->get_offer_create_args(),
            ),
        ));

        // Single offer routes
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<circle_id>\d+)/offers/(?P<offer_id>\d+)', array(
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'get_offer'),
                'permission_callback' => array($this, 'check_permissions'),
            ),
            array(
                'methods'             => WP_REST_Server::EDITABLE,
                'callback'            => array($this, 'update_offer'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => $this->get_offer_update_args(),
            ),
            array(
                'methods'             => WP_REST_Server::DELETABLE,
                'callback'            => array($this, 'delete_offer'),
                'permission_callback' => array($this, 'check_permissions'),
            ),
        ));

        // Batch operations for solutions
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<circle_id>\d+)/solutions/batch', array(
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array($this, 'batch_update_solutions'),
                'permission_callback' => array($this, 'check_permissions'),
            ),
        ));
    }

    /**
     * Check if user has permission to access endpoints
     *
     * @param WP_REST_Request $request Request object.
     * @return bool|WP_Error
     */
    public function check_permissions($request) {
        // Verify nonce
        $nonce = $request->get_header('X-WP-Nonce');
        if (!wp_verify_nonce($nonce, 'wp_rest')) {
            // Try alternative nonce locations
            $nonce = $request->get_param('_wpnonce');
            if (!wp_verify_nonce($nonce, 'wp_rest')) {
                return new WP_Error(
                    'rest_forbidden',
                    __('Invalid nonce.', 'directreach'),
                    array('status' => 403)
                );
            }
        }

        // Check capability
        if (!current_user_can('manage_options') && !current_user_can('manage_campaigns')) {
            return new WP_Error(
                'rest_forbidden',
                __('You do not have permission to access this resource.', 'directreach'),
                array('status' => 403)
            );
        }

        return true;
    }

    /**
     * Validate positive integer
     *
     * @param mixed $value Value to validate.
     * @return bool
     */
    public function validate_positive_integer($value) {
        return is_numeric($value) && intval($value) > 0;
    }

    /**
     * Validate URL format
     *
     * @param mixed $value Value to validate.
     * @return bool
     */
    public function validate_url($value) {
        if (empty($value)) {
            return true; // Allow empty for optional fields
        }
        return filter_var($value, FILTER_VALIDATE_URL) !== false;
    }

    // =========================================================================
    // SOLUTIONS ENDPOINTS
    // =========================================================================

    /**
     * Get all solutions for a journey circle
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function get_solutions($request) {
        global $wpdb;

        $circle_id = $request->get_param('circle_id');
        $table_name = $wpdb->prefix . 'dr_journey_solutions';

        // Verify journey circle exists
        if (!$this->journey_circle_exists($circle_id)) {
            return new WP_Error(
                'not_found',
                __('Journey circle not found.', 'directreach'),
                array('status' => 404)
            );
        }

        $solutions = $wpdb->get_results(
            $wpdb->prepare(
                "SELECT s.*, p.title as problem_title, p.is_primary as problem_is_primary
                 FROM {$table_name} s
                 LEFT JOIN {$wpdb->prefix}dr_journey_problems p ON s.problem_id = p.id
                 WHERE s.journey_circle_id = %d
                 ORDER BY s.position ASC, s.created_at ASC",
                $circle_id
            ),
            ARRAY_A
        );

        if ($solutions === null) {
            return new WP_Error(
                'db_error',
                __('Database error occurred.', 'directreach'),
                array('status' => 500)
            );
        }

        // Format response
        $formatted = array_map(array($this, 'format_solution_response'), $solutions);

        return rest_ensure_response(array(
            'success'   => true,
            'data'      => $formatted,
            'count'     => count($formatted),
            'circle_id' => $circle_id,
        ));
    }

    /**
     * Get a single solution
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function get_solution($request) {
        global $wpdb;

        $circle_id   = $request->get_param('circle_id');
        $solution_id = $request->get_param('solution_id');
        $table_name  = $wpdb->prefix . 'dr_journey_solutions';

        $solution = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT s.*, p.title as problem_title, p.is_primary as problem_is_primary
                 FROM {$table_name} s
                 LEFT JOIN {$wpdb->prefix}dr_journey_problems p ON s.problem_id = p.id
                 WHERE s.id = %d AND s.journey_circle_id = %d",
                $solution_id,
                $circle_id
            ),
            ARRAY_A
        );

        if (!$solution) {
            return new WP_Error(
                'not_found',
                __('Solution not found.', 'directreach'),
                array('status' => 404)
            );
        }

        return rest_ensure_response(array(
            'success' => true,
            'data'    => $this->format_solution_response($solution),
        ));
    }

    /**
     * Create a new solution
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function create_solution($request) {
        global $wpdb;

        $circle_id  = absint($request->get_param('circle_id'));
        $problem_id = absint($request->get_param('problem_id'));
        $title      = sanitize_text_field($request->get_param('title'));

        // Verify journey circle exists
        if (!$this->journey_circle_exists($circle_id)) {
            return new WP_Error(
                'not_found',
                __('Journey circle not found.', 'directreach'),
                array('status' => 404)
            );
        }

        // Verify problem exists and belongs to this circle
        if (!$this->problem_exists($problem_id, $circle_id)) {
            return new WP_Error(
                'invalid_problem',
                __('Problem not found or does not belong to this journey circle.', 'directreach'),
                array('status' => 400)
            );
        }

        // Check if problem already has a solution (1:1 mapping)
        if ($this->problem_has_solution($problem_id)) {
            return new WP_Error(
                'duplicate_solution',
                __('This problem already has a solution. Each problem can only have one solution.', 'directreach'),
                array('status' => 400)
            );
        }

        // Validate required fields
        if (empty($title)) {
            return new WP_Error(
                'missing_title',
                __('Solution title is required.', 'directreach'),
                array('status' => 400)
            );
        }

        // Get next position
        $table_name = $wpdb->prefix . 'dr_journey_solutions';
        $position   = $wpdb->get_var(
            $wpdb->prepare(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM {$table_name} WHERE journey_circle_id = %d",
                $circle_id
            )
        );

        // Insert solution
        $data = array(
            'journey_circle_id' => $circle_id,
            'problem_id'        => $problem_id,
            'title'             => $title,
            'description'       => sanitize_textarea_field($request->get_param('description') ?: ''),
            'position'          => intval($position),
            'asset_urls'        => wp_json_encode(array()),
            'status'            => 'draft',
            'created_at'        => current_time('mysql'),
            'updated_at'        => current_time('mysql'),
        );

        $formats = array('%d', '%d', '%s', '%s', '%d', '%s', '%s', '%s', '%s');

        $result = $wpdb->insert($table_name, $data, $formats);

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to create solution.', 'directreach'),
                array('status' => 500)
            );
        }

        $solution_id = $wpdb->insert_id;

        // Fetch the created solution with problem info
        $solution = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT s.*, p.title as problem_title, p.is_primary as problem_is_primary
                 FROM {$table_name} s
                 LEFT JOIN {$wpdb->prefix}dr_journey_problems p ON s.problem_id = p.id
                 WHERE s.id = %d",
                $solution_id
            ),
            ARRAY_A
        );

        return rest_ensure_response(array(
            'success' => true,
            'message' => __('Solution created successfully.', 'directreach'),
            'data'    => $this->format_solution_response($solution),
        ));
    }

    /**
     * Update a solution
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function update_solution($request) {
        global $wpdb;

        $circle_id   = absint($request->get_param('circle_id'));
        $solution_id = absint($request->get_param('solution_id'));
        $table_name  = $wpdb->prefix . 'dr_journey_solutions';

        // Verify solution exists
        $existing = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT * FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                $solution_id,
                $circle_id
            ),
            ARRAY_A
        );

        if (!$existing) {
            return new WP_Error(
                'not_found',
                __('Solution not found.', 'directreach'),
                array('status' => 404)
            );
        }

        // Build update data
        $update_data   = array();
        $update_format = array();

        if ($request->has_param('title')) {
            $title = sanitize_text_field($request->get_param('title'));
            if (empty($title)) {
                return new WP_Error(
                    'invalid_title',
                    __('Solution title cannot be empty.', 'directreach'),
                    array('status' => 400)
                );
            }
            $update_data['title'] = $title;
            $update_format[]      = '%s';
        }

        if ($request->has_param('description')) {
            $update_data['description'] = sanitize_textarea_field($request->get_param('description'));
            $update_format[]            = '%s';
        }

        if ($request->has_param('position')) {
            $update_data['position'] = absint($request->get_param('position'));
            $update_format[]         = '%d';
        }

        if ($request->has_param('status')) {
            $status = sanitize_text_field($request->get_param('status'));
            if (!in_array($status, array('draft', 'active'), true)) {
                return new WP_Error(
                    'invalid_status',
                    __('Invalid status. Must be "draft" or "active".', 'directreach'),
                    array('status' => 400)
                );
            }
            $update_data['status'] = $status;
            $update_format[]       = '%s';
        }

        if ($request->has_param('asset_urls')) {
            $asset_urls              = $request->get_param('asset_urls');
            $update_data['asset_urls'] = wp_json_encode(is_array($asset_urls) ? $asset_urls : array());
            $update_format[]         = '%s';
        }

        if (empty($update_data)) {
            return new WP_Error(
                'no_data',
                __('No valid update data provided.', 'directreach'),
                array('status' => 400)
            );
        }

        $update_data['updated_at'] = current_time('mysql');
        $update_format[]           = '%s';

        $result = $wpdb->update(
            $table_name,
            $update_data,
            array('id' => $solution_id),
            $update_format,
            array('%d')
        );

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to update solution.', 'directreach'),
                array('status' => 500)
            );
        }

        // Fetch updated solution
        $solution = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT s.*, p.title as problem_title, p.is_primary as problem_is_primary
                 FROM {$table_name} s
                 LEFT JOIN {$wpdb->prefix}dr_journey_problems p ON s.problem_id = p.id
                 WHERE s.id = %d",
                $solution_id
            ),
            ARRAY_A
        );

        return rest_ensure_response(array(
            'success' => true,
            'message' => __('Solution updated successfully.', 'directreach'),
            'data'    => $this->format_solution_response($solution),
        ));
    }

    /**
     * Delete a solution
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function delete_solution($request) {
        global $wpdb;

        $circle_id   = absint($request->get_param('circle_id'));
        $solution_id = absint($request->get_param('solution_id'));
        $table_name  = $wpdb->prefix . 'dr_journey_solutions';

        // Verify solution exists
        $existing = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT * FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                $solution_id,
                $circle_id
            ),
            ARRAY_A
        );

        if (!$existing) {
            return new WP_Error(
                'not_found',
                __('Solution not found.', 'directreach'),
                array('status' => 404)
            );
        }

        // Delete associated offers first (cascade)
        $offers_table = $wpdb->prefix . 'dr_journey_offers';
        $wpdb->delete($offers_table, array('solution_id' => $solution_id), array('%d'));

        // Delete solution
        $result = $wpdb->delete($table_name, array('id' => $solution_id), array('%d'));

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to delete solution.', 'directreach'),
                array('status' => 500)
            );
        }

        // Reorder remaining solutions
        $this->reorder_solutions($circle_id);

        return rest_ensure_response(array(
            'success' => true,
            'message' => __('Solution and associated offers deleted successfully.', 'directreach'),
        ));
    }

    /**
     * Batch update solutions (for reordering)
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function batch_update_solutions($request) {
        global $wpdb;

        $circle_id  = absint($request->get_param('circle_id'));
        $solutions  = $request->get_param('solutions');
        $table_name = $wpdb->prefix . 'dr_journey_solutions';

        if (!is_array($solutions)) {
            return new WP_Error(
                'invalid_data',
                __('Solutions must be an array.', 'directreach'),
                array('status' => 400)
            );
        }

        // Verify journey circle exists
        if (!$this->journey_circle_exists($circle_id)) {
            return new WP_Error(
                'not_found',
                __('Journey circle not found.', 'directreach'),
                array('status' => 404)
            );
        }

        $updated = 0;
        foreach ($solutions as $index => $solution) {
            if (!isset($solution['id'])) {
                continue;
            }

            $solution_id = absint($solution['id']);

            // Verify solution belongs to this circle
            $exists = $wpdb->get_var(
                $wpdb->prepare(
                    "SELECT id FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                    $solution_id,
                    $circle_id
                )
            );

            if (!$exists) {
                continue;
            }

            $update_data   = array(
                'position'   => $index,
                'updated_at' => current_time('mysql'),
            );
            $update_format = array('%d', '%s');

            if (isset($solution['title']) && !empty($solution['title'])) {
                $update_data['title'] = sanitize_text_field($solution['title']);
                $update_format[]      = '%s';
            }

            $wpdb->update(
                $table_name,
                $update_data,
                array('id' => $solution_id),
                $update_format,
                array('%d')
            );

            $updated++;
        }

        return rest_ensure_response(array(
            'success' => true,
            'message' => sprintf(__('%d solutions updated.', 'directreach'), $updated),
            'updated' => $updated,
        ));
    }

    // =========================================================================
    // OFFERS ENDPOINTS
    // =========================================================================

    /**
     * Get all offers for a journey circle (optionally filtered by solution)
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function get_offers($request) {
        global $wpdb;

        $circle_id   = absint($request->get_param('circle_id'));
        $solution_id = $request->get_param('solution_id');
        $table_name  = $wpdb->prefix . 'dr_journey_offers';

        // Verify journey circle exists
        if (!$this->journey_circle_exists($circle_id)) {
            return new WP_Error(
                'not_found',
                __('Journey circle not found.', 'directreach'),
                array('status' => 404)
            );
        }

        // Build query
        $query = "SELECT o.*, s.title as solution_title, p.title as problem_title
                  FROM {$table_name} o
                  LEFT JOIN {$wpdb->prefix}dr_journey_solutions s ON o.solution_id = s.id
                  LEFT JOIN {$wpdb->prefix}dr_journey_problems p ON s.problem_id = p.id
                  WHERE o.journey_circle_id = %d";
        $args  = array($circle_id);

        if ($solution_id) {
            $query .= " AND o.solution_id = %d";
            $args[] = absint($solution_id);
        }

        $query .= " ORDER BY o.solution_id ASC, o.position ASC, o.created_at ASC";

        $offers = $wpdb->get_results(
            $wpdb->prepare($query, $args),
            ARRAY_A
        );

        if ($offers === null) {
            return new WP_Error(
                'db_error',
                __('Database error occurred.', 'directreach'),
                array('status' => 500)
            );
        }

        // Format response
        $formatted = array_map(array($this, 'format_offer_response'), $offers);

        // Group by solution if not filtered
        $grouped = array();
        if (!$solution_id) {
            foreach ($formatted as $offer) {
                $sol_id = $offer['solution_id'];
                if (!isset($grouped[$sol_id])) {
                    $grouped[$sol_id] = array(
                        'solution_id'    => $sol_id,
                        'solution_title' => $offer['solution_title'],
                        'offers'         => array(),
                    );
                }
                $grouped[$sol_id]['offers'][] = $offer;
            }
        }

        return rest_ensure_response(array(
            'success'   => true,
            'data'      => $solution_id ? $formatted : array_values($grouped),
            'count'     => count($formatted),
            'circle_id' => $circle_id,
        ));
    }

    /**
     * Get a single offer
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function get_offer($request) {
        global $wpdb;

        $circle_id = absint($request->get_param('circle_id'));
        $offer_id  = absint($request->get_param('offer_id'));
        $table_name = $wpdb->prefix . 'dr_journey_offers';

        $offer = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT o.*, s.title as solution_title, p.title as problem_title
                 FROM {$table_name} o
                 LEFT JOIN {$wpdb->prefix}dr_journey_solutions s ON o.solution_id = s.id
                 LEFT JOIN {$wpdb->prefix}dr_journey_problems p ON s.problem_id = p.id
                 WHERE o.id = %d AND o.journey_circle_id = %d",
                $offer_id,
                $circle_id
            ),
            ARRAY_A
        );

        if (!$offer) {
            return new WP_Error(
                'not_found',
                __('Offer not found.', 'directreach'),
                array('status' => 404)
            );
        }

        return rest_ensure_response(array(
            'success' => true,
            'data'    => $this->format_offer_response($offer),
        ));
    }

    /**
     * Create a new offer
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function create_offer($request) {
        global $wpdb;

        $circle_id   = absint($request->get_param('circle_id'));
        $solution_id = absint($request->get_param('solution_id'));
        $title       = sanitize_text_field($request->get_param('title'));
        $url         = esc_url_raw($request->get_param('url'));

        // Verify journey circle exists
        if (!$this->journey_circle_exists($circle_id)) {
            return new WP_Error(
                'not_found',
                __('Journey circle not found.', 'directreach'),
                array('status' => 404)
            );
        }

        // Verify solution exists and belongs to this circle
        if (!$this->solution_exists($solution_id, $circle_id)) {
            return new WP_Error(
                'invalid_solution',
                __('Solution not found or does not belong to this journey circle.', 'directreach'),
                array('status' => 400)
            );
        }

        // Validate required fields
        if (empty($title)) {
            return new WP_Error(
                'missing_title',
                __('Offer title is required.', 'directreach'),
                array('status' => 400)
            );
        }

        if (empty($url)) {
            return new WP_Error(
                'missing_url',
                __('Offer URL is required.', 'directreach'),
                array('status' => 400)
            );
        }

        // Validate URL format
        if (!filter_var($url, FILTER_VALIDATE_URL)) {
            return new WP_Error(
                'invalid_url',
                __('Please provide a valid URL.', 'directreach'),
                array('status' => 400)
            );
        }

        // Get next position for this solution
        $table_name = $wpdb->prefix . 'dr_journey_offers';
        $position   = $wpdb->get_var(
            $wpdb->prepare(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM {$table_name} WHERE solution_id = %d",
                $solution_id
            )
        );

        // Insert offer
        $data = array(
            'journey_circle_id' => $circle_id,
            'solution_id'       => $solution_id,
            'title'             => $title,
            'url'               => $url,
            'description'       => sanitize_textarea_field($request->get_param('description') ?: ''),
            'position'          => intval($position),
            'created_at'        => current_time('mysql'),
            'updated_at'        => current_time('mysql'),
        );

        $formats = array('%d', '%d', '%s', '%s', '%s', '%d', '%s', '%s');

        $result = $wpdb->insert($table_name, $data, $formats);

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to create offer.', 'directreach'),
                array('status' => 500)
            );
        }

        $offer_id = $wpdb->insert_id;

        // Fetch the created offer with solution info
        $offer = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT o.*, s.title as solution_title, p.title as problem_title
                 FROM {$table_name} o
                 LEFT JOIN {$wpdb->prefix}dr_journey_solutions s ON o.solution_id = s.id
                 LEFT JOIN {$wpdb->prefix}dr_journey_problems p ON s.problem_id = p.id
                 WHERE o.id = %d",
                $offer_id
            ),
            ARRAY_A
        );

        return rest_ensure_response(array(
            'success' => true,
            'message' => __('Offer created successfully.', 'directreach'),
            'data'    => $this->format_offer_response($offer),
        ));
    }

    /**
     * Update an offer
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function update_offer($request) {
        global $wpdb;

        $circle_id = absint($request->get_param('circle_id'));
        $offer_id  = absint($request->get_param('offer_id'));
        $table_name = $wpdb->prefix . 'dr_journey_offers';

        // Verify offer exists
        $existing = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT * FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                $offer_id,
                $circle_id
            ),
            ARRAY_A
        );

        if (!$existing) {
            return new WP_Error(
                'not_found',
                __('Offer not found.', 'directreach'),
                array('status' => 404)
            );
        }

        // Build update data
        $update_data   = array();
        $update_format = array();

        if ($request->has_param('title')) {
            $title = sanitize_text_field($request->get_param('title'));
            if (empty($title)) {
                return new WP_Error(
                    'invalid_title',
                    __('Offer title cannot be empty.', 'directreach'),
                    array('status' => 400)
                );
            }
            $update_data['title'] = $title;
            $update_format[]      = '%s';
        }

        if ($request->has_param('url')) {
            $url = esc_url_raw($request->get_param('url'));
            if (empty($url) || !filter_var($url, FILTER_VALIDATE_URL)) {
                return new WP_Error(
                    'invalid_url',
                    __('Please provide a valid URL.', 'directreach'),
                    array('status' => 400)
                );
            }
            $update_data['url'] = $url;
            $update_format[]    = '%s';
        }

        if ($request->has_param('description')) {
            $update_data['description'] = sanitize_textarea_field($request->get_param('description'));
            $update_format[]            = '%s';
        }

        if ($request->has_param('position')) {
            $update_data['position'] = absint($request->get_param('position'));
            $update_format[]         = '%d';
        }

        if (empty($update_data)) {
            return new WP_Error(
                'no_data',
                __('No valid update data provided.', 'directreach'),
                array('status' => 400)
            );
        }

        $update_data['updated_at'] = current_time('mysql');
        $update_format[]           = '%s';

        $result = $wpdb->update(
            $table_name,
            $update_data,
            array('id' => $offer_id),
            $update_format,
            array('%d')
        );

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to update offer.', 'directreach'),
                array('status' => 500)
            );
        }

        // Fetch updated offer
        $offer = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT o.*, s.title as solution_title, p.title as problem_title
                 FROM {$table_name} o
                 LEFT JOIN {$wpdb->prefix}dr_journey_solutions s ON o.solution_id = s.id
                 LEFT JOIN {$wpdb->prefix}dr_journey_problems p ON s.problem_id = p.id
                 WHERE o.id = %d",
                $offer_id
            ),
            ARRAY_A
        );

        return rest_ensure_response(array(
            'success' => true,
            'message' => __('Offer updated successfully.', 'directreach'),
            'data'    => $this->format_offer_response($offer),
        ));
    }

    /**
     * Delete an offer
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function delete_offer($request) {
        global $wpdb;

        $circle_id = absint($request->get_param('circle_id'));
        $offer_id  = absint($request->get_param('offer_id'));
        $table_name = $wpdb->prefix . 'dr_journey_offers';

        // Verify offer exists
        $existing = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT * FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                $offer_id,
                $circle_id
            ),
            ARRAY_A
        );

        if (!$existing) {
            return new WP_Error(
                'not_found',
                __('Offer not found.', 'directreach'),
                array('status' => 404)
            );
        }

        $solution_id = $existing['solution_id'];

        // Delete offer
        $result = $wpdb->delete($table_name, array('id' => $offer_id), array('%d'));

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to delete offer.', 'directreach'),
                array('status' => 500)
            );
        }

        // Reorder remaining offers for this solution
        $this->reorder_offers($solution_id);

        return rest_ensure_response(array(
            'success' => true,
            'message' => __('Offer deleted successfully.', 'directreach'),
        ));
    }

    // =========================================================================
    // HELPER METHODS
    // =========================================================================

    /**
     * Check if journey circle exists
     *
     * @param int $circle_id Circle ID.
     * @return bool
     */
    private function journey_circle_exists($circle_id) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'dr_journey_circles';

        return (bool) $wpdb->get_var(
            $wpdb->prepare(
                "SELECT id FROM {$table_name} WHERE id = %d",
                $circle_id
            )
        );
    }

    /**
     * Check if problem exists and belongs to circle
     *
     * @param int $problem_id Problem ID.
     * @param int $circle_id  Circle ID.
     * @return bool
     */
    private function problem_exists($problem_id, $circle_id) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'dr_journey_problems';

        return (bool) $wpdb->get_var(
            $wpdb->prepare(
                "SELECT id FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                $problem_id,
                $circle_id
            )
        );
    }

    /**
     * Check if problem already has a solution
     *
     * @param int $problem_id Problem ID.
     * @return bool
     */
    private function problem_has_solution($problem_id) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'dr_journey_solutions';

        return (bool) $wpdb->get_var(
            $wpdb->prepare(
                "SELECT id FROM {$table_name} WHERE problem_id = %d",
                $problem_id
            )
        );
    }

    /**
     * Check if solution exists and belongs to circle
     *
     * @param int $solution_id Solution ID.
     * @param int $circle_id   Circle ID.
     * @return bool
     */
    private function solution_exists($solution_id, $circle_id) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'dr_journey_solutions';

        return (bool) $wpdb->get_var(
            $wpdb->prepare(
                "SELECT id FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                $solution_id,
                $circle_id
            )
        );
    }

    /**
     * Reorder solutions after deletion
     *
     * @param int $circle_id Circle ID.
     * @return void
     */
    private function reorder_solutions($circle_id) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'dr_journey_solutions';

        $solutions = $wpdb->get_results(
            $wpdb->prepare(
                "SELECT id FROM {$table_name} WHERE journey_circle_id = %d ORDER BY position ASC",
                $circle_id
            )
        );

        foreach ($solutions as $index => $solution) {
            $wpdb->update(
                $table_name,
                array('position' => $index),
                array('id' => $solution->id),
                array('%d'),
                array('%d')
            );
        }
    }

    /**
     * Reorder offers after deletion
     *
     * @param int $solution_id Solution ID.
     * @return void
     */
    private function reorder_offers($solution_id) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'dr_journey_offers';

        $offers = $wpdb->get_results(
            $wpdb->prepare(
                "SELECT id FROM {$table_name} WHERE solution_id = %d ORDER BY position ASC",
                $solution_id
            )
        );

        foreach ($offers as $index => $offer) {
            $wpdb->update(
                $table_name,
                array('position' => $index),
                array('id' => $offer->id),
                array('%d'),
                array('%d')
            );
        }
    }

    /**
     * Format solution response
     *
     * @param array $solution Raw solution data.
     * @return array Formatted solution.
     */
    private function format_solution_response($solution) {
        return array(
            'id'                 => intval($solution['id']),
            'journey_circle_id'  => intval($solution['journey_circle_id']),
            'problem_id'         => intval($solution['problem_id']),
            'problem_title'      => $solution['problem_title'] ?? '',
            'problem_is_primary' => (bool) ($solution['problem_is_primary'] ?? false),
            'title'              => $solution['title'],
            'description'        => $solution['description'] ?? '',
            'position'           => intval($solution['position']),
            'asset_urls'         => json_decode($solution['asset_urls'] ?? '[]', true) ?: array(),
            'status'             => $solution['status'],
            'created_at'         => $solution['created_at'],
            'updated_at'         => $solution['updated_at'],
        );
    }

    /**
     * Format offer response
     *
     * @param array $offer Raw offer data.
     * @return array Formatted offer.
     */
    private function format_offer_response($offer) {
        return array(
            'id'                => intval($offer['id']),
            'journey_circle_id' => intval($offer['journey_circle_id']),
            'solution_id'       => intval($offer['solution_id']),
            'solution_title'    => $offer['solution_title'] ?? '',
            'problem_title'     => $offer['problem_title'] ?? '',
            'title'             => $offer['title'],
            'url'               => $offer['url'],
            'description'       => $offer['description'] ?? '',
            'position'          => intval($offer['position']),
            'created_at'        => $offer['created_at'],
            'updated_at'        => $offer['updated_at'],
        );
    }

    /**
     * Get solution create args
     *
     * @return array
     */
    private function get_solution_create_args() {
        return array(
            'circle_id'   => array(
                'required'          => true,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
            'problem_id'  => array(
                'required'          => true,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
            'title'       => array(
                'required'          => true,
                'sanitize_callback' => 'sanitize_text_field',
            ),
            'description' => array(
                'required'          => false,
                'sanitize_callback' => 'sanitize_textarea_field',
            ),
        );
    }

    /**
     * Get solution update args
     *
     * @return array
     */
    private function get_solution_update_args() {
        return array(
            'circle_id'   => array(
                'required'          => true,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
            'solution_id' => array(
                'required'          => true,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
            'title'       => array(
                'required'          => false,
                'sanitize_callback' => 'sanitize_text_field',
            ),
            'description' => array(
                'required'          => false,
                'sanitize_callback' => 'sanitize_textarea_field',
            ),
            'position'    => array(
                'required'          => false,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
            'status'      => array(
                'required'          => false,
                'sanitize_callback' => 'sanitize_text_field',
            ),
        );
    }

    /**
     * Get offer create args
     *
     * @return array
     */
    private function get_offer_create_args() {
        return array(
            'circle_id'   => array(
                'required'          => true,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
            'solution_id' => array(
                'required'          => true,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
            'title'       => array(
                'required'          => true,
                'sanitize_callback' => 'sanitize_text_field',
            ),
            'url'         => array(
                'required'          => true,
                'validate_callback' => array($this, 'validate_url'),
                'sanitize_callback' => 'esc_url_raw',
            ),
            'description' => array(
                'required'          => false,
                'sanitize_callback' => 'sanitize_textarea_field',
            ),
        );
    }

    /**
     * Get offer update args
     *
     * @return array
     */
    private function get_offer_update_args() {
        return array(
            'circle_id'   => array(
                'required'          => true,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
            'offer_id'    => array(
                'required'          => true,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
            'title'       => array(
                'required'          => false,
                'sanitize_callback' => 'sanitize_text_field',
            ),
            'url'         => array(
                'required'          => false,
                'validate_callback' => array($this, 'validate_url'),
                'sanitize_callback' => 'esc_url_raw',
            ),
            'description' => array(
                'required'          => false,
                'sanitize_callback' => 'sanitize_textarea_field',
            ),
            'position'    => array(
                'required'          => false,
                'validate_callback' => array($this, 'validate_positive_integer'),
                'sanitize_callback' => 'absint',
            ),
        );
    }
}

// Initialize and register routes on REST API init
add_action('rest_api_init', function() {
    $controller = new DR_Journey_Solutions_Controller();
    $controller->register_routes();
});
