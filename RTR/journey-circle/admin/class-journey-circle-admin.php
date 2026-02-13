<?php
/**
 * The admin-specific functionality of the plugin.
 *
 * @package Journey_Circle
 */

class Journey_Circle_Admin {

    /**
     * The ID of this plugin.
     *
     * @since    1.0.0
     * @access   private
     * @var      string    $plugin_name    The ID of this plugin.
     */
    private $plugin_name;

    /**
     * The version of this plugin.
     *
     * @since    1.0.0
     * @access   private
     * @var      string    $version    The current version of this plugin.
     */
    private $version;

    /**
     * Initialize the class and set its properties.
     *
     * @since    1.0.0
     * @param    string    $plugin_name       The name of this plugin.
     * @param    string    $version    The version of this plugin.
     */
    public function __construct( $plugin_name, $version ) {
        $this->plugin_name = $plugin_name;
        $this->version = $version;
    }

    /**
     * Register the stylesheets for the admin area.
     *
     * @since    1.0.0
     */
    public function enqueue_styles() {
        // Only load on Journey Circle pages
        $screen = get_current_screen();
        if ( ! $screen || strpos( $screen->id, 'journey-circle' ) === false ) {
            return;
        }

        // Base admin styles
        wp_enqueue_style(
            $this->plugin_name,
            JOURNEY_CIRCLE_PLUGIN_URL . 'admin/css/journey-circle-admin.css',
            array(),
            $this->version,
            'all'
        );

        // Journey Circle Creator styles (only on creator page)
        if ( strpos( $screen->id, 'journey-circle-creator' ) !== false ) {
            // Main workflow styles
            wp_enqueue_style(
                $this->plugin_name . '-main',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/css/journey-circle.css',
                array( $this->plugin_name ),
                $this->version
            );

            // Step-specific styles
            wp_enqueue_style(
                $this->plugin_name . '-steps456',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/css/journey-circle-steps456.css',
                array( $this->plugin_name . '-main' ),
                $this->version
            );

            wp_enqueue_style(
                $this->plugin_name . '-steps78',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/css/journey-circle-steps78.css',
                array( $this->plugin_name . '-main' ),
                $this->version
            );

            // Canvas visualization styles
            wp_enqueue_style(
                $this->plugin_name . '-canvas',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/css/journey-circle-canvas.css',
                array( $this->plugin_name . '-main' ),
                $this->version
            );

            // AI feature styles
            wp_enqueue_style(
                $this->plugin_name . '-ai',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/css/journey-circle-ai.css',
                array( $this->plugin_name . '-main' ),
                $this->version
            );

            // Asset creation styles
            wp_enqueue_style(
                $this->plugin_name . '-asset',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/css/journey-circle-asset.css',
                array( $this->plugin_name . '-main' ),
                $this->version
            );

            // Completion flow styles
            wp_enqueue_style(
                $this->plugin_name . '-completion',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/css/journey-completion.css',
                array( $this->plugin_name . '-main' ),
                $this->version
            );
        }
    }

