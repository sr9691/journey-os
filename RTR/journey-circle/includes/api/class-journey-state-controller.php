<?php
/**
 * Journey State Persistence REST Controller
 *
 * Saves/loads full workflow state snapshots to jc_journey_state,
 * and syncs structured entities (offers, assets, published URLs)
 * to their dedicated relational tables.
 *
 * Endpoints:
 *   POST /directreach/v2/journey-state/save   — Save full state
 *   GET  /directreach/v2/journey-state/load    — Load state for client
 *   POST /directreach/v2/journey-state/sync    — Sync entities to relational tables
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class DR_Journey_State_Controller extends WP_REST_Controller {

    protected $namespace = 'directreach/v2';
    protected $rest_base = 'journey-state';

    public function register_routes() {
        // Save
        register_rest_route( $this->namespace, '/' . $this->rest_base . '/save', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'save_state' ),
            'permission_callback' => array( $this, 'check_permissions' ),
        ) );

        // Load
        register_rest_route( $this->namespace, '/' . $this->rest_base . '/load', array(
            'methods'             => WP_REST_Server::READABLE,
            'callback'            => array( $this, 'load_state' ),
            'permission_callback' => array( $this, 'check_permissions' ),
            'args' => array(
                'client_id' => array(
                    'required'          => true,
                    'type'              => 'integer',
                    'sanitize_callback' => 'absint',
                ),
            ),
        ) );

        // Sync entities
        register_rest_route( $this->namespace, '/' . $this->rest_base . '/sync', array(
            'methods'             => WP_REST_Server::CREATABLE,
            'callback'            => array( $this, 'sync_entities' ),
            'permission_callback' => array( $this, 'check_permissions' ),
        ) );
    }

    public function check_permissions( $request ) {
        if ( ! is_user_logged_in() ) {
            return new WP_Error( 'rest_forbidden', 'Authentication required.', array( 'status' => 401 ) );
        }
        if ( ! current_user_can( 'manage_campaigns' ) && ! current_user_can( 'manage_options' ) ) {
            return new WP_Error( 'rest_forbidden', 'Insufficient permissions.', array( 'status' => 403 ) );
        }
        return true;
    }

    /**
     * Save full workflow state snapshot.
     */
    public function save_state( $request ) {
        global $wpdb;

        $client_id         = absint( $request->get_param( 'client_id' ) );
        $service_area_id   = absint( $request->get_param( 'service_area_id' ) );
        $journey_circle_id = absint( $request->get_param( 'journey_circle_id' ) );
        $current_step      = absint( $request->get_param( 'current_step' ) ) ?: 1;
        $state_data        = $request->get_param( 'state_data' );
        $user_id           = get_current_user_id();

        if ( ! $client_id ) {
            return new WP_REST_Response( array( 'success' => false, 'error' => 'client_id is required.' ), 400 );
        }

        $state_json = is_string( $state_data ) ? $state_data : wp_json_encode( $state_data );
        $table      = $wpdb->prefix . 'jc_journey_state';
        $now        = current_time( 'mysql' );

        // Upsert by client_id + user_id
        $existing_id = $wpdb->get_var( $wpdb->prepare(
            "SELECT id FROM {$table} WHERE client_id = %d AND user_id = %d",
            $client_id, $user_id
        ) );

        if ( $existing_id ) {
            $result = $wpdb->update( $table,
                array(
                    'service_area_id'   => $service_area_id ?: null,
                    'journey_circle_id' => $journey_circle_id ?: null,
                    'state_data'        => $state_json,
                    'current_step'      => $current_step,
                    'updated_at'        => $now,
                ),
                array( 'id' => $existing_id ),
                array( '%d', '%d', '%s', '%d', '%s' ),
                array( '%d' )
            );
        } else {
            $result = $wpdb->insert( $table,
                array(
                    'client_id'         => $client_id,
                    'service_area_id'   => $service_area_id ?: null,
                    'journey_circle_id' => $journey_circle_id ?: null,
                    'state_data'        => $state_json,
                    'current_step'      => $current_step,
                    'user_id'           => $user_id,
                    'created_at'        => $now,
                    'updated_at'        => $now,
                ),
                array( '%d', '%d', '%d', '%s', '%d', '%d', '%s', '%s' )
            );
            $existing_id = $wpdb->insert_id;
        }

        if ( false === $result ) {
            error_log( 'Journey State save failed: ' . $wpdb->last_error );
            return new WP_REST_Response( array( 'success' => false, 'error' => $wpdb->last_error ), 500 );
        }

        return new WP_REST_Response( array( 'success' => true, 'state_id' => (int) $existing_id, 'saved_at' => $now ), 200 );
    }

    /**
     * Load most recent state for a client.
     */
    public function load_state( $request ) {
        global $wpdb;

        $client_id = absint( $request->get_param( 'client_id' ) );
        $user_id   = get_current_user_id();
        $table     = $wpdb->prefix . 'jc_journey_state';

        $row = $wpdb->get_row( $wpdb->prepare(
            "SELECT * FROM {$table} WHERE client_id = %d AND user_id = %d ORDER BY updated_at DESC LIMIT 1",
            $client_id, $user_id
        ) );

        if ( ! $row ) {
            return new WP_REST_Response( array( 'success' => true, 'state_data' => null ), 200 );
        }

        return new WP_REST_Response( array(
            'success'           => true,
            'state_id'          => (int) $row->id,
            'client_id'         => (int) $row->client_id,
            'service_area_id'   => (int) $row->service_area_id,
            'journey_circle_id' => (int) $row->journey_circle_id,
            'current_step'      => (int) $row->current_step,
            'state_data'        => json_decode( $row->state_data, true ),
            'updated_at'        => $row->updated_at,
        ), 200 );
    }

    /**
     * Sync structured entities from state to relational tables.
     *
     * Writes offers → jc_journey_offers,
     *        assets → jc_journey_assets,
     *        urls   → jc_journey_problems.asset_urls
     */
    public function sync_entities( $request ) {
        global $wpdb;

        $jc_id          = absint( $request->get_param( 'journey_circle_id' ) );
        $offers         = $request->get_param( 'offers' );
        $content_assets = $request->get_param( 'content_assets' );
        $published_urls = $request->get_param( 'published_urls' );

        if ( ! $jc_id ) {
            return new WP_REST_Response( array( 'success' => false, 'error' => 'journey_circle_id required.' ), 400 );
        }

        $synced = array( 'offers' => 0, 'assets' => 0, 'urls' => 0 );

        // --- Offers ---
        if ( ! empty( $offers ) && is_array( $offers ) ) {
            $t = $wpdb->prefix . 'jc_journey_offers';
            $wpdb->delete( $t, array( 'journey_circle_id' => $jc_id ), array( '%d' ) );

            foreach ( $offers as $problem_id => $list ) {
                if ( ! is_array( $list ) ) continue;
                foreach ( $list as $pos => $offer ) {
                    if ( empty( $offer['title'] ) || empty( $offer['url'] ) ) continue;
                    $wpdb->insert( $t, array(
                        'journey_circle_id' => $jc_id,
                        'problem_id'        => absint( $problem_id ),
                        'title'             => sanitize_text_field( $offer['title'] ),
                        'url'               => esc_url_raw( $offer['url'] ),
                        'position'          => (int) $pos,
                        'created_at'        => current_time( 'mysql' ),
                        'updated_at'        => current_time( 'mysql' ),
                    ), array( '%d', '%d', '%s', '%s', '%d', '%s', '%s' ) );
                    $synced['offers']++;
                }
            }
        }

        // --- Content Assets ---
        if ( ! empty( $content_assets ) && is_array( $content_assets ) ) {
            $t = $wpdb->prefix . 'jc_journey_assets';
            $wpdb->delete( $t, array( 'journey_circle_id' => $jc_id ), array( '%d' ) );

            foreach ( $content_assets as $pid => $asset_data ) {
                if ( ! is_array( $asset_data ) || empty( $asset_data['types'] ) ) continue;
                foreach ( $asset_data['types'] as $type_id => $td ) {
                    if ( ! is_array( $td ) ) continue;
                    $wpdb->insert( $t, array(
                        'journey_circle_id' => $jc_id,
                        'problem_id'        => absint( $pid ),
                        'linked_to_type'    => 'problem',
                        'linked_to_id'      => absint( $pid ),
                        'asset_type'        => sanitize_text_field( $type_id ),
                        'title'             => sanitize_text_field( $td['title'] ?? '' ),
                        'outline'           => wp_kses_post( $td['outline'] ?? '' ),
                        'content'           => wp_kses_post( $td['content'] ?? '' ),
                        'status'            => sanitize_text_field( $td['status'] ?? 'draft' ),
                        'created_at'        => current_time( 'mysql' ),
                        'updated_at'        => current_time( 'mysql' ),
                    ), array( '%d', '%d', '%s', '%d', '%s', '%s', '%s', '%s', '%s', '%s', '%s' ) );
                    $synced['assets']++;
                }
            }
        }

        // --- Published URLs ---
        if ( ! empty( $published_urls ) && is_array( $published_urls ) ) {
            $t = $wpdb->prefix . 'jc_journey_problems';
            foreach ( $published_urls as $pid => $url ) {
                if ( empty( $url ) ) continue;
                $wpdb->update( $t,
                    array( 'asset_urls' => wp_json_encode( array( esc_url_raw( $url ) ) ), 'updated_at' => current_time( 'mysql' ) ),
                    array( 'id' => absint( $pid ), 'journey_circle_id' => $jc_id ),
                    array( '%s', '%s' ), array( '%d', '%d' )
                );
                $synced['urls']++;
            }
        }

        return new WP_REST_Response( array( 'success' => true, 'synced' => $synced ), 200 );
    }
}