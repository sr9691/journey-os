<?php
/**
 * Slide Image Generator REST Controller
 *
 * Generates AI images for presentation slides using Gemini image models
 * (Nano Banana). Accepts slide data (title, key points, visual element
 * description), builds a detailed image prompt, calls the Gemini image
 * API, and returns the base64-encoded PNG.
 *
 * Models:
 *   - standard: gemini-2.5-flash-image (fast, good quality)
 *   - pro:      gemini-3-pro-image-preview (4K, best text rendering)
 *
 * Part of Iteration 3: Fix Nano Banana integration
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.1.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class DR_AI_Slide_Image_Generator {

    /**
     * REST API namespace.
     *
     * @var string
     */
    private $namespace = 'directreach/v2';

    /**
     * REST API base.
     *
     * @var string
     */
    private $rest_base = 'ai';

    /**
     * Gemini API base URL.
     *
     * @var string
     */
    const API_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/';

    /**
     * Available image models.
     *
     * @var array
     */
    const IMAGE_MODELS = array(
        'standard' => 'gemini-2.5-flash-image',
        'pro'      => 'gemini-3-pro-image-preview',
    );

    /**
     * API request timeout in seconds.
     * Image generation takes longer than text.
     *
     * @var int
     */
    const IMAGE_TIMEOUT = 90;

    /**
     * Gemini API key.
     *
     * @var string|null
     */
    private $api_key = null;

    /**
     * Constructor. Loads API key.
     */
    public function __construct() {
        $this->load_api_key();
    }

    /**
     * Register REST routes.
     */
    public function register_routes() {
        register_rest_route( $this->namespace, '/' . $this->rest_base . '/generate-slide-image', array(
            array(
                'methods'             => 'POST',
                'callback'            => array( $this, 'generate_slide_image' ),
                'permission_callback' => array( $this, 'check_permission' ),
                'args'                => $this->get_endpoint_args(),
            ),
        ) );
    }

    /**
     * Permission check.
     *
     * @param WP_REST_Request $request Request object.
     * @return bool|WP_Error
     */
    public function check_permission( $request ) {
        if ( ! is_user_logged_in() ) {
            return new WP_Error(
                'rest_not_logged_in',
                __( 'You must be logged in to generate images.', 'directreach' ),
                array( 'status' => 401 )
            );
        }

        if ( current_user_can( 'manage_options' ) || current_user_can( 'manage_campaigns' ) ) {
            return true;
        }

        return new WP_Error(
            'rest_forbidden',
            __( 'You do not have permission to generate images.', 'directreach' ),
            array( 'status' => 403 )
        );
    }

    /**
     * Handle the POST request to generate a slide image.
     *
     * @param WP_REST_Request $request Request object.
     * @return WP_REST_Response
     */
    public function generate_slide_image( $request ) {
        if ( empty( $this->api_key ) ) {
            return new WP_REST_Response( array(
                'success' => false,
                'message' => 'Gemini API key is not configured. Set it in DirectReach AI Settings.',
            ), 503 );
        }

        $slide_title    = sanitize_text_field( $request->get_param( 'slide_title' ) ?? '' );
        $section        = sanitize_text_field( $request->get_param( 'section' ) ?? '' );
        $key_points     = $request->get_param( 'key_points' ) ?? array();
        $data_points    = $request->get_param( 'data_points' ) ?? array();
        $visual_element = $request->get_param( 'visual_element' ) ?? array();
        $quality        = sanitize_text_field( $request->get_param( 'quality' ) ?? 'standard' );

        if ( empty( $slide_title ) && empty( $visual_element ) ) {
            return new WP_REST_Response( array(
                'success' => false,
                'message' => 'Slide title or visual element data is required.',
            ), 400 );
        }

        // Build the image prompt.
        $prompt = $this->build_slide_image_prompt( $slide_title, $section, $key_points, $data_points, $visual_element );

        // Choose model based on quality.
        $model = isset( self::IMAGE_MODELS[ $quality ] ) ? self::IMAGE_MODELS[ $quality ] : self::IMAGE_MODELS['standard'];

        // Call Gemini image API.
        $result = $this->call_gemini_image_api( $prompt, $model );

        if ( is_wp_error( $result ) ) {
            return new WP_REST_Response( array(
                'success' => false,
                'message' => $result->get_error_message(),
            ), 503 );
        }

        return new WP_REST_Response( array(
            'success'      => true,
            'image_base64' => $result['image_base64'],
            'mime_type'    => $result['mime_type'],
            'model_used'   => $model,
        ), 200 );
    }

    // =========================================================================
    // PROMPT BUILDING
    // =========================================================================

    /**
     * Build a detailed image prompt from slide data.
     *
     * @param string $title          Slide title.
     * @param string $section        Slide section.
     * @param array  $key_points     Key points array.
     * @param array  $data_points    Data points array.
     * @param array  $visual_element Visual element specification.
     * @return string Image generation prompt.
     */
    private function build_slide_image_prompt( $title, $section, $key_points, $data_points, $visual_element ) {
        $ve_type = isset( $visual_element['type'] ) ? $visual_element['type'] : '';
        $ve_data = isset( $visual_element['data'] ) ? $visual_element['data'] : array();
        $is_infographic = ( $ve_type === 'infographic_full' );

        if ( $is_infographic ) {
            $prompt  = "Create a professional infographic image in tall portrait format (approximately 2:3 ratio, like 1080x1620).\n";
            $prompt .= "Use a modern, clean design with a dark navy gradient header, alternating white/light-gray content sections, and a dark footer.\n\n";
        } else {
            $prompt  = "Create a professional presentation slide image in 16:9 landscape format.\n";
            $prompt .= "Dark navy background (#0F2B46). Clean, modern business design.\n\n";
        }

        // Section context for color theming.
        $section_colors = array(
            'Problem Definition'    => 'red (#EF5350) accents',
            'Problem Amplification' => 'red (#EF5350) accents',
            'Solution Overview'     => 'green (#66BB6A) accents',
            'Solution Details'      => 'green (#66BB6A) accents',
            'Benefits Summary'      => 'blue (#42A5F5) accents',
            'Credibility'           => 'purple (#AB47BC) accents',
            'Call to Action'        => 'orange (#FF7043) accents',
        );
        $color_hint = isset( $section_colors[ $section ] ) ? $section_colors[ $section ] : 'blue (#42A5F5) accents';

        $prompt .= "Color theme: {$color_hint}\n";
        if ( ! empty( $title ) ) {
            $prompt .= ( $is_infographic ? "Infographic title: " : "Slide title: " ) . "\"{$title}\"\n";
        }
        if ( ! empty( $section ) && ! $is_infographic ) {
            $prompt .= "Section category: {$section}\n";
        }

        if ( $is_infographic ) {
            // Infographic: the visual element description contains the full layout
            $prompt .= "\nINFOGRAPHIC CONTENT:\n";
            $prompt .= $this->describe_visual_element( $ve_type, $ve_data );
        } else {
            $prompt .= "\nLayout: Split layout — left side has the slide title and ";
            $prompt .= count( $key_points ) . " bullet points in white text, ";
            $prompt .= "right side displays the data visualization.\n\n";

            // Build visual element description.
            $prompt .= "RIGHT SIDE VISUALIZATION:\n";
            $prompt .= $this->describe_visual_element( $ve_type, $ve_data );

            if ( ! empty( $key_points ) ) {
                $prompt .= "\nLEFT SIDE BULLET POINTS (render as white text on dark background):\n";
                foreach ( $key_points as $point ) {
                    $prompt .= '- ' . sanitize_text_field( $point ) . "\n";
                }
            }

            if ( ! empty( $data_points ) ) {
                $prompt .= "\nBottom data pills: " . implode( ', ', array_map( 'sanitize_text_field', $data_points ) ) . "\n";
            }
        }

        $prompt .= "\nStyle requirements:\n";
        $prompt .= "- Professional corporate quality\n";
        $prompt .= "- Clean sans-serif typography\n";
        if ( $is_infographic ) {
            $prompt .= "- Tall portrait format (approximately 1080x1620 pixels)\n";
            $prompt .= "- Multiple clearly separated content sections\n";
            $prompt .= "- Data visualizations embedded inline within sections\n";
        } else {
            $prompt .= "- White text on dark navy background\n";
            $prompt .= "- 16:9 aspect ratio (1920x1080 equivalent)\n";
            $prompt .= "- Data visualization should be crisp and readable\n";
        }
        $prompt .= "- No watermarks, logos, or decorative borders\n";
        $prompt .= "- Render ALL text cleanly and legibly\n";

        return $prompt;
    }

    /**
     * Describe a visual element type in natural language for the image prompt.
     *
     * @param string $type Visual element type.
     * @param array  $data Visual element data.
     * @return string Description for the prompt.
     */
    private function describe_visual_element( $type, $data ) {
        $desc = '';

        switch ( $type ) {
            case 'bar_chart':
                $labels = isset( $data['labels'] ) ? $data['labels'] : array();
                $values = isset( $data['values'] ) ? $data['values'] : array();
                $suffix = isset( $data['value_suffix'] ) ? $data['value_suffix'] : '';
                $title  = isset( $data['title'] ) ? $data['title'] : 'Chart';

                $desc .= "Horizontal bar chart titled \"{$title}\".\n";
                $desc .= "Bars with rounded ends, each a different color from the accent palette.\n";
                $pairs = array();
                for ( $i = 0; $i < count( $labels ) && $i < count( $values ); $i++ ) {
                    $pairs[] = $labels[ $i ] . ': ' . $values[ $i ] . $suffix;
                }
                $desc .= "Data: " . implode( ', ', $pairs ) . "\n";
                $desc .= "Show value labels at the end of each bar.\n";
                break;

            case 'donut_chart':
                $segments    = isset( $data['segments'] ) ? $data['segments'] : array();
                $center_val  = isset( $data['center_value'] ) ? $data['center_value'] : '';
                $center_lbl  = isset( $data['center_label'] ) ? $data['center_label'] : '';

                $desc .= "Donut chart (ring chart with hollow center).\n";
                $seg_items = array();
                foreach ( $segments as $seg ) {
                    $seg_items[] = ( $seg['label'] ?? 'Item' ) . ': ' . ( $seg['value'] ?? 0 );
                }
                $desc .= "Segments: " . implode( ', ', $seg_items ) . "\n";
                if ( $center_val ) {
                    $desc .= "Center displays \"{$center_val}\"";
                    if ( $center_lbl ) {
                        $desc .= " with label \"{$center_lbl}\"";
                    }
                    $desc .= ".\n";
                }
                $desc .= "Each segment a different vibrant color. Labels near segments.\n";
                break;

            case 'stat_cards':
                $stats = isset( $data['stats'] ) ? $data['stats'] : array();
                $desc .= "Row of " . count( $stats ) . " stat highlight cards.\n";
                $desc .= "Each card has a large bold number and a small label below it.\n";
                foreach ( $stats as $stat ) {
                    $desc .= "  Card: \"" . ( $stat['value'] ?? '' ) . "\" — " . ( $stat['label'] ?? '' ) . "\n";
                }
                $desc .= "Cards have semi-transparent backgrounds with rounded corners.\n";
                break;

            case 'comparison':
                $before = isset( $data['before'] ) ? $data['before'] : array();
                $after  = isset( $data['after'] ) ? $data['after'] : array();
                $desc  .= "Before/After comparison panel.\n";
                $desc  .= "Left panel (red tint): \"" . ( $before['title'] ?? 'Before' ) . "\"\n";
                if ( ! empty( $before['points'] ) ) {
                    $desc .= "  Points with X marks: " . implode( ', ', $before['points'] ) . "\n";
                }
                $desc .= "Right panel (green tint): \"" . ( $after['title'] ?? 'After' ) . "\"\n";
                if ( ! empty( $after['points'] ) ) {
                    $desc .= "  Points with checkmarks: " . implode( ', ', $after['points'] ) . "\n";
                }
                break;

            case 'timeline':
                $steps = isset( $data['steps'] ) ? $data['steps'] : array();
                $desc .= "Vertical timeline with " . count( $steps ) . " phases.\n";
                $desc .= "Connected by a vertical line with colored dots at each phase.\n";
                foreach ( $steps as $step ) {
                    $phase = $step['phase'] ?? '';
                    $stitle = $step['title'] ?? '';
                    $sdesc = $step['description'] ?? '';
                    $desc .= "  {$phase}: {$stitle}" . ( $sdesc ? " — {$sdesc}" : '' ) . "\n";
                }
                break;

            case 'progress_bars':
                $bars   = isset( $data['bars'] ) ? $data['bars'] : array();
                $suffix = isset( $data['value_suffix'] ) ? $data['value_suffix'] : '%';
                $desc  .= "Stack of " . count( $bars ) . " horizontal progress bars.\n";
                $desc  .= "Each bar has a label on the left and percentage on the right.\n";
                foreach ( $bars as $bar ) {
                    $desc .= "  " . ( $bar['label'] ?? 'Item' ) . ': ' . ( $bar['value'] ?? 0 ) . $suffix . "\n";
                }
                $desc .= "Bars have rounded ends with gradient fills, on a slightly lighter background.\n";
                break;

            case 'infographic_full':
                // Full infographic as a single image
                $ig_title    = isset( $data['title'] ) ? $data['title'] : '';
                $ig_subtitle = isset( $data['subtitle'] ) ? $data['subtitle'] : '';
                $ig_sections = isset( $data['sections'] ) ? $data['sections'] : array();
                $ig_footer   = isset( $data['footer'] ) ? $data['footer'] : '';
                $ig_cta      = isset( $data['call_to_action'] ) ? $data['call_to_action'] : '';

                $desc .= "A complete infographic in tall portrait format (suitable for web/print).\n";
                $desc .= "Professional design with dark navy header, white/light gray sections, dark footer.\n\n";
                if ( $ig_title ) $desc .= "TITLE (large white text on gradient navy header): \"{$ig_title}\"\n";
                if ( $ig_subtitle ) $desc .= "SUBTITLE: \"{$ig_subtitle}\"\n\n";

                foreach ( $ig_sections as $si => $sec ) {
                    $sec_heading = isset( $sec['heading'] ) ? $sec['heading'] : '';
                    $sec_desc    = isset( $sec['description'] ) ? $sec['description'] : '';
                    $sec_dps     = isset( $sec['data_points'] ) ? $sec['data_points'] : array();
                    $sec_ve      = isset( $sec['visual_element'] ) ? $sec['visual_element'] : null;

                    $desc .= "SECTION " . ( $si + 1 ) . ":\n";
                    if ( $sec_heading ) $desc .= "  Heading: \"{$sec_heading}\"\n";
                    if ( $sec_desc ) $desc .= "  Description: \"{$sec_desc}\"\n";
                    if ( ! empty( $sec_dps ) ) {
                        $dp_items = array();
                        foreach ( $sec_dps as $dp ) {
                            $dp_items[] = ( $dp['label'] ?? '' ) . ': ' . ( $dp['value'] ?? '' );
                        }
                        $desc .= "  Data points: " . implode( ', ', $dp_items ) . "\n";
                    }
                    if ( $sec_ve && isset( $sec_ve['type'] ) ) {
                        $desc .= "  Chart: " . $this->describe_visual_element( $sec_ve['type'], $sec_ve['data'] ?? array() );
                    }
                    $desc .= "\n";
                }

                if ( $ig_cta ) $desc .= "FOOTER CTA: \"{$ig_cta}\"\n";
                if ( $ig_footer ) $desc .= "FOOTER SOURCE: \"{$ig_footer}\"\n";
                $desc .= "\nStyle: Alternating white/light-gray section backgrounds. ";
                $desc .= "Bold section headings. Colorful charts and data visualizations. ";
                $desc .= "Clean sans-serif typography throughout.\n";
                break;

            default:
                $desc .= "A clean, abstract data visualization that conveys business insights.\n";
                $desc .= "Use geometric shapes, clean lines, and the accent color palette.\n";
        }

        return $desc;
    }

    // =========================================================================
    // GEMINI IMAGE API CALL
    // =========================================================================

    /**
     * Call Gemini image generation API.
     *
     * Uses the generateContent endpoint with responseModalities = ["TEXT", "IMAGE"]
     * to get inline image data back.
     *
     * @param string $prompt Image description prompt.
     * @param string $model  Model identifier.
     * @return array|WP_Error Array with image_base64 and mime_type, or WP_Error.
     */
    private function call_gemini_image_api( $prompt, $model ) {
        $url = self::API_BASE_URL . $model . ':generateContent?key=' . $this->api_key;

        $body = array(
            'contents' => array(
                array(
                    'parts' => array(
                        array(
                            'text' => $prompt,
                        ),
                    ),
                ),
            ),
            'generationConfig' => array(
                'responseModalities' => array( 'TEXT', 'IMAGE' ),
                'temperature'        => 0.8,
            ),
            'safetySettings' => array(
                array(
                    'category'  => 'HARM_CATEGORY_HARASSMENT',
                    'threshold' => 'BLOCK_NONE',
                ),
                array(
                    'category'  => 'HARM_CATEGORY_HATE_SPEECH',
                    'threshold' => 'BLOCK_NONE',
                ),
                array(
                    'category'  => 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
                    'threshold' => 'BLOCK_NONE',
                ),
                array(
                    'category'  => 'HARM_CATEGORY_DANGEROUS_CONTENT',
                    'threshold' => 'BLOCK_NONE',
                ),
            ),
        );

        $response = wp_remote_post( $url, array(
            'headers' => array(
                'Content-Type' => 'application/json',
            ),
            'body'    => wp_json_encode( $body ),
            'timeout' => self::IMAGE_TIMEOUT,
        ) );

        if ( is_wp_error( $response ) ) {
            return new WP_Error(
                'api_connection_error',
                'Failed to connect to Gemini Image API: ' . $response->get_error_message()
            );
        }

        $code = wp_remote_retrieve_response_code( $response );
        $body_str = wp_remote_retrieve_body( $response );
        $data = json_decode( $body_str, true );

        if ( $code !== 200 ) {
            $error_msg = 'Gemini Image API error (HTTP ' . $code . ')';
            if ( isset( $data['error']['message'] ) ) {
                $error_msg .= ': ' . $data['error']['message'];
            }
            return new WP_Error( 'api_error', $error_msg );
        }

        if ( ! isset( $data['candidates'][0]['content']['parts'] ) ) {
            return new WP_Error( 'no_content', 'Gemini returned no content parts.' );
        }

        $parts = $data['candidates'][0]['content']['parts'];

        // Look for inline image data.
        foreach ( $parts as $part ) {
            if ( isset( $part['inlineData'] ) && ! empty( $part['inlineData']['data'] ) ) {
                return array(
                    'image_base64' => $part['inlineData']['data'],
                    'mime_type'    => isset( $part['inlineData']['mimeType'] ) ? $part['inlineData']['mimeType'] : 'image/png',
                );
            }
        }

        // No image found — extract text response for diagnostics.
        $text_content = '';
        foreach ( $parts as $part ) {
            if ( isset( $part['text'] ) ) {
                $text_content .= $part['text'] . ' ';
            }
        }

        return new WP_Error(
            'no_image',
            'Gemini returned text but no image. Response: ' . substr( trim( $text_content ), 0, 200 )
        );
    }

    // =========================================================================
    // API KEY LOADING
    // =========================================================================

    /**
     * Load the Gemini API key from WordPress options.
     */
    private function load_api_key() {
        // Ensure the Campaign Builder's AI Settings Manager class is available.
        if ( ! class_exists( 'CPD_AI_Settings_Manager' ) ) {
            if ( defined( 'DR_CB_PLUGIN_DIR' ) ) {
                $cb_settings_file = DR_CB_PLUGIN_DIR . 'includes/class-ai-settings-manager.php';
            } else {
                $cb_settings_file = dirname( __FILE__, 4 ) . '/campaign-builder/includes/class-ai-settings-manager.php';
            }
            if ( file_exists( $cb_settings_file ) ) {
                require_once $cb_settings_file;
            }
        }

        // Primary: Use the Campaign Builder's AI Settings Manager (handles encrypted keys).
        if ( class_exists( 'CPD_AI_Settings_Manager' ) ) {
            $settings_manager = new CPD_AI_Settings_Manager();
            $key = $settings_manager->get_api_key();
            if ( ! empty( $key ) ) {
                $this->api_key = $key;
                return;
            }
        }

        // Fallback: standalone unencrypted option.
        $standalone_key = get_option( 'dr_gemini_api_key', '' );
        if ( ! empty( $standalone_key ) ) {
            $this->api_key = $standalone_key;
            return;
        }

        // Journey Circle specific settings.
        $jc_settings = get_option( 'jc_settings', array() );
        if ( isset( $jc_settings['gemini_api_key'] ) && ! empty( $jc_settings['gemini_api_key'] ) ) {
            $this->api_key = $jc_settings['gemini_api_key'];
        }
    }

    // =========================================================================
    // ENDPOINT ARGS
    // =========================================================================

    /**
     * Get argument definitions for the generate-slide-image endpoint.
     *
     * @return array
     */
    private function get_endpoint_args() {
        return array(
            'slide_title' => array(
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_text_field',
                'default'           => '',
            ),
            'section' => array(
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_text_field',
                'default'           => '',
            ),
            'key_points' => array(
                'type'    => 'array',
                'default' => array(),
            ),
            'data_points' => array(
                'type'    => 'array',
                'default' => array(),
            ),
            'visual_element' => array(
                'type'    => 'object',
                'default' => array(),
            ),
            'quality' => array(
                'type'              => 'string',
                'sanitize_callback' => 'sanitize_text_field',
                'default'           => 'standard',
                'enum'              => array( 'standard', 'pro' ),
            ),
        );
    }
}