    /**
     * Register the JavaScript for the admin area.
     *
     * @since    1.0.0
     */
    public function enqueue_scripts() {
        // Only load on Journey Circle pages
        $screen = get_current_screen();
        if ( ! $screen || strpos( $screen->id, 'journey-circle' ) === false ) {
            return;
        }

        // Base admin script
        wp_enqueue_script(
            $this->plugin_name,
            JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/journey-circle-admin.js',
            array( 'jquery' ),
            $this->version,
            true
        );

        // Journey Circle Creator scripts (only on creator page)
        if ( strpos( $screen->id, 'journey-circle-creator' ) !== false ) {
            // Core workflow module
            wp_enqueue_script(
                $this->plugin_name . '-workflow',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/journey-circle-workflow.js',
                array( 'jquery', $this->plugin_name ),
                $this->version,
                true
            );

            // Canvas renderer
            wp_enqueue_script(
                $this->plugin_name . '-renderer',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/journey-circle-renderer.js',
                array( $this->plugin_name . '-workflow' ),
                $this->version,
                true
            );

            // Manager modules
            wp_enqueue_script(
                $this->plugin_name . '-brain-content',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/brain-content-manager.js',
                array( $this->plugin_name . '-workflow' ),
                $this->version,
                true
            );

            wp_enqueue_script(
                $this->plugin_name . '-service-area',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/service-area-manager.js',
                array( $this->plugin_name . '-workflow' ),
                $this->version,
                true
            );

            wp_enqueue_script(
                $this->plugin_name . '-problem-solution',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/problem-solution-manager.js',
                array( $this->plugin_name . '-workflow' ),
                $this->version,
                true
            );

            wp_enqueue_script(
                $this->plugin_name . '-solution-offer',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/solution-offer-manager.js',
                array( $this->plugin_name . '-workflow' ),
                $this->version,
                true
            );

            // AI modules
            wp_enqueue_script(
                $this->plugin_name . '-ai-title',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/ai-title-manager.js',
                array( $this->plugin_name . '-workflow' ),
                $this->version,
                true
            );

            wp_enqueue_script(
                $this->plugin_name . '-asset-creator',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/asset-creator.js',
                array( $this->plugin_name . '-workflow' ),
                $this->version,
                true
            );

            // Completion module
            wp_enqueue_script(
                $this->plugin_name . '-completion',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/journey-completion.js',
                array( $this->plugin_name . '-workflow' ),
                $this->version,
                true
            );

            // Client manager extension (for Campaign Builder integration)
            wp_enqueue_script(
                $this->plugin_name . '-client-extension',
                JOURNEY_CIRCLE_PLUGIN_URL . 'admin/js/modules/client-manager-journey-extension.js',
                array( $this->plugin_name . '-workflow' ),
                $this->version,
                true
            );
        }

        // Localize script with REST API data
        wp_localize_script(
            $this->plugin_name,
            'journeyCircleData',
            array(
                'ajaxUrl'   => admin_url( 'admin-ajax.php' ),
                'nonce'     => wp_create_nonce( 'journey_circle_nonce' ),
                'restUrl'   => rest_url( 'journey-circle/v1' ),
                'restNonce' => wp_create_nonce( 'wp_rest' ),
                'pluginUrl' => JOURNEY_CIRCLE_PLUGIN_URL,
            )
        );
    }

    /**
     * Add menu items to WordPress admin.
     *
     * @since    1.0.0
     */
    public function add_plugin_admin_menu() {
        // Main menu
        add_menu_page(
            __( 'Journey Circle', 'journey-circle' ),
            __( 'Journey Circle', 'journey-circle' ),
            'manage_options',
            'journey-circle',
            array( $this, 'display_dashboard_page' ),
            'dashicons-networking',
            25
        );

        // Dashboard submenu
        add_submenu_page(
            'journey-circle',
            __( 'Dashboard', 'journey-circle' ),
            __( 'Dashboard', 'journey-circle' ),
            'manage_options',
            'journey-circle',
            array( $this, 'display_dashboard_page' )
        );

        // Journey Circle Creator submenu
        add_submenu_page(
            'journey-circle',
            __( 'Create Journey Circle', 'journey-circle' ),
            __( 'Create New', 'journey-circle' ),
            'manage_options',
            'journey-circle-creator',
            array( $this, 'display_creator_page' )
        );

        // Settings submenu
        add_submenu_page(
            'journey-circle',
            __( 'Settings', 'journey-circle' ),
            __( 'Settings', 'journey-circle' ),
            'manage_options',
            'journey-circle-settings',
            array( $this, 'display_settings_page' )
        );
    }

    /**
     * Display the dashboard page.
     *
     * @since    1.0.0
     */
    public function display_dashboard_page() {
        include_once JOURNEY_CIRCLE_PLUGIN_DIR . 'admin/views/dashboard.php';
    }

    /**
     * Display the Journey Circle Creator page.
     *
     * @since    1.0.0
     */
    public function display_creator_page() {
        include_once JOURNEY_CIRCLE_PLUGIN_DIR . 'admin/views/journey-circle/journey-circle-creator.php';
    }

    /**
     * Display the settings page.
     *
     * @since    1.0.0
     */
    public function display_settings_page() {
        include_once JOURNEY_CIRCLE_PLUGIN_DIR . 'admin/views/settings.php';
    }
}
