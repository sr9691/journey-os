<?php
/**
 * Register all custom post types.
 *
 * @package Journey_Circle
 */

class JC_Post_Types {

    /**
     * Initialize the class and register all post types.
     *
     * @since 1.0.0
     */
    public function __construct() {
        add_action( 'init', array( $this, 'register_post_types' ) );
    }
    
    /**
     * Register all custom post types.
     *
     * @since 1.0.0
     */
    public function register_post_types() {
        $this->register_service_area();
        $this->register_journey_circle();
        $this->register_problem();
        $this->register_solution();
        $this->register_offer();
        $this->register_brain_content();
    }
    
    /**
     * Register Service Area post type.
     *
     * @since 1.0.0
     */
    private function register_service_area() {
        $labels = array(
            'name'                  => _x( 'Service Areas', 'Post Type General Name', 'journey-circle' ),
            'singular_name'         => _x( 'Service Area', 'Post Type Singular Name', 'journey-circle' ),
            'menu_name'             => __( 'Service Areas', 'journey-circle' ),
            'name_admin_bar'        => __( 'Service Area', 'journey-circle' ),
            'archives'              => __( 'Service Area Archives', 'journey-circle' ),
            'attributes'            => __( 'Service Area Attributes', 'journey-circle' ),
            'parent_item_colon'     => __( 'Parent Service Area:', 'journey-circle' ),
            'all_items'             => __( 'All Service Areas', 'journey-circle' ),
            'add_new_item'          => __( 'Add New Service Area', 'journey-circle' ),
            'add_new'               => __( 'Add New', 'journey-circle' ),
            'new_item'              => __( 'New Service Area', 'journey-circle' ),
            'edit_item'             => __( 'Edit Service Area', 'journey-circle' ),
            'update_item'           => __( 'Update Service Area', 'journey-circle' ),
            'view_item'             => __( 'View Service Area', 'journey-circle' ),
            'view_items'            => __( 'View Service Areas', 'journey-circle' ),
            'search_items'          => __( 'Search Service Area', 'journey-circle' ),
            'not_found'             => __( 'Not found', 'journey-circle' ),
            'not_found_in_trash'    => __( 'Not found in Trash', 'journey-circle' ),
        );
        
        $args = array(
            'label'                 => __( 'Service Area', 'journey-circle' ),
            'description'           => __( 'Service or product areas for journey circles', 'journey-circle' ),
            'labels'                => $labels,
            'supports'              => array( 'title', 'editor', 'author', 'custom-fields' ),
            'hierarchical'          => false,
            'public'                => false,
            'show_ui'               => true,
            'show_in_menu'          => 'journey-circle',
            'menu_position'         => 25,
            'menu_icon'             => 'dashicons-networking',
            'show_in_admin_bar'     => true,
            'show_in_nav_menus'     => false,
            'can_export'            => true,
            'has_archive'           => false,
            'exclude_from_search'   => true,
            'publicly_queryable'    => false,
            'capability_type'       => 'post',
            'show_in_rest'          => true,
            'rest_base'             => 'service-areas',
        );
        
        register_post_type( 'jc_service_area', $args );
    }
    
    /**
     * Register Journey Circle post type.
     *
     * @since 1.0.0
     */
    private function register_journey_circle() {
        $labels = array(
            'name'                  => _x( 'Journey Circles', 'Post Type General Name', 'journey-circle' ),
            'singular_name'         => _x( 'Journey Circle', 'Post Type Singular Name', 'journey-circle' ),
            'menu_name'             => __( 'Journey Circles', 'journey-circle' ),
            'name_admin_bar'        => __( 'Journey Circle', 'journey-circle' ),
            'all_items'             => __( 'All Journey Circles', 'journey-circle' ),
            'add_new_item'          => __( 'Add New Journey Circle', 'journey-circle' ),
            'add_new'               => __( 'Add New', 'journey-circle' ),
            'new_item'              => __( 'New Journey Circle', 'journey-circle' ),
            'edit_item'             => __( 'Edit Journey Circle', 'journey-circle' ),
            'update_item'           => __( 'Update Journey Circle', 'journey-circle' ),
            'view_item'             => __( 'View Journey Circle', 'journey-circle' ),
            'search_items'          => __( 'Search Journey Circle', 'journey-circle' ),
        );
        
        $args = array(
            'label'                 => __( 'Journey Circle', 'journey-circle' ),
            'description'           => __( 'Complete journey circles with problems, solutions, and offers', 'journey-circle' ),
            'labels'                => $labels,
            'supports'              => array( 'title', 'custom-fields' ),
            'hierarchical'          => false,
            'public'                => false,
            'show_ui'               => true,
            'show_in_menu'          => 'journey-circle',
            'show_in_admin_bar'     => true,
            'show_in_nav_menus'     => false,
            'can_export'            => true,
            'has_archive'           => false,
            'exclude_from_search'   => true,
            'publicly_queryable'    => false,
            'capability_type'       => 'post',
            'show_in_rest'          => true,
            'rest_base'             => 'journey-circles',
        );
        
        register_post_type( 'jc_journey_circle', $args );
    }
    
