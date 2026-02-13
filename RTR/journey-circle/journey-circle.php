<?php
/**
 * Plugin Name: Journey Circle Creator
 * Plugin URI: https://directreach.com/journey-circle
 * Description: Create structured problem → solution → offer content ecosystems with AI-assisted content generation for marketing campaigns.
 * Version: 1.0.0
 * Author: DirectReach
 * Author URI: https://directreach.com
 * License: GPL-2.0+
 * License URI: http://www.gnu.org/licenses/gpl-2.0.txt
 * Text Domain: journey-circle
 * Domain Path: /languages
 *
 * @package Journey_Circle
 */

// If this file is called directly, abort.
if ( ! defined( 'WPINC' ) ) {
    die;
}

/**
 * Current plugin version.
 */
define( 'JOURNEY_CIRCLE_VERSION', '1.0.0' );
define( 'JOURNEY_CIRCLE_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'JOURNEY_CIRCLE_PLUGIN_URL', plugin_dir_url( __FILE__ ) );
define( 'JOURNEY_CIRCLE_PLUGIN_BASENAME', plugin_basename( __FILE__ ) );

/**
 * The code that runs during plugin activation.
 */
function activate_journey_circle() {
    require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/class-journey-circle-activator.php';
    Journey_Circle_Activator::activate();
}

/**
 * The code that runs during plugin deactivation.
 */
function deactivate_journey_circle() {
    require_once JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/class-journey-circle-deactivator.php';
    Journey_Circle_Deactivator::deactivate();
}

register_activation_hook( __FILE__, 'activate_journey_circle' );
register_deactivation_hook( __FILE__, 'deactivate_journey_circle' );

/**
 * The core plugin class.
 */
require JOURNEY_CIRCLE_PLUGIN_DIR . 'includes/class-journey-circle.php';

/**
 * Begins execution of the plugin.
 */
function run_journey_circle() {
    $plugin = new Journey_Circle();
    $plugin->run();
}
run_journey_circle();
