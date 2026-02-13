<?php
/**
 * Dashboard page template
 *
 * @package Journey_Circle
 */

// Security check
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// Get statistics
$service_area_manager = new Service_Area_Manager();
$journey_manager = new Journey_Circle_Manager();

// Count totals
$total_service_areas = wp_count_posts( 'jc_service_area' )->publish;
$total_journey_circles = wp_count_posts( 'jc_journey_circle' )->publish;
$total_problems = wp_count_posts( 'jc_problem' )->publish;
$total_solutions = wp_count_posts( 'jc_solution' )->publish;
$total_offers = wp_count_posts( 'jc_offer' )->publish;
?>

<div class="wrap">
    <h1><?php echo esc_html( get_admin_page_title() ); ?></h1>
    
    <div class="jc-dashboard">
        <div class="jc-stats-grid">
            <div class="jc-stat-card">
                <h3><?php _e( 'Service Areas', 'journey-circle' ); ?></h3>
                <div class="jc-stat-number"><?php echo esc_html( $total_service_areas ); ?></div>
                <a href="<?php echo admin_url( 'edit.php?post_type=jc_service_area' ); ?>" class="button">
                    <?php _e( 'View All', 'journey-circle' ); ?>
                </a>
            </div>
            
            <div class="jc-stat-card">
                <h3><?php _e( 'Journey Circles', 'journey-circle' ); ?></h3>
                <div class="jc-stat-number"><?php echo esc_html( $total_journey_circles ); ?></div>
                <a href="<?php echo admin_url( 'edit.php?post_type=jc_journey_circle' ); ?>" class="button">
                    <?php _e( 'View All', 'journey-circle' ); ?>
                </a>
            </div>
            
            <div class="jc-stat-card">
                <h3><?php _e( 'Problems', 'journey-circle' ); ?></h3>
                <div class="jc-stat-number"><?php echo esc_html( $total_problems ); ?></div>
                <a href="<?php echo admin_url( 'edit.php?post_type=jc_problem' ); ?>" class="button">
                    <?php _e( 'View All', 'journey-circle' ); ?>
                </a>
            </div>
            
            <div class="jc-stat-card">
                <h3><?php _e( 'Solutions', 'journey-circle' ); ?></h3>
                <div class="jc-stat-number"><?php echo esc_html( $total_solutions ); ?></div>
                <a href="<?php echo admin_url( 'edit.php?post_type=jc_solution' ); ?>" class="button">
                    <?php _e( 'View All', 'journey-circle' ); ?>
                </a>
            </div>
            
            <div class="jc-stat-card">
                <h3><?php _e( 'Offers', 'journey-circle' ); ?></h3>
                <div class="jc-stat-number"><?php echo esc_html( $total_offers ); ?></div>
                <a href="<?php echo admin_url( 'edit.php?post_type=jc_offer' ); ?>" class="button">
                    <?php _e( 'View All', 'journey-circle' ); ?>
                </a>
            </div>
        </div>
        
        <div class="jc-quick-actions">
            <h2><?php _e( 'Quick Actions', 'journey-circle' ); ?></h2>
            <div class="jc-actions-grid">
                <a href="<?php echo admin_url( 'post-new.php?post_type=jc_service_area' ); ?>" class="button button-primary button-large">
                    <span class="dashicons dashicons-plus"></span>
                    <?php _e( 'New Service Area', 'journey-circle' ); ?>
                </a>
                <a href="<?php echo admin_url( 'post-new.php?post_type=jc_journey_circle' ); ?>" class="button button-primary button-large">
                    <span class="dashicons dashicons-networking"></span>
                    <?php _e( 'New Journey Circle', 'journey-circle' ); ?>
                </a>
                <a href="<?php echo admin_url( 'admin.php?page=journey-circle-settings' ); ?>" class="button button-large">
                    <span class="dashicons dashicons-admin-settings"></span>
                    <?php _e( 'Settings', 'journey-circle' ); ?>
                </a>
            </div>
        </div>
        
        <div class="jc-getting-started">
            <h2><?php _e( 'Getting Started', 'journey-circle' ); ?></h2>
            <ol>
                <li><?php _e( 'Create a Service Area for your client or product', 'journey-circle' ); ?></li>
                <li><?php _e( 'Build a Journey Circle with 5 problems, 5 solutions, and offers', 'journey-circle' ); ?></li>
                <li><?php _e( 'Upload brain content (URLs, files, text) for AI assistance', 'journey-circle' ); ?></li>
                <li><?php _e( 'Generate content assets using AI', 'journey-circle' ); ?></li>
                <li><?php _e( 'Export and link your published content', 'journey-circle' ); ?></li>
            </ol>
        </div>
    </div>
</div>

<style>
.jc-dashboard {
    margin-top: 20px;
}

.jc-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.jc-stat-card {
    background: #fff;
    border: 1px solid #c3c4c7;
    border-radius: 4px;
    padding: 20px;
    text-align: center;
}

.jc-stat-card h3 {
    margin: 0 0 10px 0;
    font-size: 14px;
    color: #50575e;
}

.jc-stat-number {
    font-size: 48px;
    font-weight: bold;
    color: #2271b1;
    margin: 10px 0;
}

.jc-quick-actions,
.jc-getting-started {
    background: #fff;
    border: 1px solid #c3c4c7;
    border-radius: 4px;
    padding: 20px;
    margin-bottom: 20px;
}

.jc-actions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-top: 15px;
}

.jc-getting-started ol {
    margin: 15px 0 0 20px;
}

.jc-getting-started li {
    margin-bottom: 10px;
}
</style>
