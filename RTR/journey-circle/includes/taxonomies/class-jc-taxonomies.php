<?php
/**
 * Register all custom taxonomies.
 *
 * @package Journey_Circle
 */

class JC_Taxonomies {

    /**
     * Initialize the class and register all taxonomies.
     *
     * @since 1.0.0
     */
    public function __construct() {
        add_action( 'init', array( $this, 'register_taxonomies' ) );
    }
    
    /**
     * Register all custom taxonomies.
     *
     * @since 1.0.0
     */
    public function register_taxonomies() {
        $this->register_industry_taxonomy();
        $this->register_asset_type_taxonomy();
        $this->register_status_taxonomy();
    }
    
    /**
     * Register Industry taxonomy.
     * Hierarchical taxonomy for industry targeting.
     *
     * @since 1.0.0
     */
    private function register_industry_taxonomy() {
        $labels = array(
            'name'                       => _x( 'Industries', 'Taxonomy General Name', 'journey-circle' ),
            'singular_name'              => _x( 'Industry', 'Taxonomy Singular Name', 'journey-circle' ),
            'menu_name'                  => __( 'Industries', 'journey-circle' ),
            'all_items'                  => __( 'All Industries', 'journey-circle' ),
            'parent_item'                => __( 'Parent Industry', 'journey-circle' ),
            'parent_item_colon'          => __( 'Parent Industry:', 'journey-circle' ),
            'new_item_name'              => __( 'New Industry Name', 'journey-circle' ),
            'add_new_item'               => __( 'Add New Industry', 'journey-circle' ),
            'edit_item'                  => __( 'Edit Industry', 'journey-circle' ),
            'update_item'                => __( 'Update Industry', 'journey-circle' ),
            'view_item'                  => __( 'View Industry', 'journey-circle' ),
            'separate_items_with_commas' => __( 'Separate industries with commas', 'journey-circle' ),
            'add_or_remove_items'        => __( 'Add or remove industries', 'journey-circle' ),
            'choose_from_most_used'      => __( 'Choose from the most used', 'journey-circle' ),
            'popular_items'              => __( 'Popular Industries', 'journey-circle' ),
            'search_items'               => __( 'Search Industries', 'journey-circle' ),
            'not_found'                  => __( 'Not Found', 'journey-circle' ),
        );
        
        $args = array(
            'labels'                     => $labels,
            'hierarchical'               => true,
            'public'                     => false,
            'show_ui'                    => true,
            'show_admin_column'          => true,
            'show_in_nav_menus'          => false,
            'show_tagcloud'              => false,
            'show_in_rest'               => true,
            'rest_base'                  => 'industries',
        );
        
        register_taxonomy( 'jc_industry', array( 'jc_journey_circle', 'jc_service_area' ), $args );
    }
    
    /**
     * Register Asset Type taxonomy.
     * Non-hierarchical taxonomy for content asset types.
     *
     * @since 1.0.0
     */
    private function register_asset_type_taxonomy() {
        $labels = array(
            'name'                       => _x( 'Asset Types', 'Taxonomy General Name', 'journey-circle' ),
            'singular_name'              => _x( 'Asset Type', 'Taxonomy Singular Name', 'journey-circle' ),
            'menu_name'                  => __( 'Asset Types', 'journey-circle' ),
            'all_items'                  => __( 'All Asset Types', 'journey-circle' ),
            'new_item_name'              => __( 'New Asset Type Name', 'journey-circle' ),
            'add_new_item'               => __( 'Add New Asset Type', 'journey-circle' ),
            'edit_item'                  => __( 'Edit Asset Type', 'journey-circle' ),
            'update_item'                => __( 'Update Asset Type', 'journey-circle' ),
            'view_item'                  => __( 'View Asset Type', 'journey-circle' ),
            'search_items'               => __( 'Search Asset Types', 'journey-circle' ),
            'not_found'                  => __( 'Not Found', 'journey-circle' ),
        );
        
        $args = array(
            'labels'                     => $labels,
            'hierarchical'               => false,
            'public'                     => false,
            'show_ui'                    => true,
            'show_admin_column'          => true,
            'show_in_nav_menus'          => false,
            'show_tagcloud'              => false,
            'show_in_rest'               => true,
            'rest_base'                  => 'asset-types',
        );
        
        register_taxonomy( 'jc_asset_type', array( 'jc_problem', 'jc_solution' ), $args );
        
        // Insert default asset types
        $this->insert_default_asset_types();
    }
    
    /**
     * Register Status taxonomy.
     * For tracking workflow status.
     *
     * @since 1.0.0
     */
    private function register_status_taxonomy() {
        $labels = array(
            'name'                       => _x( 'Status', 'Taxonomy General Name', 'journey-circle' ),
            'singular_name'              => _x( 'Status', 'Taxonomy Singular Name', 'journey-circle' ),
            'menu_name'                  => __( 'Status', 'journey-circle' ),
        );
        
        $args = array(
            'labels'                     => $labels,
            'hierarchical'               => false,
            'public'                     => false,
            'show_ui'                    => true,
            'show_admin_column'          => true,
            'show_in_rest'               => true,
        );
        
        register_taxonomy( 'jc_status', array( 'jc_journey_circle', 'jc_problem', 'jc_solution' ), $args );
        
        // Insert default statuses
        $this->insert_default_statuses();
    }
    
    /**
     * Insert default asset types if they don't exist.
     *
     * @since 1.0.0
     */
    private function insert_default_asset_types() {
        $asset_types = array(
            'long_article'   => 'Long Article (2000+ words)',
            'short_article'  => 'Short Article (500-1000 words)',
            'infographic'    => 'Infographic',
            'video_script'   => 'Video Script',
            'social_post'    => 'Social Media Post',
            'email_sequence' => 'Email Sequence',
        );
        
        foreach ( $asset_types as $slug => $name ) {
            if ( ! term_exists( $slug, 'jc_asset_type' ) ) {
                wp_insert_term( $name, 'jc_asset_type', array( 'slug' => $slug ) );
            }
        }
    }
    
    /**
     * Insert default statuses if they don't exist.
     *
     * @since 1.0.0
     */
    private function insert_default_statuses() {
        $statuses = array(
            'draft'      => 'Draft',
            'in_progress' => 'In Progress',
            'complete'   => 'Complete',
            'active'     => 'Active',
            'archived'   => 'Archived',
        );
        
        foreach ( $statuses as $slug => $name ) {
            if ( ! term_exists( $slug, 'jc_status' ) ) {
                wp_insert_term( $name, 'jc_status', array( 'slug' => $slug ) );
            }
        }
    }
}
