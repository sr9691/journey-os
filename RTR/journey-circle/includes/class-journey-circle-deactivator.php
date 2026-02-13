<?php
/**
 * Fired during plugin deactivation.
 *
 * @package Journey_Circle
 */

class Journey_Circle_Deactivator {

    /**
     * Deactivate the plugin.
     *
     * @since 1.0.0
     */
    public static function deactivate() {
        // Flush rewrite rules
        flush_rewrite_rules();
        
        // Note: We don't delete data on deactivation, only on uninstall
    }
}
