<?php
/**
 * The core plugin class.
 *
 * This is used to define internationalization, admin-specific hooks, and
 * public-facing site hooks.
 *
 * @package Journey_Circle
 */

class Journey_Circle {

    /**
     * The loader that's responsible for maintaining and registering all hooks.
     *
     * @since    1.0.0
     * @access   protected
     * @var      Journey_Circle_Loader    $loader    Maintains and registers all hooks for the plugin.
     */
    protected $loader;

    /**
     * The unique identifier of this plugin.
     *
     * @since    1.0.0
     * @access   protected
     * @var      string    $plugin_name    The string used to uniquely identify this plugin.
     */
    protected $plugin_name;

    /**
     * The current version of the plugin.
     *
     * @since    1.0.0
     * @access   protected
     * @var      string    $version    The current version of the plugin.
     */
    protected $version;

    /**
     * Define the core functionality of the plugin.
     *
     * @since    1.0.0
     */
    public function __construct() {
        $this->version = JOURNEY_CIRCLE_VERSION;
        $this->plugin_name = 'journey-circle';

        $this->load_dependencies();
        $this->define_admin_hooks();
    }

    /**
     * Load the required dependencies for this plugin.
     *
     * @since    1.0.0
     * @access   private
     */
    private function load_dependencies() {
        /**
         * The class responsible for orchestrating the actions and filters of the
         * core plugin.
         */
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/class-journey-circle-loader.php';

        /**
         * Post types and taxonomies
         */
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/post-types/class-jc-post-types.php';
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/taxonomies/class-jc-taxonomies.php';

        /**
         * The class responsible for defining all actions that occur in the admin area.
         */
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'admin/class-journey-circle-admin.php';
        
        /**
         * Model classes for CRUD operations
         */
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/models/class-service-area-manager.php';
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/models/class-journey-circle-manager.php';
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/models/class-brain-content-manager.php';

        /**
         * Journey Circle specific classes
         */
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/journey-circle/class-journey-circle-page.php';
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/journey-circle/class-ai-content-generator.php';

        /**
         * REST API Controllers
         */
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/api/class-industries-controller.php';
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/api/class-journey-problems-controller.php';
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/api/class-journey-solutions-controller.php';
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/api/class-ai-content-controller.php';
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/api/class-journey-completion-controller.php';
        require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/api/class-client-journey-status-controller.php';

        $this->loader = new Journey_Circle_Loader();
    }

    /**
     * Register all of the hooks related to the admin area functionality
     * of the plugin.
     *
     * @since    1.0.0
     * @access   private
     */
    private function define_admin_hooks() {
        // Initialize post types and taxonomies
        new JC_Post_Types();
        new JC_Taxonomies();

        $plugin_admin = new Journey_Circle_Admin( $this->get_plugin_name(), $this->get_version() );

        $this->loader->add_action( 'admin_enqueue_scripts', $plugin_admin, 'enqueue_styles' );
        $this->loader->add_action( 'admin_enqueue_scripts', $plugin_admin, 'enqueue_scripts' );
        $this->loader->add_action( 'admin_menu', $plugin_admin, 'add_plugin_admin_menu' );

        // Register REST API routes
        $this->loader->add_action( 'rest_api_init', $this, 'register_rest_routes' );
    }

    /**
     * Register REST API routes for all controllers.
     *
     * @since    1.0.0
     */
    public function register_rest_routes() {
        // Industries controller
        $industries_controller = new JC_Industries_Controller();
        $industries_controller->register_routes();

        // Journey Problems controller
        $problems_controller = new JC_Journey_Problems_Controller();
        $problems_controller->register_routes();

        // Journey Solutions controller
        $solutions_controller = new JC_Journey_Solutions_Controller();
        $solutions_controller->register_routes();

        // AI Content controller
        $ai_controller = new JC_AI_Content_Controller();
        $ai_controller->register_routes();

        // Journey Completion controller
        $completion_controller = new JC_Journey_Completion_Controller();
        $completion_controller->register_routes();

        // Client Journey Status controller
        $status_controller = new JC_Client_Journey_Status_Controller();
        $status_controller->register_routes();
    }

    /**
     * Run the loader to execute all of the hooks with WordPress.
     *
     * @since    1.0.0
     */
    public function run() {
        $this->loader->run();
    }

    /**
     * The name of the plugin used to uniquely identify it within the context of
     * WordPress and to define internationalization functionality.
     *
     * @since     1.0.0
     * @return    string    The name of the plugin.
     */
    public function get_plugin_name() {
        return $this->plugin_name;
    }

    /**
     * Retrieve the version number of the plugin.
     *
     * @since     1.0.0
     * @return    string    The version number of the plugin.
     */
    public function get_version() {
        return $this->version;
    }
}
