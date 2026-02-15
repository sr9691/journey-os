<?php
/**
 * Journey Circle Completion REST API Controller
 * 
 * Iteration 10: Steps 10-11 & Completion Flow
 * Handles asset URL linking, completion status tracking, and journey finalization.
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Class DR_Journey_Completion_Controller
 * 
 * REST API endpoints for journey completion workflow:
 * - PUT /journey-circles/{id}/assets/{asset_id} - Update asset with published URL
 * - PUT /journey-circles/{id}/problems/{problem_id} - Update problem asset_urls
 * - PUT /journey-circles/{id}/solutions/{solution_id} - Update solution asset_urls
 * - GET /journey-circles/{id}/completion-status - Get completion progress
 * - PUT /journey-circles/{id}/complete - Mark journey as complete
 */
class DR_Journey_Completion_Controller extends WP_REST_Controller {

    /**
     * Namespace for REST routes
     *
     * @var string
     */
    protected $namespace = 'directreach/v2';

    /**
     * Base route for journey circles
     *
     * @var string
     */
    protected $rest_base = 'journey-circles';

    /**
     * Journey Circle Manager instance
     *
     * @var DR_Journey_Circle_Manager
     */
    private $journey_manager;

    /**
     * Constructor
     */
    public function __construct() {
        $this->journey_manager = new DR_Journey_Circle_Manager();
    }

