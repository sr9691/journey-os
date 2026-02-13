<?php
/**
 * AI Content Generator
 *
 * Integrates with Google Gemini API to generate problem titles,
 * solution titles, content outlines, and full content for Journey Circles.
 *
 * Part of Iteration 8: AI Title Recommendations
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Class DR_AI_Content_Generator
 *
 * Handles all AI-powered content generation for the Journey Circle workflow.
 * Uses Google Gemini API with structured prompt templates and response caching.
 *
 * Features:
 * - Problem title generation (8-10 titles)
 * - Solution title generation (3 per problem)
 * - Transient-based caching (15 minutes)
 * - Graceful error handling with fallback
 * - Structured JSON output parsing
 */
class DR_AI_Content_Generator {

    /**
     * Gemini API base URL.
     *
     * @var string
     */
    const API_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/';

    /**
     * Default Gemini model to use.
     *
     * @var string
     */
    const DEFAULT_MODEL = 'gemini-2.0-flash';

    /**
     * Cache duration in seconds (15 minutes).
     *
     * @var int
     */
    const CACHE_DURATION = 900;

    /**
     * API request timeout in seconds.
     *
     * @var int
     */
    const API_TIMEOUT = 30;

    /**
     * Maximum number of problem titles to request.
     *
     * @var int
     */
    const MAX_PROBLEM_TITLES = 10;

    /**
     * Minimum number of problem titles to request.
     *
     * @var int
     */
    const MIN_PROBLEM_TITLES = 8;

    /**
     * Number of solution titles per problem.
     *
     * @var int
     */
    const SOLUTION_TITLES_COUNT = 3;

    /**
     * Gemini API key.
     *
     * @var string|null
     */
    private $api_key = null;

    /**
     * Gemini model identifier.
     *
     * @var string
     */
    private $model;

    /**
     * Last API error message.
     *
     * @var string
     */
    private $last_error = '';

    /**
     * Constructor.
     *
     * Loads API key from WordPress options and sets the model.
     *
     * @param string|null $model Optional model override.
     */
    public function __construct( $model = null ) {
        $this->load_api_key();
        $this->model = $model ?? self::DEFAULT_MODEL;
    }

    // =========================================================================
    // PUBLIC API
    // =========================================================================

    /**
     * Generate problem title recommendations.
     *
     * Given brain content, industries, and service area context,
     * generates 8-10 problem titles suitable for content marketing.
     *
     * @since 2.0.0
     *
     * @param array $args {
     *     Arguments for problem title generation.
     *
     *     @type int    $service_area_id  Service area ID.
     *     @type string $service_area_name Service area name.
     *     @type array  $industries       Array of industry names/IDs.
     *     @type array  $brain_content    Array of brain content items.
     *     @type bool   $force_refresh    Skip cache if true.
     * }
     * @return array|WP_Error Array of title strings on success, WP_Error on failure.
     */
    public function generate_problem_titles( $args ) {
        $defaults = array(
            'service_area_id'   => 0,
            'service_area_name' => '',
            'industries'        => array(),
            'brain_content'     => array(),
            'force_refresh'     => false,
        );
        $args = wp_parse_args( $args, $defaults );

        // Validate inputs.
        if ( empty( $args['service_area_name'] ) && empty( $args['service_area_id'] ) ) {
            return new WP_Error(
                'missing_service_area',
                __( 'Service area is required to generate problem titles.', 'directreach' )
            );
        }

        // Resolve service area name from ID if needed.
        if ( empty( $args['service_area_name'] ) && ! empty( $args['service_area_id'] ) ) {
            $args['service_area_name'] = $this->get_service_area_name( $args['service_area_id'] );
        }

        // Check cache unless force refresh.
        if ( ! $args['force_refresh'] ) {
            $cache_key = $this->build_cache_key( 'problem_titles', $args );
            $cached    = get_transient( $cache_key );
            if ( false !== $cached ) {
                return $cached;
            }
        }

        // Build prompt.
        $prompt = $this->build_problem_titles_prompt( $args );

        // Call Gemini API.
        $response = $this->call_gemini_api( $prompt );

        if ( is_wp_error( $response ) ) {
            return $response;
        }

        // Parse response into title array.
        $titles = $this->parse_titles_response( $response, 'problems' );

        if ( is_wp_error( $titles ) ) {
            return $titles;
        }

        // Validate we got enough titles.
        if ( count( $titles ) < self::MIN_PROBLEM_TITLES ) {
            // Pad with generic titles if AI returned too few.
            $titles = $this->pad_problem_titles( $titles, $args['service_area_name'] );
        }

        // Trim to max.
        $titles = array_slice( $titles, 0, self::MAX_PROBLEM_TITLES );

        // Cache the result.
        $cache_key = $cache_key ?? $this->build_cache_key( 'problem_titles', $args );
        set_transient( $cache_key, $titles, self::CACHE_DURATION );

        return $titles;
    }

