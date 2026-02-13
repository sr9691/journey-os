<?php
/**
 * Step 9 Template Snippet - Asset Creation Workflow
 * 
 * Add this to your journey-circle-creator.php template file
 * within the steps container.
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}
?>

<!-- Step 9: Asset Creation -->
<div id="step-9-container" 
     class="step-container" 
     data-step="9"
     style="display: none;">
    <!-- AssetCreator module will render content here -->
    <div class="step-loading">
        <div class="loading-spinner"></div>
        <p><?php esc_html_e('Loading asset creator...', 'directreach'); ?></p>
    </div>
</div>

<?php
/**
 * Script Localization
 * 
 * Add this to your enqueue scripts function to pass data to JavaScript:
 */

// In your enqueue function, add:
/*
wp_localize_script('dr-journey-circle', 'drJourneyCircle', array(
    'nonce'   => wp_create_nonce('wp_rest'),
    'apiBase' => rest_url('directreach/v2'),
    'userId'  => get_current_user_id(),
    'strings' => array(
        'generating'       => __('Generating...', 'directreach'),
        'generatingOutline' => __('Generating outline...', 'directreach'),
        'generatingContent' => __('Generating content...', 'directreach'),
        'revising'         => __('Revising...', 'directreach'),
        'saving'           => __('Saving...', 'directreach'),
        'error'            => __('An error occurred. Please try again.', 'directreach'),
        'networkError'     => __('Network error. Check your connection.', 'directreach'),
        'timeout'          => __('Request timed out. Please try again.', 'directreach'),
    ),
));
*/

/**
 * Step 9 Progress Indicator Item
 * 
 * Add this to your progress indicator list:
 */
?>
<!-- In your progress indicator -->
<li class="progress-step" data-step="9">
    <span class="step-number">9</span>
    <span class="step-label"><?php esc_html_e('Create Assets', 'directreach'); ?></span>
</li>

<?php
/**
 * Workflow Navigation Integration
 * 
 * In your step navigation, handle Step 9:
 */

// Example JavaScript for step navigation:
/*
// When entering Step 9
if (currentStep === 9) {
    // Initialize Asset Creator if not already
    if (!window.assetCreator) {
        window.assetCreator = new AssetCreator({
            containerSelector: '#step-9-container',
            apiNamespace: drJourneyCircle.apiBase,
            nonce: drJourneyCircle.nonce
        });
        window.assetCreator.init();
    } else {
        // Re-render to refresh data
        window.assetCreator.render();
    }
}

// Step 9 validation (can proceed when at least one asset is approved)
function validateStep9() {
    const assets = window.journeyCircleWorkflow?.getState()?.assets || [];
    const approvedAssets = assets.filter(a => 
        a.status === 'approved' || a.status === 'published'
    );
    return approvedAssets.length > 0;
}
*/

/**
 * Style Enqueue
 * 
 * Don't forget to enqueue the CSS:
 */

// In your admin enqueue function:
/*
function dr_enqueue_journey_circle_assets($hook) {
    // Only on journey circle page
    if ($hook !== 'directreach_page_dr-journey-circle') {
        return;
    }
    
    // Existing styles
    wp_enqueue_style(
        'dr-journey-circle',
        plugins_url('admin/css/journey-circle.css', DR_PLUGIN_FILE),
        array(),
        DR_VERSION
    );
    
    // Asset creator styles (Iteration 9)
    wp_enqueue_style(
        'dr-journey-circle-asset',
        plugins_url('admin/css/journey-circle-asset.css', DR_PLUGIN_FILE),
        array('dr-journey-circle'),
        DR_VERSION
    );
    
    // Asset creator script (Iteration 9)
    wp_enqueue_script(
        'dr-asset-creator',
        plugins_url('admin/js/modules/asset-creator.js', DR_PLUGIN_FILE),
        array('jquery'),
        DR_VERSION,
        true
    );
}
add_action('admin_enqueue_scripts', 'dr_enqueue_journey_circle_assets');
*/
?>