    /**
     * Register REST API routes
     */
    public function register_routes() {
        // Update asset with published URL
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<id>[\d]+)/assets/(?P<asset_id>[\d]+)', array(
            array(
                'methods'             => WP_REST_Server::EDITABLE,
                'callback'            => array($this, 'update_asset_url'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => $this->get_update_asset_args(),
            ),
        ));

        // Update problem asset_urls
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<id>[\d]+)/problems/(?P<problem_id>[\d]+)/asset-urls', array(
            array(
                'methods'             => WP_REST_Server::EDITABLE,
                'callback'            => array($this, 'update_problem_asset_urls'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => $this->get_update_asset_urls_args(),
            ),
        ));

        // Update solution asset_urls
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<id>[\d]+)/solutions/(?P<solution_id>[\d]+)/asset-urls', array(
            array(
                'methods'             => WP_REST_Server::EDITABLE,
                'callback'            => array($this, 'update_solution_asset_urls'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => $this->get_update_asset_urls_args(),
            ),
        ));

        // Get completion status
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<id>[\d]+)/completion-status', array(
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'get_completion_status'),
                'permission_callback' => array($this, 'check_permissions'),
            ),
        ));

        // Mark journey as complete
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<id>[\d]+)/complete', array(
            array(
                'methods'             => WP_REST_Server::EDITABLE,
                'callback'            => array($this, 'mark_complete'),
                'permission_callback' => array($this, 'check_permissions'),
            ),
        ));

        // Get all assets for a journey circle
        register_rest_route($this->namespace, '/' . $this->rest_base . '/(?P<id>[\d]+)/assets', array(
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'get_all_assets'),
                'permission_callback' => array($this, 'check_permissions'),
            ),
        ));
    }

    /**
     * Check user permissions
     *
     * @param WP_REST_Request $request Request object
     * @return bool|WP_Error
     */
    public function check_permissions($request) {
        // Verify nonce
        $nonce = $request->get_header('X-WP-Nonce');
        if (!wp_verify_nonce($nonce, 'wp_rest')) {
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
                __('You do not have permission to manage campaigns.', 'directreach'),
                array('status' => 403)
            );
        }

        return true;
    }

    /**
     * Update asset with published URL
     *
     * @param WP_REST_Request $request Request object
     * @return WP_REST_Response|WP_Error
     */
    public function update_asset_url($request) {
        global $wpdb;

        $journey_circle_id = absint($request->get_param('id'));
        $asset_id = absint($request->get_param('asset_id'));
        $url = esc_url_raw($request->get_param('url'));

        // Validate journey circle exists
        $journey_circle = $this->journey_manager->get($journey_circle_id);
        if (!$journey_circle) {
            return new WP_Error(
                'not_found',
                __('Journey circle not found.', 'directreach'),
                array('status' => 404)
            );
        }

        // Validate URL
        if (empty($url) || !filter_var($url, FILTER_VALIDATE_URL)) {
            return new WP_Error(
                'invalid_url',
                __('Please provide a valid URL.', 'directreach'),
                array('status' => 400)
            );
        }

        // Update asset
        $table_name = $wpdb->prefix . 'dr_journey_assets';
        $updated = $wpdb->update(
            $table_name,
            array(
                'url'        => $url,
                'status'     => 'published',
                'updated_at' => current_time('mysql'),
            ),
            array(
                'id'               => $asset_id,
                'journey_circle_id' => $journey_circle_id,
            ),
            array('%s', '%s', '%s'),
            array('%d', '%d')
        );

        if ($updated === false) {
            return new WP_Error(
                'update_failed',
                __('Failed to update asset.', 'directreach'),
                array('status' => 500)
            );
        }

        // Get updated asset
        $asset = $wpdb->get_row($wpdb->prepare(
            "SELECT * FROM {$table_name} WHERE id = %d",
            $asset_id
        ));

        // Also update the linked problem or solution asset_urls
        $this->sync_asset_url_to_linked_entity($asset);

        return rest_ensure_response(array(
            'success' => true,
            'asset'   => $this->prepare_asset_for_response($asset),
            'message' => __('Asset URL updated and marked as published.', 'directreach'),
        ));
    }

    /**
     * Sync asset URL to the linked problem or solution
     *
     * @param object $asset Asset object
     */
    private function sync_asset_url_to_linked_entity($asset) {
        global $wpdb;

        if (empty($asset->url)) {
            return;
        }

        $table_name = '';
        $id_field = '';

        if ($asset->linked_to_type === 'problem') {
            $table_name = $wpdb->prefix . 'dr_journey_problems';
            $id_field = 'id';
        } elseif ($asset->linked_to_type === 'solution') {
            $table_name = $wpdb->prefix . 'dr_journey_solutions';
            $id_field = 'id';
        } else {
            return;
        }

        // Get current asset_urls
        $current = $wpdb->get_var($wpdb->prepare(
            "SELECT asset_urls FROM {$table_name} WHERE {$id_field} = %d",
            $asset->linked_to_id
        ));

        $asset_urls = !empty($current) ? json_decode($current, true) : array();
        if (!is_array($asset_urls)) {
            $asset_urls = array();
        }

        // Add URL if not already present
        if (!in_array($asset->url, $asset_urls, true)) {
            $asset_urls[] = $asset->url;

            $wpdb->update(
                $table_name,
                array(
                    'asset_urls' => wp_json_encode($asset_urls),
                    'updated_at' => current_time('mysql'),
                ),
                array($id_field => $asset->linked_to_id),
                array('%s', '%s'),
                array('%d')
            );
        }
    }

    /**
     * Update problem asset_urls
     *
     * @param WP_REST_Request $request Request object
     * @return WP_REST_Response|WP_Error
     */
    public function update_problem_asset_urls($request) {
        global $wpdb;

        $journey_circle_id = absint($request->get_param('id'));
        $problem_id = absint($request->get_param('problem_id'));
        $asset_urls = $request->get_param('asset_urls');

        // Validate and sanitize URLs
        if (!is_array($asset_urls)) {
            $asset_urls = array();
        }
        $asset_urls = array_map('esc_url_raw', $asset_urls);
        $asset_urls = array_filter($asset_urls, function($url) {
            return filter_var($url, FILTER_VALIDATE_URL);
        });

        $table_name = $wpdb->prefix . 'dr_journey_problems';
        $updated = $wpdb->update(
            $table_name,
            array(
                'asset_urls' => wp_json_encode(array_values($asset_urls)),
                'updated_at' => current_time('mysql'),
            ),
            array(
                'id'               => $problem_id,
                'journey_circle_id' => $journey_circle_id,
            ),
            array('%s', '%s'),
            array('%d', '%d')
        );

        if ($updated === false) {
            return new WP_Error(
                'update_failed',
                __('Failed to update problem asset URLs.', 'directreach'),
                array('status' => 500)
            );
        }

        return rest_ensure_response(array(
            'success'    => true,
            'problem_id' => $problem_id,
            'asset_urls' => array_values($asset_urls),
            'message'    => __('Problem asset URLs updated.', 'directreach'),
        ));
    }

    /**
     * Update solution asset_urls
     *
     * @param WP_REST_Request $request Request object
     * @return WP_REST_Response|WP_Error
     */
    public function update_solution_asset_urls($request) {
        global $wpdb;

        $journey_circle_id = absint($request->get_param('id'));
        $solution_id = absint($request->get_param('solution_id'));
        $asset_urls = $request->get_param('asset_urls');

        // Validate and sanitize URLs
        if (!is_array($asset_urls)) {
            $asset_urls = array();
        }
        $asset_urls = array_map('esc_url_raw', $asset_urls);
        $asset_urls = array_filter($asset_urls, function($url) {
            return filter_var($url, FILTER_VALIDATE_URL);
        });

        $table_name = $wpdb->prefix . 'dr_journey_solutions';
        $updated = $wpdb->update(
            $table_name,
            array(
                'asset_urls' => wp_json_encode(array_values($asset_urls)),
                'updated_at' => current_time('mysql'),
            ),
            array(
                'id'               => $solution_id,
                'journey_circle_id' => $journey_circle_id,
            ),
            array('%s', '%s'),
            array('%d', '%d')
        );

        if ($updated === false) {
            return new WP_Error(
                'update_failed',
                __('Failed to update solution asset URLs.', 'directreach'),
                array('status' => 500)
            );
        }

        return rest_ensure_response(array(
            'success'     => true,
            'solution_id' => $solution_id,
            'asset_urls'  => array_values($asset_urls),
            'message'     => __('Solution asset URLs updated.', 'directreach'),
        ));
    }

    /**
     * Get completion status for a journey circle
     *
     * @param WP_REST_Request $request Request object
     * @return WP_REST_Response|WP_Error
     */
    public function get_completion_status($request) {
        global $wpdb;

        $journey_circle_id = absint($request->get_param('id'));

        // Validate journey circle exists
        $journey_circle = $this->journey_manager->get($journey_circle_id);
        if (!$journey_circle) {
            return new WP_Error(
                'not_found',
                __('Journey circle not found.', 'directreach'),
                array('status' => 404)
            );
        }

        // Get problems with their completion status
        $problems_table = $wpdb->prefix . 'dr_journey_problems';
        $problems = $wpdb->get_results($wpdb->prepare(
            "SELECT id, title, position, is_primary, asset_urls 
             FROM {$problems_table} 
             WHERE journey_circle_id = %d 
             ORDER BY position ASC",
            $journey_circle_id
        ));

        // Get solutions with their completion status
        $solutions_table = $wpdb->prefix . 'dr_journey_solutions';
        $solutions = $wpdb->get_results($wpdb->prepare(
            "SELECT id, title, position, problem_id, asset_urls 
             FROM {$solutions_table} 
             WHERE journey_circle_id = %d 
             ORDER BY position ASC",
            $journey_circle_id
        ));

        // Get all assets
        $assets_table = $wpdb->prefix . 'dr_journey_assets';
        $assets = $wpdb->get_results($wpdb->prepare(
            "SELECT id, title, asset_type, linked_to_type, linked_to_id, status, url 
             FROM {$assets_table} 
             WHERE journey_circle_id = %d 
             ORDER BY created_at ASC",
            $journey_circle_id
        ));

        // Calculate completion for problems
        $problems_data = array();
        $problems_completed = 0;
        foreach ($problems as $problem) {
            $problem_assets = array_filter($assets, function($asset) use ($problem) {
                return $asset->linked_to_type === 'problem' && 
                       (int)$asset->linked_to_id === (int)$problem->id;
            });
            
            $has_approved_asset = false;
            foreach ($problem_assets as $asset) {
                if (in_array($asset->status, array('approved', 'published'), true)) {
                    $has_approved_asset = true;
                    break;
                }
            }

            $asset_urls = !empty($problem->asset_urls) ? json_decode($problem->asset_urls, true) : array();
            $has_published_url = !empty($asset_urls);

            $is_complete = $has_approved_asset || $has_published_url;
            if ($is_complete) {
                $problems_completed++;
            }

            $problems_data[] = array(
                'id'                 => (int)$problem->id,
                'title'              => $problem->title,
                'position'           => (int)$problem->position,
                'is_primary'         => (bool)$problem->is_primary,
                'asset_count'        => count($problem_assets),
                'has_approved_asset' => $has_approved_asset,
                'has_published_url'  => $has_published_url,
                'is_complete'        => $is_complete,
                'asset_urls'         => $asset_urls,
            );
        }

        // Calculate completion for solutions
        $solutions_data = array();
        $solutions_completed = 0;
        foreach ($solutions as $solution) {
            $solution_assets = array_filter($assets, function($asset) use ($solution) {
                return $asset->linked_to_type === 'solution' && 
                       (int)$asset->linked_to_id === (int)$solution->id;
            });
            
            $has_approved_asset = false;
            foreach ($solution_assets as $asset) {
                if (in_array($asset->status, array('approved', 'published'), true)) {
                    $has_approved_asset = true;
                    break;
                }
            }

            $asset_urls = !empty($solution->asset_urls) ? json_decode($solution->asset_urls, true) : array();
            $has_published_url = !empty($asset_urls);

            $is_complete = $has_approved_asset || $has_published_url;
            if ($is_complete) {
                $solutions_completed++;
            }

            $solutions_data[] = array(
                'id'                 => (int)$solution->id,
                'title'              => $solution->title,
                'position'           => (int)$solution->position,
                'problem_id'         => (int)$solution->problem_id,
                'asset_count'        => count($solution_assets),
                'has_approved_asset' => $has_approved_asset,
                'has_published_url'  => $has_published_url,
                'is_complete'        => $is_complete,
                'asset_urls'         => $asset_urls,
            );
        }

        // Prepare assets data
        $assets_data = array();
        foreach ($assets as $asset) {
            $assets_data[] = array(
                'id'             => (int)$asset->id,
                'title'          => $asset->title,
                'asset_type'     => $asset->asset_type,
                'linked_to_type' => $asset->linked_to_type,
                'linked_to_id'   => (int)$asset->linked_to_id,
                'status'         => $asset->status,
                'url'            => $asset->url,
            );
        }

        // Calculate overall completion
        $total_required = count($problems) + count($solutions);
        $total_completed = $problems_completed + $solutions_completed;
        $completion_percentage = $total_required > 0 
            ? round(($total_completed / $total_required) * 100) 
            : 0;

        $is_journey_complete = count($problems) === 5 && 
                               count($solutions) === 5 && 
                               $problems_completed === 5 && 
                               $solutions_completed === 5;

        return rest_ensure_response(array(
            'journey_circle_id'     => $journey_circle_id,
            'current_status'        => $journey_circle->status,
            'is_complete'           => $is_journey_complete,
            'completion_percentage' => $completion_percentage,
            'problems'              => array(
                'total'     => count($problems),
                'completed' => $problems_completed,
                'items'     => $problems_data,
            ),
            'solutions'             => array(
                'total'     => count($solutions),
                'completed' => $solutions_completed,
                'items'     => $solutions_data,
            ),
            'assets'                => array(
                'total' => count($assets),
                'items' => $assets_data,
            ),
        ));
    }

    /**
     * Mark journey as complete
     *
     * @param WP_REST_Request $request Request object
     * @return WP_REST_Response|WP_Error
     */
    public function mark_complete($request) {
        global $wpdb;

        $journey_circle_id = absint($request->get_param('id'));

        // Get completion status first to validate
        $status_request = new WP_REST_Request('GET');
        $status_request->set_param('id', $journey_circle_id);
        $status_response = $this->get_completion_status($status_request);

        if (is_wp_error($status_response)) {
            return $status_response;
        }

        $status_data = $status_response->get_data();

        // Validate completion requirements
        if ($status_data['problems']['completed'] < 5 || $status_data['solutions']['completed'] < 5) {
            return new WP_Error(
                'incomplete_journey',
                sprintf(
                    __('Journey cannot be marked complete. Problems: %d/5, Solutions: %d/5', 'directreach'),
                    $status_data['problems']['completed'],
                    $status_data['solutions']['completed']
                ),
                array(
                    'status'   => 400,
                    'problems' => $status_data['problems'],
                    'solutions' => $status_data['solutions'],
                )
            );
        }

        // Update journey circle status
        $table_name = $wpdb->prefix . 'dr_journey_circles';
        $updated = $wpdb->update(
            $table_name,
            array(
                'status'     => 'complete',
                'updated_at' => current_time('mysql'),
            ),
            array('id' => $journey_circle_id),
            array('%s', '%s'),
            array('%d')
        );

        if ($updated === false) {
            return new WP_Error(
                'update_failed',
                __('Failed to mark journey as complete.', 'directreach'),
                array('status' => 500)
            );
        }

        // Get service area and client info for return data
        $journey_circle = $this->journey_manager->get($journey_circle_id);
        $service_area = $this->get_service_area($journey_circle->service_area_id);
        $client = $this->get_client_from_service_area($service_area);

        return rest_ensure_response(array(
            'success'           => true,
            'journey_circle_id' => $journey_circle_id,
            'status'            => 'complete',
            'completion_data'   => array(
                'clientId'        => $client ? (int)$client->id : null,
                'clientName'      => $client ? $client->name : null,
                'serviceAreaId'   => (int)$journey_circle->service_area_id,
                'serviceAreaName' => $service_area ? $service_area->name : null,
                'circleComplete'  => true,
                'problemCount'    => $status_data['problems']['completed'],
                'solutionCount'   => $status_data['solutions']['completed'],
                'assetCount'      => $status_data['assets']['total'],
            ),
            'message'           => __('Journey circle marked as complete!', 'directreach'),
        ));
    }

    /**
     * Get all assets for a journey circle
     *
     * @param WP_REST_Request $request Request object
     * @return WP_REST_Response|WP_Error
     */
    public function get_all_assets($request) {
        global $wpdb;

        $journey_circle_id = absint($request->get_param('id'));

        $table_name = $wpdb->prefix . 'dr_journey_assets';
        $assets = $wpdb->get_results($wpdb->prepare(
            "SELECT * FROM {$table_name} 
             WHERE journey_circle_id = %d 
             ORDER BY created_at DESC",
            $journey_circle_id
        ));

        $prepared_assets = array();
        foreach ($assets as $asset) {
            $prepared_assets[] = $this->prepare_asset_for_response($asset);
        }

        return rest_ensure_response(array(
            'journey_circle_id' => $journey_circle_id,
            'total'             => count($assets),
            'assets'            => $prepared_assets,
        ));
    }

    /**
     * Get service area by ID
     *
     * @param int $service_area_id Service area ID
     * @return object|null
     */
    private function get_service_area($service_area_id) {
        global $wpdb;
        $table_name = $wpdb->prefix . 'dr_service_areas';
        return $wpdb->get_row($wpdb->prepare(
            "SELECT * FROM {$table_name} WHERE id = %d",
            $service_area_id
        ));
    }

    /**
     * Get client from service area
     *
     * @param object $service_area Service area object
     * @return object|null
     */
    private function get_client_from_service_area($service_area) {
        if (!$service_area) {
            return null;
        }

        global $wpdb;
        $table_name = $wpdb->prefix . 'cpd_clients';
        return $wpdb->get_row($wpdb->prepare(
            "SELECT * FROM {$table_name} WHERE id = %d",
            $service_area->client_id
        ));
    }

    /**
     * Prepare asset for API response
     *
     * @param object $asset Asset object
     * @return array
     */
    private function prepare_asset_for_response($asset) {
        return array(
            'id'              => (int)$asset->id,
            'journey_circle_id' => (int)$asset->journey_circle_id,
            'linked_to_type'  => $asset->linked_to_type,
            'linked_to_id'    => (int)$asset->linked_to_id,
            'asset_type'      => $asset->asset_type,
            'title'           => $asset->title,
            'outline'         => $asset->outline,
            'content'         => $asset->content,
            'url'             => $asset->url,
            'status'          => $asset->status,
            'created_at'      => $asset->created_at,
            'updated_at'      => $asset->updated_at,
        );
    }

    /**
     * Get arguments for update asset endpoint
     *
     * @return array
     */
    private function get_update_asset_args() {
        return array(
            'url' => array(
                'required'          => true,
                'type'              => 'string',
                'description'       => __('Published URL for the asset', 'directreach'),
                'sanitize_callback' => 'esc_url_raw',
                'validate_callback' => function($value) {
                    return filter_var($value, FILTER_VALIDATE_URL) !== false;
                },
            ),
        );
    }

    /**
     * Get arguments for update asset URLs endpoint
     *
     * @return array
     */
    private function get_update_asset_urls_args() {
        return array(
            'asset_urls' => array(
                'required'          => true,
                'type'              => 'array',
                'description'       => __('Array of published asset URLs', 'directreach'),
                'items'             => array(
                    'type' => 'string',
                ),
            ),
        );
    }
}

// Register the controller
add_action('rest_api_init', function() {
    $controller = new DR_Journey_Completion_Controller();
    $controller->register_routes();
});