    /**
     * Generate solution title recommendations for a specific problem.
     *
     * Given a problem title and brain content, generates 3 solution titles.
     *
     * @since 2.0.0
     *
     * @param array $args {
     *     Arguments for solution title generation.
     *
     *     @type int    $problem_id       Problem ID.
     *     @type string $problem_title    Problem title text.
     *     @type string $service_area_name Service area name for context.
     *     @type array  $brain_content    Array of brain content items.
     *     @type array  $industries       Industry names for context.
     *     @type bool   $force_refresh    Skip cache if true.
     * }
     * @return array|WP_Error Array of title strings on success, WP_Error on failure.
     */
    public function generate_solution_titles( $args ) {
        $defaults = array(
            'problem_id'        => 0,
            'problem_title'     => '',
            'service_area_name' => '',
            'brain_content'     => array(),
            'industries'        => array(),
            'force_refresh'     => false,
        );
        $args = wp_parse_args( $args, $defaults );

        // Validate inputs.
        if ( empty( $args['problem_title'] ) ) {
            return new WP_Error(
                'missing_problem_title',
                __( 'Problem title is required to generate solution titles.', 'directreach' )
            );
        }

        // Check cache unless force refresh.
        if ( ! $args['force_refresh'] ) {
            $cache_key = $this->build_cache_key( 'solution_titles', $args );
            $cached    = get_transient( $cache_key );
            if ( false !== $cached ) {
                return $cached;
            }
        }

        // Build prompt.
        $prompt = $this->build_solution_titles_prompt( $args );

        // Call Gemini API.
        $response = $this->call_gemini_api( $prompt );

        if ( is_wp_error( $response ) ) {
            return $response;
        }

        // Parse response.
        $titles = $this->parse_titles_response( $response, 'solutions' );

        if ( is_wp_error( $titles ) ) {
            return $titles;
        }

        // Ensure exactly 3 titles.
        $titles = array_slice( $titles, 0, self::SOLUTION_TITLES_COUNT );

        if ( count( $titles ) < self::SOLUTION_TITLES_COUNT ) {
            $titles = $this->pad_solution_titles( $titles, $args['problem_title'] );
        }

        // Cache the result.
        $cache_key = $cache_key ?? $this->build_cache_key( 'solution_titles', $args );
        set_transient( $cache_key, $titles, self::CACHE_DURATION );

        return $titles;
    }

    /**
     * Check if the Gemini API key is configured.
     *
     * @since 2.0.0
     *
     * @return bool True if API key exists.
     */
    public function is_configured() {
        return ! empty( $this->api_key );
    }

    /**
     * Get the last error message.
     *
     * @since 2.0.0
     *
     * @return string Last error message.
     */
    public function get_last_error() {
        return $this->last_error;
    }

    /**
     * Clear cached titles for a specific context.
     *
     * @since 2.0.0
     *
     * @param string $type 'problem_titles' or 'solution_titles'.
     * @param array  $args Arguments used for generation (for cache key).
     * @return bool True if cache was deleted.
     */
    public function clear_cache( $type, $args ) {
        $cache_key = $this->build_cache_key( $type, $args );
        return delete_transient( $cache_key );
    }

    // =========================================================================
    // PROMPT BUILDING
    // =========================================================================

