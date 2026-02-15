<?php
/**
 * Service Areas REST Controller
 *
 * Handles REST API endpoints for service areas.
 *
 * @package Journey_Circle
 * @since 1.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Journey_Circle_Service_Areas_Controller extends WP_REST_Controller {

    /**
     * Namespace
     *
     * @var string
     */
    protected $namespace = 'directreach/v2';

    /**
     * Rest base
     *
     * @var string
     */
    protected $rest_base = 'service-areas';

    /**
     * Service Area Manager instance
     *
     * @var Service_Area_Manager
     */
    private $manager;

    /**
     * Constructor
     */
    public function __construct() {
        $this->manager = new Service_Area_Manager();
    }

    /**
     * Register routes
     */
    public function register_routes() {
        // GET /service-areas?client_id={id} - List service areas for client
        // POST /service-areas - Create new service area
        register_rest_route(
            $this->namespace,
            '/' . $this->rest_base,
            array(
                array(
                    'methods'             => WP_REST_Server::READABLE,
                    'callback'            => array( $this, 'get_items' ),
                    'permission_callback' => array( $this, 'get_items_permissions_check' ),
                    'args'                => array(
                        'client_id' => array(
                            'required'          => true,
                            'type'              => 'integer',
                            'sanitize_callback' => 'absint',
                            'description'       => 'Client ID to filter service areas',
                        ),
                    ),
                ),
                array(
                    'methods'             => WP_REST_Server::CREATABLE,
                    'callback'            => array( $this, 'create_item' ),
                    'permission_callback' => array( $this, 'create_item_permissions_check' ),
                    'args'                => $this->get_endpoint_args_for_item_schema( WP_REST_Server::CREATABLE ),
                ),
            )
        );

        // GET /service-areas/{id} - Get single service area
        // PUT /service-areas/{id} - Update service area
        // DELETE /service-areas/{id} - Delete service area
        register_rest_route(
            $this->namespace,
            '/' . $this->rest_base . '/(?P<id>[\d]+)',
            array(
                array(
                    'methods'             => WP_REST_Server::READABLE,
                    'callback'            => array( $this, 'get_item' ),
                    'permission_callback' => array( $this, 'get_item_permissions_check' ),
                    'args'                => array(
                        'id' => array(
                            'required'          => true,
                            'type'              => 'integer',
                            'sanitize_callback' => 'absint',
                        ),
                    ),
                ),
                array(
                    'methods'             => WP_REST_Server::EDITABLE,
                    'callback'            => array( $this, 'update_item' ),
                    'permission_callback' => array( $this, 'update_item_permissions_check' ),
                    'args'                => $this->get_endpoint_args_for_item_schema( WP_REST_Server::EDITABLE ),
                ),
                array(
                    'methods'             => WP_REST_Server::DELETABLE,
                    'callback'            => array( $this, 'delete_item' ),
                    'permission_callback' => array( $this, 'delete_item_permissions_check' ),
                    'args'                => array(
                        'id' => array(
                            'required'          => true,
                            'type'              => 'integer',
                            'sanitize_callback' => 'absint',
                        ),
                        'force' => array(
                            'default'           => false,
                            'type'              => 'boolean',
                            'description'       => 'Force delete even if service area has journey circles',
                        ),
                    ),
                ),
            )
        );
    }

    /**
     * Check if user can list service areas
     *
     * @param WP_REST_Request $request Request object.
     * @return bool|WP_Error
     */
    public function get_items_permissions_check( $request ) {
        if ( ! is_user_logged_in() ) {
            return new WP_Error(
                'rest_forbidden',
                __( 'You must be logged in to view service areas.', 'journey-circle' ),
                array( 'status' => 401 )
            );
        }

        return true;
    }

    /**
     * Get service areas for a client
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function get_items( $request ) {
        $client_id = $request->get_param( 'client_id' );

        if ( empty( $client_id ) ) {
            return new WP_Error(
                'missing_client_id',
                __( 'Client ID is required.', 'journey-circle' ),
                array( 'status' => 400 )
            );
        }

        $service_areas = $this->manager->get_by_client( $client_id );

        return rest_ensure_response( $service_areas );
    }

    /**
     * Check if user can view a service area
     *
     * @param WP_REST_Request $request Request object.
     * @return bool|WP_Error
     */
    public function get_item_permissions_check( $request ) {
        return $this->get_items_permissions_check( $request );
    }

    /**
     * Get a single service area
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function get_item( $request ) {
        $id = $request->get_param( 'id' );
        $service_area = $this->manager->get( $id );

        if ( is_wp_error( $service_area ) ) {
            return new WP_Error(
                'not_found',
                __( 'Service area not found.', 'journey-circle' ),
                array( 'status' => 404 )
            );
        }

        return rest_ensure_response( $service_area );
    }

    /**
     * Check if user can create service areas
     *
     * @param WP_REST_Request $request Request object.
     * @return bool|WP_Error
     */
    public function create_item_permissions_check( $request ) {
        if ( ! is_user_logged_in() ) {
            return new WP_Error(
                'rest_forbidden',
                __( 'You must be logged in to create service areas.', 'journey-circle' ),
                array( 'status' => 401 )
            );
        }

        return true;
    }

    /**
     * Create a new service area
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function create_item( $request ) {
        $args = array(
            'title'       => $request->get_param( 'title' ),
            'description' => $request->get_param( 'description' ) ?? '',
            'client_id'   => $request->get_param( 'client_id' ),
            'status'      => $request->get_param( 'status' ) ?? 'draft',
        );

        // Validate
        $validation = $this->manager->validate( $args );
        if ( is_wp_error( $validation ) ) {
            return $validation;
        }

        // Create
        $id = $this->manager->create( $args );

        if ( is_wp_error( $id ) ) {
            return $id;
        }

        $service_area = $this->manager->get( $id );

        return rest_ensure_response( $service_area );
    }

    /**
     * Check if user can update service areas
     *
     * @param WP_REST_Request $request Request object.
     * @return bool|WP_Error
     */
    public function update_item_permissions_check( $request ) {
        return $this->create_item_permissions_check( $request );
    }

    /**
     * Update a service area
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function update_item( $request ) {
        $id = $request->get_param( 'id' );
        
        $args = array();
        
        if ( $request->has_param( 'title' ) ) {
            $args['title'] = $request->get_param( 'title' );
        }
        
        // Accept 'name' as alias for 'title' (JS compatibility)
        if ( $request->has_param( 'name' ) && ! isset( $args['title'] ) ) {
            $args['title'] = $request->get_param( 'name' );
        }
        
        if ( $request->has_param( 'description' ) ) {
            $args['description'] = $request->get_param( 'description' );
        }
        
        if ( $request->has_param( 'status' ) ) {
            $args['status'] = $request->get_param( 'status' );
        }

        $result = $this->manager->update( $id, $args );

        if ( is_wp_error( $result ) ) {
            return $result;
        }

        $service_area = $this->manager->get( $id );

        return rest_ensure_response( $service_area );
    }

    /**
     * Check if user can delete service areas
     *
     * @param WP_REST_Request $request Request object.
     * @return bool|WP_Error
     */
    public function delete_item_permissions_check( $request ) {
        return $this->create_item_permissions_check( $request );
    }

    /**
     * Delete a service area
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response|WP_Error
     */
    public function delete_item( $request ) {
        $id = $request->get_param( 'id' );
        $force = $request->get_param( 'force' );

        $result = $this->manager->delete( $id, $force );

        if ( is_wp_error( $result ) ) {
            return $result;
        }

        if ( ! $result ) {
            return new WP_Error(
                'delete_failed',
                __( 'Failed to delete service area.', 'journey-circle' ),
                array( 'status' => 500 )
            );
        }

        return rest_ensure_response( array(
            'deleted' => true,
            'id'      => $id,
        ) );
    }

    /**
     * Get schema for endpoint arguments
     *
     * @return array
     */
    public function get_item_schema() {
        return array(
            '$schema'    => 'http://json-schema.org/draft-04/schema#',
            'title'      => 'service_area',
            'type'       => 'object',
            'properties' => array(
                'id' => array(
                    'description' => __( 'Unique identifier for the service area.', 'journey-circle' ),
                    'type'        => 'integer',
                    'context'     => array( 'view', 'edit' ),
                    'readonly'    => true,
                ),
                'title' => array(
                    'description' => __( 'Title of the service area.', 'journey-circle' ),
                    'type'        => 'string',
                    'context'     => array( 'view', 'edit' ),
                    'required'    => true,
                ),
                'description' => array(
                    'description' => __( 'Description of the service area.', 'journey-circle' ),
                    'type'        => 'string',
                    'context'     => array( 'view', 'edit' ),
                ),
                'client_id' => array(
                    'description' => __( 'Client ID this service area belongs to.', 'journey-circle' ),
                    'type'        => 'integer',
                    'context'     => array( 'view', 'edit' ),
                    'required'    => true,
                ),
                'status' => array(
                    'description' => __( 'Status of the service area.', 'journey-circle' ),
                    'type'        => 'string',
                    'enum'        => array( 'draft', 'active', 'archived' ),
                    'context'     => array( 'view', 'edit' ),
                    'default'     => 'draft',
                ),
                'created_at' => array(
                    'description' => __( 'Date the service area was created.', 'journey-circle' ),
                    'type'        => 'string',
                    'format'      => 'date-time',
                    'context'     => array( 'view' ),
                    'readonly'    => true,
                ),
                'updated_at' => array(
                    'description' => __( 'Date the service area was last updated.', 'journey-circle' ),
                    'type'        => 'string',
                    'format'      => 'date-time',
                    'context'     => array( 'view' ),
                    'readonly'    => true,
                ),
            ),
        );
    }
}

// Routes are registered via Journey_Circle::register_rest_routes()