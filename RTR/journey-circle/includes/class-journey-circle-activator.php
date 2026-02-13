<?php
/**
 * Fired during plugin activation.
 *
 * @package Journey_Circle
 */

class Journey_Circle_Activator {

    /**
     * Activate the plugin.
     *
     * Creates custom database tables and sets up initial configuration.
     *
     * @since 1.0.0
     */
    public static function activate() {
        // Create custom database tables
        self::create_tables();
        
        // Flush rewrite rules for custom post types
        flush_rewrite_rules();
        
        // Set plugin version
        add_option( 'journey_circle_version', JOURNEY_CIRCLE_VERSION );
        
        // Set default options
        self::set_default_options();
    }
    
    /**
     * Create custom database tables.
     *
     * @since 1.0.0
     */
    private static function create_tables() {
        global $wpdb;
        
        $charset_collate = $wpdb->get_charset_collate();
        $table_prefix = $wpdb->prefix . 'jc_';
        
        require_once( ABSPATH . 'wp-admin/includes/upgrade.php' );
        
        // Metadata table for storing additional data
        $sql_metadata = "CREATE TABLE IF NOT EXISTS {$table_prefix}metadata (
            id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
            post_id BIGINT(20) UNSIGNED NOT NULL,
            meta_key VARCHAR(255) NOT NULL,
            meta_value LONGTEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY post_id (post_id),
            KEY meta_key (meta_key)
        ) $charset_collate;";
        
        // Journey Circle relationships table
        $sql_relationships = "CREATE TABLE IF NOT EXISTS {$table_prefix}relationships (
            id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
            journey_circle_id BIGINT(20) UNSIGNED NOT NULL,
            problem_id BIGINT(20) UNSIGNED,
            solution_id BIGINT(20) UNSIGNED,
            offer_id BIGINT(20) UNSIGNED,
            relationship_type VARCHAR(50) NOT NULL,
            position INT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY journey_circle_id (journey_circle_id),
            KEY problem_id (problem_id),
            KEY solution_id (solution_id),
            KEY offer_id (offer_id),
            KEY relationship_type (relationship_type)
        ) $charset_collate;";
        
        // Brain content storage table
        $sql_brain_content = "CREATE TABLE IF NOT EXISTS {$table_prefix}brain_content_data (
            id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
            service_area_id BIGINT(20) UNSIGNED NOT NULL,
            content_type VARCHAR(50) NOT NULL,
            content_value LONGTEXT NOT NULL,
            file_path VARCHAR(500),
            processed TINYINT(1) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY service_area_id (service_area_id),
            KEY content_type (content_type)
        ) $charset_collate;";
        
        // AI generated content tracking
        $sql_ai_content = "CREATE TABLE IF NOT EXISTS {$table_prefix}ai_generated_content (
            id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
            journey_circle_id BIGINT(20) UNSIGNED NOT NULL,
            linked_to_type VARCHAR(50) NOT NULL,
            linked_to_id BIGINT(20) UNSIGNED NOT NULL,
            asset_type VARCHAR(50) NOT NULL,
            title VARCHAR(500),
            outline LONGTEXT,
            content LONGTEXT,
            published_url VARCHAR(2048),
            status VARCHAR(50) DEFAULT 'draft',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY journey_circle_id (journey_circle_id),
            KEY linked_to (linked_to_type, linked_to_id),
            KEY status (status)
        ) $charset_collate;";
        
        dbDelta( $sql_metadata );
        dbDelta( $sql_relationships );
        dbDelta( $sql_brain_content );
        dbDelta( $sql_ai_content );
    }
    
    /**
     * Set default plugin options.
     *
     * @since 1.0.0
     */
    private static function set_default_options() {
        $defaults = array(
            'jc_enable_ai' => true,
            'jc_ai_provider' => 'gemini',
            'jc_max_problems' => 5,
            'jc_max_solutions' => 5,
        );
        
        foreach ( $defaults as $key => $value ) {
            if ( false === get_option( $key ) ) {
                add_option( $key, $value );
            }
        }
    }
}
