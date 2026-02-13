<?php
/**
 * Client Journey Status REST API Extension
 * 
 * Iteration 10: Campaign Builder Integration
 * Adds endpoint to fetch journey statuses for multiple clients.
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Class DR_Client_Journey_Status_Controller
 * 
 * REST API endpoint for fetching journey statuses:
 * - GET /clients/journey-statuses?client_ids=1,2,3
 */
class DR_Client_Journey_Status_Controller extends WP_REST_Controller {

    /**
     * Namespace for REST routes
     *
     * @var string
     */
    protected $namespace = 'directreach/v2';

    /**
     * Base route
     *
     * @var string
     */
    protected $rest_base = 'clients';

    /**
     * Register REST API routes
     */
    public function register_routes() {
        register_rest_route($this->namespace, '/' . $this->rest_base . '/journey-statuses', array(
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array($this, 'get_journey_statuses'),
                'permission_callback' => array($this, 'check_permissions'),
                'args'                => array(
                    'client_ids' => array(
                        'required'          => true,
                        'type'              => 'string',
                        'description'       => __('Comma-separated list of client IDs', 'directreach'),
                        'sanitize_callback' => 'sanitize_text_field',
                    ),
                ),
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
                __('You do not have permission to view this data.', 'directreach'),
                array('status' => 403)
            );
        }

        return true;
    }

    /**
     * Get journey statuses for multiple clients
     *
     * @param WP_REST_Request $request Request object
     * @return WP_REST_Response|WP_Error
     */
    public function get_journey_statuses($request) {
        global $wpdb;

        $client_ids_param = $request->get_param('client_ids');
        
        // Parse and validate client IDs
        $client_ids = array_map('absint', explode(',', $client_ids_param));
        $client_ids = array_filter($client_ids, function($id) {
            return $id > 0;
        });

        if (empty($client_ids)) {
            return rest_ensure_response(array());
        }

        // Build query to get journey statuses for all clients
        $placeholders = implode(',', array_fill(0, count($client_ids), '%d'));
        
        $service_areas_table = $wpdb->prefix . 'dr_service_areas';
        $journey_circles_table = $wpdb->prefix . 'dr_journey_circles';

        // Query joins service areas with journey circles to get status
        // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
        $query = $wpdb->prepare(
            "SELECT 
                sa.client_id,
                sa.id as service_area_id,
                jc.id as journey_circle_id,
                jc.status as journey_status
             FROM {$service_areas_table} sa
             LEFT JOIN {$journey_circles_table} jc ON sa.id = jc.service_area_id
             WHERE sa.client_id IN ({$placeholders})
             ORDER BY jc.updated_at DESC",
            ...$client_ids
        );

        $results = $wpdb->get_results($query);

        // Process results to get best status per client
        // (a client might have multiple service areas/journeys)
        $statuses = array();
        
        foreach ($results as $row) {
            $client_id = (int)$row->client_id;
            $journey_status = $row->journey_status;

            // If we haven't seen this client yet, or if this is a "better" status
            if (!isset($statuses[$client_id]) || 
                $this->is_better_status($journey_status, $statuses[$client_id])) {
                $statuses[$client_id] = $journey_status ?: 'none';
            }
        }

        // Add 'none' for clients with no journeys
        foreach ($client_ids as $client_id) {
            if (!isset($statuses[$client_id])) {
                $statuses[$client_id] = 'none';
            }
        }

        return rest_ensure_response($statuses);
    }

    /**
     * Compare journey statuses to determine which is "better"
     * Priority: complete > active > incomplete > none
     *
     * @param string $new_status New status to compare
     * @param string $current_status Current best status
     * @return bool Whether new status is better
     */
    private function is_better_status($new_status, $current_status) {
        $priority = array(
            'complete'   => 4,
            'active'     => 3,
            'incomplete' => 2,
            'none'       => 1,
            ''           => 0,
        );

        $new_priority = $priority[$new_status] ?? 0;
        $current_priority = $priority[$current_status] ?? 0;

        return $new_priority > $current_priority;
    }
}

// Register the controller
add_action('rest_api_init', function() {
    $controller = new DR_Client_Journey_Status_Controller();
    $controller->register_routes();
});
