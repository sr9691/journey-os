<?php
/**
 * Journey Problems REST Controller
 * 
 * Handles REST API endpoints for journey circle problems.
 * 
 * @package DirectReach
 * @subpackage JourneyCircle
 * @since 2.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class DR_Journey_Problems_Controller {

    /**
     * API namespace
     */
    const NAMESPACE = 'directreach/v2';

    /**
     * Register REST routes
     */
    public function register_routes() {
        // Get problems for a journey circle
        register_rest_route(self::NAMESPACE, '/journey-circles/(?P<circle_id>\d+)/problems', [
            [
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => [$this, 'get_problems'],
                'permission_callback' => [$this, 'check_permission'],
                'args'                => [
                    'circle_id' => [
                        'required'          => true,
                        'validate_callback' => function($param) {
                            return is_numeric($param);
                        }
                    ]
                ]
            ],
            [
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => [$this, 'create_problem'],
                'permission_callback' => [$this, 'check_permission'],
                'args'                => $this->get_problem_args()
            ]
        ]);

        // Single problem operations
        register_rest_route(self::NAMESPACE, '/journey-circles/(?P<circle_id>\d+)/problems/(?P<problem_id>\d+)', [
            [
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => [$this, 'get_problem'],
                'permission_callback' => [$this, 'check_permission']
            ],
            [
                'methods'             => WP_REST_Server::EDITABLE,
                'callback'            => [$this, 'update_problem'],
                'permission_callback' => [$this, 'check_permission'],
                'args'                => $this->get_problem_args()
            ],
            [
                'methods'             => WP_REST_Server::DELETABLE,
                'callback'            => [$this, 'delete_problem'],
                'permission_callback' => [$this, 'check_permission']
            ]
        ]);

        // Bulk operations
        register_rest_route(self::NAMESPACE, '/journey-circles/(?P<circle_id>\d+)/problems/bulk', [
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => [$this, 'bulk_save_problems'],
            'permission_callback' => [$this, 'check_permission'],
            'args'                => [
                'problems' => [
                    'required' => true,
                    'type'     => 'array'
                ],
                'replace_existing' => [
                    'required' => false,
                    'type'     => 'boolean',
                    'default'  => true
                ]
            ]
        ]);

        // Problem recommendations endpoint
        register_rest_route(self::NAMESPACE, '/journey-circles/(?P<circle_id>\d+)/recommendations/problems', [
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => [$this, 'get_problem_recommendations'],
            'permission_callback' => [$this, 'check_permission'],
            'args'                => [
                'industries' => [
                    'required' => false,
                    'type'     => 'array'
                ],
                'service_area_id' => [
                    'required' => false,
                    'type'     => 'integer'
                ],
                'brain_content' => [
                    'required' => false,
                    'type'     => 'array'
                ]
            ]
        ]);
    }

    /**
     * Check user permissions
     */
    public function check_permission($request) {
        // Verify nonce
        $nonce = $request->get_header('X-WP-Nonce');
        if (!$nonce || !wp_verify_nonce($nonce, 'wp_rest')) {
            return new WP_Error(
                'rest_invalid_nonce',
                __('Invalid nonce.', 'directreach'),
                ['status' => 401]
            );
        }

        // Check capability
        if (!current_user_can('manage_campaigns')) {
            return new WP_Error(
                'rest_forbidden',
                __('You do not have permission to access this resource.', 'directreach'),
                ['status' => 403]
            );
        }

        return true;
    }

    /**
     * Get problem creation/update arguments
     */
    private function get_problem_args() {
        return [
            'title' => [
                'required'          => true,
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_text_field',
                'validate_callback' => function($param) {
                    return !empty($param);
                }
            ],
            'description' => [
                'required'          => false,
                'type'              => 'string',
                'sanitize_callback' => 'wp_kses_post',
                'default'           => ''
            ],
            'is_primary' => [
                'required' => false,
                'type'     => 'boolean',
                'default'  => false
            ],
            'position' => [
                'required'          => false,
                'type'              => 'integer',
                'validate_callback' => function($param) {
                    return is_numeric($param) && $param >= 0 && $param <= 4;
                },
                'default'           => 0
            ],
            'asset_urls' => [
                'required' => false,
                'type'     => 'array',
                'default'  => []
            ],
            'status' => [
                'required'          => false,
                'type'              => 'string',
                'enum'              => ['draft', 'active'],
                'default'           => 'draft'
            ]
        ];
    }

    /**
     * Get all problems for a journey circle
     */
    public function get_problems($request) {
        global $wpdb;

        $circle_id = absint($request['circle_id']);
        $table_name = $wpdb->prefix . 'dr_journey_problems';

        $problems = $wpdb->get_results(
            $wpdb->prepare(
                "SELECT * FROM {$table_name} WHERE journey_circle_id = %d ORDER BY position ASC",
                $circle_id
            ),
            ARRAY_A
        );

        if ($problems === null) {
            return new WP_Error(
                'db_error',
                __('Database error occurred.', 'directreach'),
                ['status' => 500]
            );
        }

        // Parse JSON fields
        foreach ($problems as &$problem) {
            $problem['asset_urls'] = json_decode($problem['asset_urls'], true) ?: [];
            $problem['is_primary'] = (bool) $problem['is_primary'];
            $problem['position'] = (int) $problem['position'];
        }

        return rest_ensure_response([
            'success'  => true,
            'problems' => $problems,
            'count'    => count($problems)
        ]);
    }

    /**
     * Get a single problem
     */
    public function get_problem($request) {
        global $wpdb;

        $circle_id = absint($request['circle_id']);
        $problem_id = absint($request['problem_id']);
        $table_name = $wpdb->prefix . 'dr_journey_problems';

        $problem = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT * FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                $problem_id,
                $circle_id
            ),
            ARRAY_A
        );

        if (!$problem) {
            return new WP_Error(
                'not_found',
                __('Problem not found.', 'directreach'),
                ['status' => 404]
            );
        }

        // Parse JSON fields
        $problem['asset_urls'] = json_decode($problem['asset_urls'], true) ?: [];
        $problem['is_primary'] = (bool) $problem['is_primary'];
        $problem['position'] = (int) $problem['position'];

        return rest_ensure_response([
            'success' => true,
            'problem' => $problem
        ]);
    }

    /**
     * Create a new problem
     */
    public function create_problem($request) {
        global $wpdb;

        $circle_id = absint($request['circle_id']);
        $table_name = $wpdb->prefix . 'dr_journey_problems';

        // Verify journey circle exists
        $circle_table = $wpdb->prefix . 'dr_journey_circles';
        $circle_exists = $wpdb->get_var(
            $wpdb->prepare("SELECT id FROM {$circle_table} WHERE id = %d", $circle_id)
        );

        if (!$circle_exists) {
            return new WP_Error(
                'invalid_circle',
                __('Journey circle not found.', 'directreach'),
                ['status' => 404]
            );
        }

        // Check if we already have 5 problems
        $problem_count = $wpdb->get_var(
            $wpdb->prepare(
                "SELECT COUNT(*) FROM {$table_name} WHERE journey_circle_id = %d",
                $circle_id
            )
        );

        if ($problem_count >= 5) {
            return new WP_Error(
                'limit_reached',
                __('Maximum 5 problems allowed per journey circle.', 'directreach'),
                ['status' => 400]
            );
        }

        // If this is primary, unset other primary problems
        if ($request->get_param('is_primary')) {
            $wpdb->update(
                $table_name,
                ['is_primary' => 0],
                ['journey_circle_id' => $circle_id],
                ['%d'],
                ['%d']
            );
        }

        // Prepare data
        $data = [
            'journey_circle_id' => $circle_id,
            'title'             => sanitize_text_field($request->get_param('title')),
            'description'       => wp_kses_post($request->get_param('description') ?: ''),
            'is_primary'        => $request->get_param('is_primary') ? 1 : 0,
            'position'          => absint($request->get_param('position') ?: 0),
            'asset_urls'        => wp_json_encode($request->get_param('asset_urls') ?: []),
            'status'            => sanitize_text_field($request->get_param('status') ?: 'draft'),
            'created_at'        => current_time('mysql'),
            'updated_at'        => current_time('mysql')
        ];

        $result = $wpdb->insert($table_name, $data, [
            '%d', '%s', '%s', '%d', '%d', '%s', '%s', '%s', '%s'
        ]);

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to create problem.', 'directreach'),
                ['status' => 500]
            );
        }

        $problem_id = $wpdb->insert_id;

        // Update journey circle primary_problem_id if this is primary
        if ($data['is_primary']) {
            $wpdb->update(
                $circle_table,
                ['primary_problem_id' => $problem_id],
                ['id' => $circle_id],
                ['%d'],
                ['%d']
            );
        }

        return rest_ensure_response([
            'success' => true,
            'id'      => $problem_id,
            'message' => __('Problem created successfully.', 'directreach')
        ]);
    }

    /**
     * Update a problem
     */
    public function update_problem($request) {
        global $wpdb;

        $circle_id = absint($request['circle_id']);
        $problem_id = absint($request['problem_id']);
        $table_name = $wpdb->prefix . 'dr_journey_problems';

        // Verify problem exists
        $existing = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT * FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                $problem_id,
                $circle_id
            )
        );

        if (!$existing) {
            return new WP_Error(
                'not_found',
                __('Problem not found.', 'directreach'),
                ['status' => 404]
            );
        }

        // If setting as primary, unset others
        if ($request->get_param('is_primary')) {
            $wpdb->update(
                $table_name,
                ['is_primary' => 0],
                ['journey_circle_id' => $circle_id],
                ['%d'],
                ['%d']
            );
        }

        // Prepare update data
        $data = [];
        $formats = [];

        if ($request->has_param('title')) {
            $data['title'] = sanitize_text_field($request->get_param('title'));
            $formats[] = '%s';
        }

        if ($request->has_param('description')) {
            $data['description'] = wp_kses_post($request->get_param('description'));
            $formats[] = '%s';
        }

        if ($request->has_param('is_primary')) {
            $data['is_primary'] = $request->get_param('is_primary') ? 1 : 0;
            $formats[] = '%d';
        }

        if ($request->has_param('position')) {
            $data['position'] = absint($request->get_param('position'));
            $formats[] = '%d';
        }

        if ($request->has_param('asset_urls')) {
            $data['asset_urls'] = wp_json_encode($request->get_param('asset_urls'));
            $formats[] = '%s';
        }

        if ($request->has_param('status')) {
            $data['status'] = sanitize_text_field($request->get_param('status'));
            $formats[] = '%s';
        }

        $data['updated_at'] = current_time('mysql');
        $formats[] = '%s';

        $result = $wpdb->update(
            $table_name,
            $data,
            ['id' => $problem_id],
            $formats,
            ['%d']
        );

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to update problem.', 'directreach'),
                ['status' => 500]
            );
        }

        // Update journey circle primary_problem_id if this is primary
        if (isset($data['is_primary']) && $data['is_primary']) {
            $circle_table = $wpdb->prefix . 'dr_journey_circles';
            $wpdb->update(
                $circle_table,
                ['primary_problem_id' => $problem_id],
                ['id' => $circle_id],
                ['%d'],
                ['%d']
            );
        }

        return rest_ensure_response([
            'success' => true,
            'message' => __('Problem updated successfully.', 'directreach')
        ]);
    }

    /**
     * Delete a problem
     */
    public function delete_problem($request) {
        global $wpdb;

        $circle_id = absint($request['circle_id']);
        $problem_id = absint($request['problem_id']);
        $table_name = $wpdb->prefix . 'dr_journey_problems';

        // Verify problem exists
        $existing = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT * FROM {$table_name} WHERE id = %d AND journey_circle_id = %d",
                $problem_id,
                $circle_id
            )
        );

        if (!$existing) {
            return new WP_Error(
                'not_found',
                __('Problem not found.', 'directreach'),
                ['status' => 404]
            );
        }

        // Delete problem
        $result = $wpdb->delete(
            $table_name,
            ['id' => $problem_id],
            ['%d']
        );

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to delete problem.', 'directreach'),
                ['status' => 500]
            );
        }

        // Clear primary_problem_id if this was the primary
        if ($existing->is_primary) {
            $circle_table = $wpdb->prefix . 'dr_journey_circles';
            $wpdb->update(
                $circle_table,
                ['primary_problem_id' => null],
                ['id' => $circle_id],
                ['%s'],
                ['%d']
            );
        }

        return rest_ensure_response([
            'success' => true,
            'message' => __('Problem deleted successfully.', 'directreach')
        ]);
    }

    /**
     * Bulk save problems (replace all)
     */
    public function bulk_save_problems($request) {
        global $wpdb;

        $circle_id = absint($request['circle_id']);
        $problems = $request->get_param('problems');
        $replace_existing = $request->get_param('replace_existing');
        $table_name = $wpdb->prefix . 'dr_journey_problems';

        // Validate problems array
        if (!is_array($problems) || count($problems) > 5) {
            return new WP_Error(
                'invalid_data',
                __('Invalid problems data. Maximum 5 problems allowed.', 'directreach'),
                ['status' => 400]
            );
        }

        // Start transaction
        $wpdb->query('START TRANSACTION');

        try {
            // Delete existing problems if replacing
            if ($replace_existing) {
                $wpdb->delete(
                    $table_name,
                    ['journey_circle_id' => $circle_id],
                    ['%d']
                );
            }

            $created_ids = [];
            $primary_id = null;

            // Insert new problems
            foreach ($problems as $index => $problem) {
                $data = [
                    'journey_circle_id' => $circle_id,
                    'title'             => sanitize_text_field($problem['title']),
                    'description'       => wp_kses_post($problem['description'] ?? ''),
                    'is_primary'        => !empty($problem['isPrimary']) ? 1 : 0,
                    'position'          => isset($problem['position']) ? absint($problem['position']) : $index,
                    'asset_urls'        => wp_json_encode($problem['asset_urls'] ?? []),
                    'status'            => sanitize_text_field($problem['status'] ?? 'draft'),
                    'created_at'        => current_time('mysql'),
                    'updated_at'        => current_time('mysql')
                ];

                $wpdb->insert($table_name, $data, [
                    '%d', '%s', '%s', '%d', '%d', '%s', '%s', '%s', '%s'
                ]);

                $inserted_id = $wpdb->insert_id;
                $created_ids[] = $inserted_id;

                if ($data['is_primary']) {
                    $primary_id = $inserted_id;
                }
            }

            // Update journey circle primary_problem_id
            if ($primary_id) {
                $circle_table = $wpdb->prefix . 'dr_journey_circles';
                $wpdb->update(
                    $circle_table,
                    ['primary_problem_id' => $primary_id],
                    ['id' => $circle_id],
                    ['%d'],
                    ['%d']
                );
            }

            $wpdb->query('COMMIT');

            return rest_ensure_response([
                'success'     => true,
                'created_ids' => $created_ids,
                'count'       => count($created_ids),
                'message'     => __('Problems saved successfully.', 'directreach')
            ]);

        } catch (Exception $e) {
            $wpdb->query('ROLLBACK');
            
            return new WP_Error(
                'save_failed',
                $e->getMessage(),
                ['status' => 500]
            );
        }
    }

    /**
     * Get problem recommendations
     * 
     * Returns existing problems from database only.
     * If no problems exist, returns empty array and user adds manually.
     * 
     * @param WP_REST_Request $request
     * @return WP_REST_Response|WP_Error
     */
    public function get_problem_recommendations($request) {
        global $wpdb;
        
        $circle_id = absint($request->get_param('circle_id'));

        // Get existing problems from the database
        $table_name = $wpdb->prefix . 'dr_journey_problems';
        $existing_problems = $wpdb->get_results($wpdb->prepare(
            "SELECT * FROM {$table_name} WHERE journey_circle_id = %d ORDER BY position ASC",
            $circle_id
        ));

        $recommendations = [];
        
        if (!empty($existing_problems)) {
            $recommendations = array_map(function($problem) {
                return [
                    'id'       => (int) $problem->id,
                    'title'    => $problem->title,
                    'category' => $problem->description ?: '', // Using description as category
                    'position' => (int) $problem->position,
                    'is_primary' => (bool) $problem->is_primary,
                    'status'   => $problem->status
                ];
            }, $existing_problems);
        }

        return rest_ensure_response([
            'success'         => true,
            'recommendations' => $recommendations,
            'count'           => count($recommendations)
        ]);
    }
}