    /**
     * Register Problem post type.
     *
     * @since 1.0.0
     */
    private function register_problem() {
        $labels = array(
            'name'                  => _x( 'Problems', 'Post Type General Name', 'journey-circle' ),
            'singular_name'         => _x( 'Problem', 'Post Type Singular Name', 'journey-circle' ),
            'menu_name'             => __( 'Problems', 'journey-circle' ),
            'all_items'             => __( 'All Problems', 'journey-circle' ),
            'add_new_item'          => __( 'Add New Problem', 'journey-circle' ),
            'edit_item'             => __( 'Edit Problem', 'journey-circle' ),
        );
        
        $args = array(
            'label'                 => __( 'Problem', 'journey-circle' ),
            'description'           => __( 'Problems in journey circles (outer ring)', 'journey-circle' ),
            'labels'                => $labels,
            'supports'              => array( 'title', 'editor', 'custom-fields' ),
            'hierarchical'          => false,
            'public'                => false,
            'show_ui'               => true,
            'show_in_menu'          => 'journey-circle',
            'capability_type'       => 'post',
            'show_in_rest'          => true,
            'rest_base'             => 'problems',
        );
        
        register_post_type( 'jc_problem', $args );
    }
    
    /**
     * Register Solution post type.
     *
     * @since 1.0.0
     */
    private function register_solution() {
        $labels = array(
            'name'                  => _x( 'Solutions', 'Post Type General Name', 'journey-circle' ),
            'singular_name'         => _x( 'Solution', 'Post Type Singular Name', 'journey-circle' ),
            'menu_name'             => __( 'Solutions', 'journey-circle' ),
            'all_items'             => __( 'All Solutions', 'journey-circle' ),
            'add_new_item'          => __( 'Add New Solution', 'journey-circle' ),
            'edit_item'             => __( 'Edit Solution', 'journey-circle' ),
        );
        
        $args = array(
            'label'                 => __( 'Solution', 'journey-circle' ),
            'description'           => __( 'Solutions in journey circles (middle ring)', 'journey-circle' ),
            'labels'                => $labels,
            'supports'              => array( 'title', 'editor', 'custom-fields' ),
            'hierarchical'          => false,
            'public'                => false,
            'show_ui'               => true,
            'show_in_menu'          => 'journey-circle',
            'capability_type'       => 'post',
            'show_in_rest'          => true,
            'rest_base'             => 'solutions',
        );
        
        register_post_type( 'jc_solution', $args );
    }
    
    /**
     * Register Offer post type.
     *
     * @since 1.0.0
     */
    private function register_offer() {
        $labels = array(
            'name'                  => _x( 'Offers', 'Post Type General Name', 'journey-circle' ),
            'singular_name'         => _x( 'Offer', 'Post Type Singular Name', 'journey-circle' ),
            'menu_name'             => __( 'Offers', 'journey-circle' ),
            'all_items'             => __( 'All Offers', 'journey-circle' ),
            'add_new_item'          => __( 'Add New Offer', 'journey-circle' ),
            'edit_item'             => __( 'Edit Offer', 'journey-circle' ),
        );
        
        $args = array(
            'label'                 => __( 'Offer', 'journey-circle' ),
            'description'           => __( 'Offers in journey circles (center)', 'journey-circle' ),
            'labels'                => $labels,
            'supports'              => array( 'title', 'editor', 'custom-fields' ),
            'hierarchical'          => false,
            'public'                => false,
            'show_ui'               => true,
            'show_in_menu'          => 'journey-circle',
            'capability_type'       => 'post',
            'show_in_rest'          => true,
            'rest_base'             => 'offers',
        );
        
        register_post_type( 'jc_offer', $args );
    }
    
    /**
     * Register Brain Content post type.
     *
     * @since 1.0.0
     */
    private function register_brain_content() {
        $labels = array(
            'name'                  => _x( 'Brain Content', 'Post Type General Name', 'journey-circle' ),
            'singular_name'         => _x( 'Brain Content', 'Post Type Singular Name', 'journey-circle' ),
            'menu_name'             => __( 'Brain Content', 'journey-circle' ),
            'all_items'             => __( 'All Brain Content', 'journey-circle' ),
            'add_new_item'          => __( 'Add New Content', 'journey-circle' ),
            'edit_item'             => __( 'Edit Content', 'journey-circle' ),
        );
        
        $args = array(
            'label'                 => __( 'Brain Content', 'journey-circle' ),
            'description'           => __( 'Source material for AI content generation', 'journey-circle' ),
            'labels'                => $labels,
            'supports'              => array( 'title', 'editor', 'custom-fields' ),
            'hierarchical'          => false,
            'public'                => false,
            'show_ui'               => true,
            'show_in_menu'          => 'journey-circle',
            'capability_type'       => 'post',
            'show_in_rest'          => true,
            'rest_base'             => 'brain-content',
        );
        
        register_post_type( 'jc_brain_content', $args );
    }
}