    /**
     * Build the prompt for problem title generation.
     *
     * @param array $args Generation arguments.
     * @return string The constructed prompt.
     */
    private function build_problem_titles_prompt( $args ) {
        $brain_summary = $this->summarize_brain_content( $args['brain_content'] );
        $industries    = $this->format_industries( $args['industries'] );
        $service_area  = sanitize_text_field( $args['service_area_name'] );

        $prompt = <<<PROMPT
You are an expert content marketing strategist specializing in B2B and service-based industries.

TASK: Generate exactly 10 problem titles for a content marketing journey circle.

CONTEXT:
- Service Area: {$service_area}
- Target Industries: {$industries}
- Source Material (Brain Content):
{$brain_summary}

REQUIREMENTS FOR PROBLEM TITLES:
1. Each title should describe a specific, painful problem that the target audience faces
2. Write from the perspective of the potential customer experiencing the problem
3. Be specific to the listed industries — avoid generic business problems
4. Make titles content-marketing friendly — each should work as the basis for a long-form article, blog post, or whitepaper
5. Focus on problems that the service area can ultimately solve
6. Use language that resonates with decision-makers and stakeholders
7. Vary the angle — cover different aspects of the pain point (cost, efficiency, risk, compliance, growth, talent, technology, etc.)
8. Keep titles concise but descriptive (8-15 words each)
9. Do NOT include numbering or bullet points in the titles themselves

RESPONSE FORMAT:
Return ONLY a valid JSON object with this exact structure:
{
  "titles": [
    "First problem title here",
    "Second problem title here",
    "Third problem title here",
    "Fourth problem title here",
    "Fifth problem title here",
    "Sixth problem title here",
    "Seventh problem title here",
    "Eighth problem title here",
    "Ninth problem title here",
    "Tenth problem title here"
  ]
}

Return ONLY the JSON object. No markdown, no code fences, no explanation.
PROMPT;

        return $prompt;
    }

    /**
     * Build the prompt for solution title generation.
     *
     * @param array $args Generation arguments.
     * @return string The constructed prompt.
     */
    private function build_solution_titles_prompt( $args ) {
        $brain_summary = $this->summarize_brain_content( $args['brain_content'] );
        $problem_title = sanitize_text_field( $args['problem_title'] );
        $service_area  = sanitize_text_field( $args['service_area_name'] );
        $industries    = $this->format_industries( $args['industries'] );

        $prompt = <<<PROMPT
You are an expert content marketing strategist specializing in B2B and service-based industries.

TASK: Generate exactly 3 solution titles that address a specific problem.

PROBLEM BEING SOLVED:
"{$problem_title}"

CONTEXT:
- Service Area: {$service_area}
- Target Industries: {$industries}
- Source Material (Brain Content):
{$brain_summary}

REQUIREMENTS FOR SOLUTION TITLES:
1. Each title should present a clear, actionable solution approach to the stated problem
2. Solutions should be distinct from each other — offer genuinely different strategic angles
3. Write from the perspective of a trusted advisor proposing solutions
4. Make titles content-marketing friendly — each should work as the basis for solution-focused content
5. Be specific enough to be compelling but broad enough to generate multiple content pieces
6. Use confident, authoritative language that inspires trust
7. Keep titles concise but descriptive (8-15 words each)
8. Do NOT include numbering or bullet points in the titles themselves

RESPONSE FORMAT:
Return ONLY a valid JSON object with this exact structure:
{
  "titles": [
    "First solution title here",
    "Second solution title here",
    "Third solution title here"
  ]
}

Return ONLY the JSON object. No markdown, no code fences, no explanation.
PROMPT;

        return $prompt;
    }

    // =========================================================================
    // API COMMUNICATION
    // =========================================================================

