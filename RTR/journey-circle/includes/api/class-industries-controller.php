<?php
/**
 * Industry Taxonomy REST Controller
 * 
 * Handles REST API endpoints for industry taxonomy data.
 * 
 * @package DirectReach
 * @subpackage JourneyCircle
 * @since 2.0.0
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

class DR_Industries_Controller {

    /**
     * API namespace
     */
    const NAMESPACE = 'directreach/v2';

    /**
     * Register REST routes
     */
    public function register_routes() {
        // Get all industries
        register_rest_route(self::NAMESPACE, '/industries', [
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => [$this, 'get_industries'],
            'permission_callback' => [$this, 'check_permission']
        ]);

        // Get industry categories only
        register_rest_route(self::NAMESPACE, '/industries/categories', [
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => [$this, 'get_categories'],
            'permission_callback' => [$this, 'check_permission']
        ]);

        // Get subcategories for a category
        register_rest_route(self::NAMESPACE, '/industries/categories/(?P<category>[a-zA-Z0-9\s\-&]+)/subcategories', [
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => [$this, 'get_subcategories'],
            'permission_callback' => [$this, 'check_permission'],
            'args'                => [
                'category' => [
                    'required'          => true,
                    'sanitize_callback' => 'sanitize_text_field'
                ]
            ]
        ]);

        // Update industries for a journey circle
        register_rest_route(self::NAMESPACE, '/journey-circles/(?P<circle_id>\d+)/industries', [
            [
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => [$this, 'get_circle_industries'],
                'permission_callback' => [$this, 'check_permission']
            ],
            [
                'methods'             => WP_REST_Server::EDITABLE,
                'callback'            => [$this, 'update_circle_industries'],
                'permission_callback' => [$this, 'check_permission'],
                'args'                => [
                    'industries' => [
                        'required' => true,
                        'type'     => 'array'
                    ]
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
        if (!current_user_can('manage_campaigns') && !current_user_can('manage_options')) {
            return new WP_Error(
                'rest_forbidden',
                __('You do not have permission to access this resource.', 'directreach'),
                ['status' => 403]
            );
        }

        return true;
    }

    /**
     * Get complete industry taxonomy
     */
    public function get_industries($request) {
        $taxonomy = $this->get_industry_taxonomy();

        // Build flat list with values
        $flat_list = [];
        foreach ($taxonomy as $category => $subcategories) {
            if (empty($subcategories)) {
                $flat_list[] = [
                    'value'       => $category,
                    'label'       => $category,
                    'category'    => $category,
                    'subcategory' => null
                ];
            } else {
                foreach ($subcategories as $subcategory) {
                    $flat_list[] = [
                        'value'       => $category . '|' . $subcategory,
                        'label'       => $subcategory,
                        'category'    => $category,
                        'subcategory' => $subcategory
                    ];
                }
            }
        }

        return rest_ensure_response([
            'success'    => true,
            'taxonomy'   => $taxonomy,
            'flat_list'  => $flat_list,
            'categories' => array_keys($taxonomy)
        ]);
    }

    /**
     * Get industry categories only
     */
    public function get_categories($request) {
        $taxonomy = $this->get_industry_taxonomy();
        $categories = [];

        foreach ($taxonomy as $category => $subcategories) {
            $categories[] = [
                'name'              => $category,
                'subcategory_count' => count($subcategories)
            ];
        }

        return rest_ensure_response([
            'success'    => true,
            'categories' => $categories
        ]);
    }

    /**
     * Get subcategories for a category
     */
    public function get_subcategories($request) {
        $category = urldecode($request['category']);
        $taxonomy = $this->get_industry_taxonomy();

        if (!isset($taxonomy[$category])) {
            return new WP_Error(
                'not_found',
                __('Category not found.', 'directreach'),
                ['status' => 404]
            );
        }

        $subcategories = array_map(function($sub) use ($category) {
            return [
                'value' => $category . '|' . $sub,
                'label' => $sub
            ];
        }, $taxonomy[$category]);

        return rest_ensure_response([
            'success'       => true,
            'category'      => $category,
            'subcategories' => $subcategories
        ]);
    }

    /**
     * Get industries for a journey circle
     */
    public function get_circle_industries($request) {
        global $wpdb;

        $circle_id = absint($request['circle_id']);
        $table_name = $wpdb->prefix . 'dr_journey_circles';

        $circle = $wpdb->get_row(
            $wpdb->prepare(
                "SELECT industries FROM {$table_name} WHERE id = %d",
                $circle_id
            )
        );

        if (!$circle) {
            return new WP_Error(
                'not_found',
                __('Journey circle not found.', 'directreach'),
                ['status' => 404]
            );
        }

        $industries = json_decode($circle->industries, true) ?: [];

        return rest_ensure_response([
            'success'    => true,
            'industries' => $industries,
            'count'      => count($industries)
        ]);
    }

    /**
     * Update industries for a journey circle
     */
    public function update_circle_industries($request) {
        global $wpdb;

        $circle_id = absint($request['circle_id']);
        $industries = $request->get_param('industries');
        $table_name = $wpdb->prefix . 'dr_journey_circles';

        // Verify journey circle exists
        $exists = $wpdb->get_var(
            $wpdb->prepare("SELECT id FROM {$table_name} WHERE id = %d", $circle_id)
        );

        if (!$exists) {
            return new WP_Error(
                'not_found',
                __('Journey circle not found.', 'directreach'),
                ['status' => 404]
            );
        }

        // Sanitize industries array
        $sanitized_industries = array_map('sanitize_text_field', $industries);

        // Update
        $result = $wpdb->update(
            $table_name,
            [
                'industries'  => wp_json_encode($sanitized_industries),
                'updated_at'  => current_time('mysql')
            ],
            ['id' => $circle_id],
            ['%s', '%s'],
            ['%d']
        );

        if ($result === false) {
            return new WP_Error(
                'db_error',
                __('Failed to update industries.', 'directreach'),
                ['status' => 500]
            );
        }

        return rest_ensure_response([
            'success' => true,
            'message' => __('Industries updated successfully.', 'directreach'),
            'count'   => count($sanitized_industries)
        ]);
    }

    /**
     * Get complete industry taxonomy
     * Based on RB2B-compatible industry structure
     */
    private function get_industry_taxonomy() {
        // Use shared industry taxonomy from scoring system if available
        if (function_exists('rtr_get_industry_taxonomy')) {
            return rtr_get_industry_taxonomy();
        }

        // Fallback: try to include the config file
        $config_path = WP_PLUGIN_DIR . '/directreach/RTR/scoring-system/includes/industry-config.php';
        if (file_exists($config_path)) {
            require_once $config_path;
            if (function_exists('rtr_get_industry_taxonomy')) {
                return rtr_get_industry_taxonomy();
            }
        }

        // Final fallback: hardcoded taxonomy
        return [
            'Agriculture' => [
                'Agriculture',
                'Dairy',
                'Farming',
                'Fishery',
                'Ranching'
            ],
            'Automotive' => [],
            'Construction' => [
                'Construction',
                'Architecture & Planning',
                'Civil Engineering'
            ],
            'Creative Arts and Entertainment' => [
                'Creative Arts and Entertainment',
                'Animation',
                'Computer Games',
                'Design',
                'Entertainment',
                'Fine Art',
                'Gambling & Casinos',
                'Graphic Design',
                'Motion Pictures & Film',
                'Music',
                'Performing Arts',
                'Photography'
            ],
            'Education' => [
                'Education',
                'Education Management',
                'E-Learning',
                'Higher Education',
                'Primary/Secondary Education'
            ],
            'Energy' => [
                'Energy',
                'Oil & Energy',
                'Renewables & Environment'
            ],
            'Finance and Banking' => [
                'Finance and Banking',
                'Accounting',
                'Banking',
                'Capital Markets',
                'Financial Services',
                'Insurance',
                'Investment Banking',
                'Investment Management',
                'Venture Capital & Private Equity'
            ],
            'Food and Beverage' => [
                'Food & Beverages',
                'Food Production',
                'Restaurants',
                'Wine & Spirits'
            ],
            'Government and Public Administration' => [
                'Government and Public Administration',
                'Defense & Space',
                'Government Administration',
                'Government Relations',
                'International Affairs',
                'Judiciary',
                'Law Enforcement',
                'Legislative Office',
                'Military',
                'Political Organization',
                'Public Policy',
                'Public Safety'
            ],
            'Health and Pharmaceuticals' => [
                'Health and Pharmaceuticals',
                'Alternative Medicine',
                'Biotechnology',
                'Health, Wellness & Fitness',
                'Hospital & Health Care',
                'Medical Devices',
                'Medical Practice',
                'Mental Health Care',
                'Pharmaceuticals',
                'Veterinary'
            ],
            'Information Technology' => [
                'Information Technology',
                'Computer & Network Security',
                'Computer Hardware',
                'Computer Networking',
                'Computer Software',
                'Information Services',
                'Information Technology & Services'
            ],
            'Manufacturing' => [
                'Apparel & Fashion',
                'Building Materials',
                'Business Supplies & Equipment',
                'Chemicals',
                'Consumer Electronics',
                'Cosmetics',
                'Electrical & Electronic Manufacturing',
                'Furniture',
                'Glass, Ceramics & Concrete',
                'Industrial Automation',
                'Luxury Goods & Jewelry',
                'Machinery',
                'Manufacturing',
                'Mining & Metals',
                'Nanotechnology',
                'Packaging & Containers',
                'Paper & Forest Products',
                'Printing',
                'Railroad Manufacture',
                'Semiconductors',
                'Sporting Goods',
                'Textiles',
                'Tobacco'
            ],
            'Marketing & Advertising' => [
                'Marketing & Advertising',
                'Public Relations & Communications'
            ],
            'Media and Publishing' => [
                'Media and Publishing',
                'Broadcast Media',
                'Media Production',
                'Newspapers',
                'Online Media',
                'Writing & Editing'
            ],
            'Non-Profit and Social Services' => [
                'Non-Profit and Social Services',
                'Civic & Social Organization',
                'Fund-Raising',
                'Individual & Family Services',
                'Libraries',
                'Museums & Institutions',
                'Nonprofit Organization Management',
                'Philanthropy',
                'Religious Institutions'
            ],
            'Professional and Business Services' => [
                'Professional and Business Services',
                'Alternative Dispute Resolution',
                'Consumer Services',
                'Environmental Services',
                'Executive Office',
                'Facilities Services',
                'Human Resources',
                'International Trade and Development',
                'Law Practice',
                'Legal Services',
                'Management Consulting',
                'Market Research',
                'Outsourcing/Offshoring',
                'Program Development',
                'Research',
                'Security & Investigations',
                'Staffing & Recruiting',
                'Think Tanks',
                'Translation & Localization'
            ],
            'Real Estate' => [
                'Commercial Real Estate',
                'Real Estate'
            ],
            'Retail' => [
                'Arts & Crafts',
                'Consumer Goods',
                'Retail',
                'Supermarkets',
                'Wholesale'
            ],
            'Telecommunications' => [
                'Telecommunications',
                'Wireless'
            ],
            'Tourism and Hospitality' => [
                'Events Services',
                'Hospitality',
                'Leisure, Travel & Tourism',
                'Recreational Facilities & Services',
                'Sports',
                'Tourism and Hospitality'
            ],
            'Transportation and Logistics' => [
                'Transportation and Logistics',
                'Aviation & Aerospace',
                'Import & Export',
                'Logistics & Supply Chain',
                'Maritime',
                'Package/Freight Delivery',
                'Transportation/Trucking/Railroad'
            ],
            'Utilities' => []
        ];
    }
}