<?php
/**
 * Settings page template
 *
 * @package Journey_Circle
 */

// Security check
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// Handle form submission
if ( isset( $_POST['jc_settings_nonce'] ) && wp_verify_nonce( $_POST['jc_settings_nonce'], 'jc_save_settings' ) ) {
    // Save settings
    update_option( 'jc_enable_ai', isset( $_POST['jc_enable_ai'] ) ? 1 : 0 );
    update_option( 'jc_ai_provider', sanitize_text_field( $_POST['jc_ai_provider'] ) );
    update_option( 'jc_ai_api_key', sanitize_text_field( $_POST['jc_ai_api_key'] ) );
    update_option( 'jc_max_problems', absint( $_POST['jc_max_problems'] ) );
    update_option( 'jc_max_solutions', absint( $_POST['jc_max_solutions'] ) );
    
    echo '<div class="notice notice-success"><p>' . __( 'Settings saved successfully.', 'journey-circle' ) . '</p></div>';
}

// Get current settings
$enable_ai = get_option( 'jc_enable_ai', true );
$ai_provider = get_option( 'jc_ai_provider', 'gemini' );
$ai_api_key = get_option( 'jc_ai_api_key', '' );
$max_problems = get_option( 'jc_max_problems', 5 );
$max_solutions = get_option( 'jc_max_solutions', 5 );
?>

<div class="wrap">
    <h1><?php echo esc_html( get_admin_page_title() ); ?></h1>
    
    <form method="post" action="">
        <?php wp_nonce_field( 'jc_save_settings', 'jc_settings_nonce' ); ?>
        
        <table class="form-table">
            <tbody>
                <tr>
                    <th scope="row">
                        <label for="jc_enable_ai"><?php _e( 'Enable AI', 'journey-circle' ); ?></label>
                    </th>
                    <td>
                        <input type="checkbox" id="jc_enable_ai" name="jc_enable_ai" value="1" <?php checked( $enable_ai, 1 ); ?>>
                        <p class="description"><?php _e( 'Enable AI-powered content generation', 'journey-circle' ); ?></p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">
                        <label for="jc_ai_provider"><?php _e( 'AI Provider', 'journey-circle' ); ?></label>
                    </th>
                    <td>
                        <select id="jc_ai_provider" name="jc_ai_provider">
                            <option value="gemini" <?php selected( $ai_provider, 'gemini' ); ?>>Google Gemini</option>
                            <option value="openai" <?php selected( $ai_provider, 'openai' ); ?>>OpenAI (Coming Soon)</option>
                        </select>
                        <p class="description"><?php _e( 'Select AI provider for content generation', 'journey-circle' ); ?></p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">
                        <label for="jc_ai_api_key"><?php _e( 'AI API Key', 'journey-circle' ); ?></label>
                    </th>
                    <td>
                        <input type="text" id="jc_ai_api_key" name="jc_ai_api_key" value="<?php echo esc_attr( $ai_api_key ); ?>" class="regular-text">
                        <p class="description"><?php _e( 'Enter your API key for the selected AI provider', 'journey-circle' ); ?></p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">
                        <label for="jc_max_problems"><?php _e( 'Max Problems', 'journey-circle' ); ?></label>
                    </th>
                    <td>
                        <input type="number" id="jc_max_problems" name="jc_max_problems" value="<?php echo esc_attr( $max_problems ); ?>" min="1" max="10">
                        <p class="description"><?php _e( 'Maximum number of problems per journey circle', 'journey-circle' ); ?></p>
                    </td>
                </tr>
                
                <tr>
                    <th scope="row">
                        <label for="jc_max_solutions"><?php _e( 'Max Solutions', 'journey-circle' ); ?></label>
                    </th>
                    <td>
                        <input type="number" id="jc_max_solutions" name="jc_max_solutions" value="<?php echo esc_attr( $max_solutions ); ?>" min="1" max="10">
                        <p class="description"><?php _e( 'Maximum number of solutions per journey circle', 'journey-circle' ); ?></p>
                    </td>
                </tr>
            </tbody>
        </table>
        
        <?php submit_button(); ?>
    </form>
    
    <hr>
    
    <h2><?php _e( 'Database Information', 'journey-circle' ); ?></h2>
    <table class="widefat">
        <thead>
            <tr>
                <th><?php _e( 'Table Name', 'journey-circle' ); ?></th>
                <th><?php _e( 'Status', 'journey-circle' ); ?></th>
            </tr>
        </thead>
        <tbody>
            <?php
            global $wpdb;
            $tables = array(
                $wpdb->prefix . 'jc_metadata',
                $wpdb->prefix . 'jc_relationships',
                $wpdb->prefix . 'jc_brain_content_data',
                $wpdb->prefix . 'jc_ai_generated_content',
            );
            
            foreach ( $tables as $table ) {
                $exists = $wpdb->get_var( "SHOW TABLES LIKE '$table'" ) === $table;
                echo '<tr>';
                echo '<td>' . esc_html( $table ) . '</td>';
                echo '<td>' . ( $exists ? '<span style="color: green;">✓ Exists</span>' : '<span style="color: red;">✗ Missing</span>' ) . '</td>';
                echo '</tr>';
            }
            ?>
        </tbody>
    </table>
</div>