    /**
     * Call the Gemini API with a prompt.
     *
     * @param string $prompt The prompt text.
     * @return string|WP_Error Response text on success, WP_Error on failure.
     */
    private function call_gemini_api( $prompt ) {
        if ( ! $this->is_configured() ) {
            $this->last_error = __( 'Gemini API key is not configured. Please set it in DirectReach AI Settings.', 'directreach' );
            return new WP_Error( 'api_not_configured', $this->last_error );
        }

        $url = self::API_BASE_URL . $this->model . ':generateContent?key=' . $this->api_key;

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
                'temperature'     => 0.8,
                'topP'            => 0.9,
                'topK'            => 40,
                'maxOutputTokens' => 2048,
                'responseMimeType' => 'application/json',
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
            'timeout' => self::API_TIMEOUT,
        ) );

        // Handle connection errors.
        if ( is_wp_error( $response ) ) {
            $this->last_error = sprintf(
                /* translators: %s: error message */
                __( 'Failed to connect to Gemini API: %s', 'directreach' ),
                $response->get_error_message()
            );

            // Check for timeout specifically.
            if ( strpos( $response->get_error_message(), 'timed out' ) !== false
                || strpos( $response->get_error_message(), 'timeout' ) !== false ) {
                return new WP_Error(
                    'api_timeout',
                    __( 'The AI request timed out. Please try again.', 'directreach' )
                );
            }

            return new WP_Error( 'api_connection_error', $this->last_error );
        }

        // Check HTTP status code.
        $status_code = wp_remote_retrieve_response_code( $response );

        if ( $status_code !== 200 ) {
            $body_raw = wp_remote_retrieve_body( $response );
            $error_data = json_decode( $body_raw, true );

            $error_message = isset( $error_data['error']['message'] )
                ? $error_data['error']['message']
                : sprintf(
                    /* translators: %d: HTTP status code */
                    __( 'Gemini API returned status %d', 'directreach' ),
                    $status_code
                );

            $this->last_error = $error_message;

            // Map common HTTP errors.
            $error_code_map = array(
                400 => 'api_bad_request',
                401 => 'api_unauthorized',
                403 => 'api_forbidden',
                429 => 'api_rate_limited',
                500 => 'api_server_error',
                503 => 'api_unavailable',
            );

            $wp_error_code = isset( $error_code_map[ $status_code ] )
                ? $error_code_map[ $status_code ]
                : 'api_error';

            // Provide user-friendly messages for common errors.
            $user_messages = array(
                'api_unauthorized' => __( 'The Gemini API key is invalid. Please check your AI settings.', 'directreach' ),
                'api_forbidden'    => __( 'Access denied by Gemini API. Please verify your API key permissions.', 'directreach' ),
                'api_rate_limited' => __( 'Too many AI requests. Please wait a moment and try again.', 'directreach' ),
                'api_unavailable'  => __( 'The AI service is temporarily unavailable. Please try again later.', 'directreach' ),
            );

            $user_message = isset( $user_messages[ $wp_error_code ] )
                ? $user_messages[ $wp_error_code ]
                : $error_message;

            return new WP_Error( $wp_error_code, $user_message, array(
                'status'    => $status_code,
                'raw_error' => $error_message,
            ) );
        }

        // Parse successful response.
        $body_raw  = wp_remote_retrieve_body( $response );
        $body_data = json_decode( $body_raw, true );

        if ( json_last_error() !== JSON_ERROR_NONE ) {
            $this->last_error = __( 'Failed to parse Gemini API response.', 'directreach' );
            return new WP_Error( 'api_parse_error', $this->last_error );
        }

        // Extract text from Gemini response structure.
        $text = $this->extract_gemini_text( $body_data );

        if ( is_wp_error( $text ) ) {
            return $text;
        }

        return $text;
    }

    /**
     * Extract text content from Gemini API response structure.
     *
     * @param array $body_data Decoded response body.
     * @return string|WP_Error Extracted text or error.
     */
    private function extract_gemini_text( $body_data ) {
        // Standard Gemini response structure:
        // candidates[0].content.parts[0].text
        if ( isset( $body_data['candidates'][0]['content']['parts'][0]['text'] ) ) {
            return $body_data['candidates'][0]['content']['parts'][0]['text'];
        }

        // Check for blocked content.
        if ( isset( $body_data['candidates'][0]['finishReason'] )
            && $body_data['candidates'][0]['finishReason'] === 'SAFETY' ) {
            $this->last_error = __( 'The AI flagged the request as potentially unsafe. Please try different input.', 'directreach' );
            return new WP_Error( 'ai_safety_blocked', $this->last_error );
        }

        // Check for prompt feedback blocking.
        if ( isset( $body_data['promptFeedback']['blockReason'] ) ) {
            $this->last_error = sprintf(
                /* translators: %s: block reason */
                __( 'The AI blocked this request: %s', 'directreach' ),
                $body_data['promptFeedback']['blockReason']
            );
            return new WP_Error( 'ai_prompt_blocked', $this->last_error );
        }

        // Unexpected response structure.
        $this->last_error = __( 'Unexpected response format from Gemini API.', 'directreach' );
        return new WP_Error( 'api_unexpected_response', $this->last_error );
    }

    // =========================================================================
    // RESPONSE PARSING
    // =========================================================================

    /**
     * Parse the AI response text into an array of titles.
     *
     * Handles JSON parsing with multiple fallback strategies.
     *
     * @param string $response_text Raw response text from AI.
     * @param string $type          'problems' or 'solutions'.
     * @return array|WP_Error Array of title strings or error.
     */
    private function parse_titles_response( $response_text, $type ) {
        // Strategy 1: Direct JSON parse.
        $data = json_decode( $response_text, true );

        if ( json_last_error() === JSON_ERROR_NONE && isset( $data['titles'] ) && is_array( $data['titles'] ) ) {
            return $this->sanitize_titles( $data['titles'] );
        }

        // Strategy 2: Extract JSON from markdown code fences.
        $cleaned = $this->extract_json_from_text( $response_text );
        if ( $cleaned ) {
            $data = json_decode( $cleaned, true );
            if ( json_last_error() === JSON_ERROR_NONE && isset( $data['titles'] ) && is_array( $data['titles'] ) ) {
                return $this->sanitize_titles( $data['titles'] );
            }
        }

        // Strategy 3: Try to find a JSON array in the response.
        if ( preg_match( '/\[([^\]]+)\]/', $response_text, $matches ) ) {
            $array_str = '[' . $matches[1] . ']';
            $titles    = json_decode( $array_str, true );
            if ( json_last_error() === JSON_ERROR_NONE && is_array( $titles ) ) {
                return $this->sanitize_titles( $titles );
            }
        }

        // Strategy 4: Line-by-line parsing as last resort.
        $lines  = explode( "\n", $response_text );
        $titles = array();
        foreach ( $lines as $line ) {
            $line = trim( $line );
            // Remove numbering like "1.", "1)", "- ", "* ".
            $line = preg_replace( '/^[\d]+[\.\)]\s*/', '', $line );
            $line = preg_replace( '/^[-\*]\s*/', '', $line );
            // Remove surrounding quotes.
            $line = trim( $line, '"\'`' );
            $line = trim( $line );

            if ( strlen( $line ) > 10 && strlen( $line ) < 200 ) {
                $titles[] = $line;
            }
        }

        if ( ! empty( $titles ) ) {
            return $this->sanitize_titles( $titles );
        }

        // All parsing strategies failed.
        $this->last_error = __( 'Could not parse AI response into titles. Please try regenerating.', 'directreach' );
        return new WP_Error( 'parse_error', $this->last_error, array(
            'raw_response' => substr( $response_text, 0, 500 ),
        ) );
    }

    /**
     * Extract JSON string from text that may contain markdown fences.
     *
     * @param string $text Raw text.
     * @return string|false Extracted JSON string or false.
     */
    private function extract_json_from_text( $text ) {
        // Try ```json ... ``` pattern.
        if ( preg_match( '/```(?:json)?\s*(\{[\s\S]*?\})\s*```/', $text, $matches ) ) {
            return $matches[1];
        }

        // Try to find first { ... } block.
        $start = strpos( $text, '{' );
        $end   = strrpos( $text, '}' );

        if ( $start !== false && $end !== false && $end > $start ) {
            return substr( $text, $start, $end - $start + 1 );
        }

        return false;
    }

    /**
     * Sanitize an array of title strings.
     *
     * @param array $titles Raw title strings.
     * @return array Sanitized titles.
     */
    private function sanitize_titles( $titles ) {
        $sanitized = array();
        foreach ( $titles as $title ) {
            if ( ! is_string( $title ) ) {
                continue;
            }
            $title = sanitize_text_field( $title );
            $title = trim( $title, '"\'`' );
            $title = trim( $title );

            // Skip empty or too-short titles.
            if ( strlen( $title ) < 5 ) {
                continue;
            }

            // Skip duplicates.
            if ( ! in_array( $title, $sanitized, true ) ) {
                $sanitized[] = $title;
            }
        }
        return $sanitized;
    }

    // =========================================================================
    // BRAIN CONTENT PROCESSING
    // =========================================================================

    /**
     * Summarize brain content into a text block for prompts.
     *
     * @param array $brain_content Array of brain content items.
     * @return string Summarized text.
     */
    private function summarize_brain_content( $brain_content ) {
        if ( empty( $brain_content ) || ! is_array( $brain_content ) ) {
            return '(No source material provided)';
        }

        $parts = array();
        $url_count  = 0;
        $text_count = 0;
        $file_count = 0;

        foreach ( $brain_content as $item ) {
            if ( ! is_array( $item ) ) {
                continue;
            }

            $type  = isset( $item['type'] ) ? $item['type'] : '';
            $value = isset( $item['value'] ) ? $item['value'] : '';

            switch ( $type ) {
                case 'url':
                    $url_count++;
                    $parts[] = '- Reference URL: ' . esc_url( $value );
                    break;

                case 'text':
                    $text_count++;
                    // Truncate long text to keep prompt manageable.
                    $text = wp_strip_all_tags( $value );
                    if ( strlen( $text ) > 1000 ) {
                        $text = substr( $text, 0, 1000 ) . '... (truncated)';
                    }
                    $parts[] = '- Pasted content: ' . $text;
                    break;

                case 'file':
                    $file_count++;
                    $filename = isset( $item['filename'] ) ? $item['filename'] : $value;
                    $parts[] = '- Uploaded file: ' . sanitize_file_name( $filename );
                    break;
            }
        }

        if ( empty( $parts ) ) {
            return '(No usable source material)';
        }

        $summary = implode( "\n", $parts );

        // Add count summary.
        $counts = array();
        if ( $url_count > 0 ) {
            /* translators: %d: number of URLs */
            $counts[] = sprintf( _n( '%d URL', '%d URLs', $url_count, 'directreach' ), $url_count );
        }
        if ( $text_count > 0 ) {
            /* translators: %d: number of text blocks */
            $counts[] = sprintf( _n( '%d text block', '%d text blocks', $text_count, 'directreach' ), $text_count );
        }
        if ( $file_count > 0 ) {
            /* translators: %d: number of files */
            $counts[] = sprintf( _n( '%d file', '%d files', $file_count, 'directreach' ), $file_count );
        }

        $header = sprintf(
            /* translators: %s: comma-separated count summary */
            __( 'Source material includes: %s', 'directreach' ),
            implode( ', ', $counts )
        );

        return $header . "\n" . $summary;
    }

    /**
     * Format industries array into a readable string for prompts.
     *
     * @param array $industries Industry names or IDs.
     * @return string Formatted industries string.
     */
    private function format_industries( $industries ) {
        if ( empty( $industries ) || ! is_array( $industries ) ) {
            return 'General / All industries';
        }

        $names = array();
        foreach ( $industries as $industry ) {
            if ( is_numeric( $industry ) ) {
                // Try to get term name from taxonomy.
                $term = get_term( intval( $industry ), 'jc_industry' );
                if ( $term && ! is_wp_error( $term ) ) {
                    $names[] = $term->name;
                } else {
                    $names[] = 'Industry #' . intval( $industry );
                }
            } else {
                $names[] = sanitize_text_field( $industry );
            }
        }

        return implode( ', ', $names );
    }

    // =========================================================================
    // CACHE MANAGEMENT
    // =========================================================================

    /**
     * Build a cache key from generation arguments.
     *
     * @param string $type 'problem_titles' or 'solution_titles'.
     * @param array  $args Generation arguments.
     * @return string Cache key.
     */
    private function build_cache_key( $type, $args ) {
        $key_data = array(
            'type'  => $type,
            'model' => $this->model,
        );

        switch ( $type ) {
            case 'problem_titles':
                $key_data['sa']         = $args['service_area_id'] ?? $args['service_area_name'] ?? '';
                $key_data['industries'] = is_array( $args['industries'] ) ? implode( ',', $args['industries'] ) : '';
                $key_data['brain']      = $this->hash_brain_content( $args['brain_content'] ?? array() );
                break;

            case 'solution_titles':
                $key_data['problem'] = $args['problem_title'] ?? '';
                $key_data['brain']   = $this->hash_brain_content( $args['brain_content'] ?? array() );
                break;
        }

        $hash = md5( wp_json_encode( $key_data ) );
        return 'dr_ai_' . $type . '_' . $hash;
    }

    /**
     * Generate a hash of brain content for cache key purposes.
     *
     * @param array $brain_content Brain content array.
     * @return string MD5 hash.
     */
    private function hash_brain_content( $brain_content ) {
        if ( empty( $brain_content ) ) {
            return 'empty';
        }
        return md5( wp_json_encode( $brain_content ) );
    }

    // =========================================================================
    // FALLBACK / PADDING
    // =========================================================================

    /**
     * Pad problem titles if AI returned too few.
     *
     * @param array  $titles        Existing titles.
     * @param string $service_area  Service area name.
     * @return array Padded titles array.
     */
    private function pad_problem_titles( $titles, $service_area ) {
        $generic_patterns = array(
            'Rising costs of managing %s operations without a clear strategy',
            'Difficulty scaling %s processes across growing teams',
            'Lack of visibility into %s performance metrics and ROI',
            'Struggling to keep up with industry changes in %s',
            'Inefficient %s workflows causing missed deadlines and opportunities',
            'Poor alignment between %s strategy and business objectives',
            'High turnover and talent gaps in %s teams',
            'Outdated technology hampering %s effectiveness',
            'Compliance and regulatory challenges in %s',
            'Fragmented %s data making informed decisions impossible',
        );

        $count = count( $titles );
        while ( $count < self::MIN_PROBLEM_TITLES ) {
            $pattern = $generic_patterns[ $count % count( $generic_patterns ) ];
            $title   = sprintf( $pattern, $service_area );
            if ( ! in_array( $title, $titles, true ) ) {
                $titles[] = $title;
            }
            $count++;
        }

        return $titles;
    }

    /**
     * Pad solution titles if AI returned too few.
     *
     * @param array  $titles        Existing titles.
     * @param string $problem_title Problem being solved.
     * @return array Padded titles array.
     */
    private function pad_solution_titles( $titles, $problem_title ) {
        $generic_patterns = array(
            'Implementing a strategic framework to address: %s',
            'Building a data-driven approach to overcome: %s',
            'Leveraging expert guidance to solve: %s',
        );

        $count = count( $titles );
        while ( $count < self::SOLUTION_TITLES_COUNT ) {
            // Truncate problem title for pattern.
            $short_problem = strlen( $problem_title ) > 60
                ? substr( $problem_title, 0, 57 ) . '...'
                : $problem_title;
            $pattern = $generic_patterns[ $count % count( $generic_patterns ) ];
            $title   = sprintf( $pattern, $short_problem );
            if ( ! in_array( $title, $titles, true ) ) {
                $titles[] = $title;
            }
            $count++;
        }

        return $titles;
    }

    // =========================================================================
    // UTILITY METHODS
    // =========================================================================

    /**
     * Load the Gemini API key from WordPress options.
     */
    private function load_api_key() {
        $ai_settings = get_option( 'dr_ai_settings', array() );

        if ( isset( $ai_settings['gemini_api_key'] ) && ! empty( $ai_settings['gemini_api_key'] ) ) {
            $this->api_key = $ai_settings['gemini_api_key'];
            return;
        }

        // Fallback: check for standalone option.
        $standalone_key = get_option( 'dr_gemini_api_key', '' );
        if ( ! empty( $standalone_key ) ) {
            $this->api_key = $standalone_key;
            return;
        }

        // Check Journey Circle specific settings.
        $jc_settings = get_option( 'jc_settings', array() );
        if ( isset( $jc_settings['gemini_api_key'] ) && ! empty( $jc_settings['gemini_api_key'] ) ) {
            $this->api_key = $jc_settings['gemini_api_key'];
        }
    }

    /**
     * Get service area name from ID.
     *
     * @param int $service_area_id Service area post ID.
     * @return string Service area name.
     */
    private function get_service_area_name( $service_area_id ) {
        // Try custom post type.
        $post = get_post( absint( $service_area_id ) );
        if ( $post && ! is_wp_error( $post ) ) {
            return $post->post_title;
        }

        // Fallback: try custom table.
        global $wpdb;
        $table = $wpdb->prefix . 'dr_service_areas';
        $name  = $wpdb->get_var(
            $wpdb->prepare( "SELECT name FROM {$table} WHERE id = %d", $service_area_id )
        );

        return $name ? $name : __( 'Unknown Service Area', 'directreach' );
    }
}
