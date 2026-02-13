<?php
/**
 * AI Content Generator Extension - Iteration 9
 * 
 * Extends the existing DR_AI_Content_Generator class with methods for
 * outline generation, content generation, and revision handling.
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Add these methods to the existing DR_AI_Content_Generator class
 * in /includes/journey-circle/class-ai-content-generator.php
 */

// ============================================================================
// OUTLINE GENERATION METHODS
// ============================================================================

/**
 * Generate a content outline for a problem or solution.
 *
 * @param array $args {
 *     Arguments for outline generation.
 *     @type int    $journey_circle_id Journey circle ID.
 *     @type string $linked_to_type    'problem' or 'solution'.
 *     @type int    $linked_to_id      Problem or solution ID.
 *     @type string $asset_type        'article_long', 'article_short', or 'infographic'.
 *     @type array  $brain_content     Array of brain content items.
 *     @type array  $industries        Array of industry names.
 *     @type string $service_area_name Service area name.
 *     @type string $problem_title     The problem title.
 *     @type string $solution_title    The solution title (if applicable).
 * }
 * @return array|WP_Error Array with 'outline', 'title', 'asset_id' on success.
 */
public function generate_outline($args) {
    $defaults = array(
        'journey_circle_id' => 0,
        'linked_to_type'    => '',
        'linked_to_id'      => 0,
        'asset_type'        => 'article_long',
        'brain_content'     => array(),
        'industries'        => array(),
        'service_area_name' => '',
        'problem_title'     => '',
        'solution_title'    => '',
    );
    
    $args = wp_parse_args($args, $defaults);
    
    // Validate required fields
    if (empty($args['journey_circle_id']) || empty($args['linked_to_type']) || empty($args['linked_to_id'])) {
        return new WP_Error('missing_required', __('Missing required parameters for outline generation.', 'directreach'));
    }
    
    if (!in_array($args['linked_to_type'], array('problem', 'solution'), true)) {
        return new WP_Error('invalid_type', __('Invalid linked_to_type. Must be "problem" or "solution".', 'directreach'));
    }
    
    if (!in_array($args['asset_type'], array('article_long', 'article_short', 'infographic'), true)) {
        return new WP_Error('invalid_asset_type', __('Invalid asset type.', 'directreach'));
    }
    
    // Check for cached outline
    $cache_key = $this->get_outline_cache_key($args);
    $cached = get_transient($cache_key);
    if ($cached !== false) {
        // Create or update asset record with cached outline
        $asset_id = $this->create_or_update_asset($args, $cached['outline'], $cached['title']);
        if (is_wp_error($asset_id)) {
            return $asset_id;
        }
        return array(
            'outline'  => $cached['outline'],
            'title'    => $cached['title'],
            'asset_id' => $asset_id,
            'cached'   => true,
        );
    }
    
    // Build the prompt
    $prompt = $this->build_outline_prompt($args);
    
    // Call Gemini API
    $response = $this->call_gemini_api($prompt, array(
        'temperature'   => 0.7,
        'max_tokens'    => 2000,
        'response_type' => 'application/json',
        'timeout'       => 30,
    ));
    
    if (is_wp_error($response)) {
        return $response;
    }
    
    // Parse the response
    $parsed = $this->parse_outline_response($response, $args);
    if (is_wp_error($parsed)) {
        return $parsed;
    }
    
    // Cache the outline (30 minutes)
    set_transient($cache_key, $parsed, 30 * MINUTE_IN_SECONDS);
    
    // Create asset record
    $asset_id = $this->create_or_update_asset($args, $parsed['outline'], $parsed['title']);
    if (is_wp_error($asset_id)) {
        return $asset_id;
    }
    
    return array(
        'outline'  => $parsed['outline'],
        'title'    => $parsed['title'],
        'asset_id' => $asset_id,
        'cached'   => false,
    );
}

/**
 * Build the prompt for outline generation.
 *
 * @param array $args Generation arguments.
 * @return string The formatted prompt.
 */
private function build_outline_prompt($args) {
    $asset_type_labels = array(
        'article_long'  => 'Long-form Article (2000-3000 words)',
        'article_short' => 'Short Article (800-1200 words)',
        'infographic'   => 'Infographic Content (key points and statistics)',
    );
    
    $format_label = $asset_type_labels[$args['asset_type']] ?? 'Article';
    $content_focus = $args['linked_to_type'] === 'problem' ? 'problem' : 'solution';
    
    // Prepare brain content summary
    $brain_summary = $this->summarize_brain_content($args['brain_content']);
    
    // Prepare industries
    $industries_text = !empty($args['industries']) 
        ? implode(', ', $args['industries']) 
        : 'General business';
    
    $prompt = <<<PROMPT
You are an expert content strategist creating a detailed outline for a {$format_label}.

CONTEXT:
- Service Area: {$args['service_area_name']}
- Target Industries: {$industries_text}
- Content Focus: {$content_focus}
- Problem Being Addressed: {$args['problem_title']}
PROMPT;

    if (!empty($args['solution_title'])) {
        $prompt .= "\n- Solution Being Presented: {$args['solution_title']}";
    }

    if (!empty($brain_summary)) {
        $prompt .= "\n\nBACKGROUND INFORMATION:\n{$brain_summary}";
    }

    $prompt .= <<<PROMPT


TASK:
Create a comprehensive outline for content that addresses this {$content_focus}. The outline should be structured, actionable, and designed to engage readers in the {$industries_text} space.

REQUIREMENTS:
1. Generate a compelling, SEO-friendly title
2. Create 4-6 main sections with clear headings
3. Include 2-4 key points under each section
4. Suggest relevant statistics or data points where appropriate
5. Include a call-to-action section

OUTPUT FORMAT:
Respond with a JSON object in this exact structure:
{
    "title": "The compelling article title",
    "sections": [
        {
            "heading": "Section Heading",
            "key_points": [
                "Key point 1",
                "Key point 2"
            ],
            "suggested_data": "Relevant statistic or data point to include",
            "estimated_words": 400
        }
    ],
    "total_estimated_words": 2500,
    "target_audience": "Description of primary audience",
    "key_takeaways": [
        "Main takeaway 1",
        "Main takeaway 2"
    ],
    "cta_suggestion": "Suggested call-to-action"
}

Generate the outline now:
PROMPT;

    return $prompt;
}

/**
 * Parse the outline response from Gemini.
 *
 * @param string $response Raw API response.
 * @param array  $args     Original arguments.
 * @return array|WP_Error Parsed outline data.
 */
private function parse_outline_response($response, $args) {
    // Try to parse as JSON
    $data = json_decode($response, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        // Try to extract JSON from response
        $data = $this->extract_json_from_response($response);
        
        if ($data === null) {
            return new WP_Error(
                'parse_error',
                __('Failed to parse outline response from AI.', 'directreach'),
                array('raw_response' => $response)
            );
        }
    }
    
    // Validate required fields
    if (empty($data['title']) || empty($data['sections'])) {
        return new WP_Error(
            'invalid_response',
            __('AI response missing required outline fields.', 'directreach'),
            array('parsed_data' => $data)
        );
    }
    
    // Format the outline as readable text
    $outline_text = $this->format_outline_as_text($data);
    
    return array(
        'outline' => $outline_text,
        'title'   => sanitize_text_field($data['title']),
        'data'    => $data,
    );
}

/**
 * Format parsed outline data as readable text.
 *
 * @param array $data Parsed outline data.
 * @return string Formatted outline text.
 */
private function format_outline_as_text($data) {
    $output = "# " . $data['title'] . "\n\n";
    
    if (!empty($data['target_audience'])) {
        $output .= "**Target Audience:** " . $data['target_audience'] . "\n\n";
    }
    
    if (!empty($data['total_estimated_words'])) {
        $output .= "**Estimated Length:** ~" . number_format($data['total_estimated_words']) . " words\n\n";
    }
    
    $output .= "---\n\n## Outline\n\n";
    
    $section_num = 1;
    foreach ($data['sections'] as $section) {
        $output .= "### {$section_num}. {$section['heading']}\n";
        
        if (!empty($section['estimated_words'])) {
            $output .= "*({$section['estimated_words']} words)*\n";
        }
        
        $output .= "\n";
        
        if (!empty($section['key_points'])) {
            foreach ($section['key_points'] as $point) {
                $output .= "- {$point}\n";
            }
        }
        
        if (!empty($section['suggested_data'])) {
            $output .= "\n📊 **Data/Stat:** {$section['suggested_data']}\n";
        }
        
        $output .= "\n";
        $section_num++;
    }
    
    if (!empty($data['key_takeaways'])) {
        $output .= "---\n\n## Key Takeaways\n\n";
        foreach ($data['key_takeaways'] as $takeaway) {
            $output .= "- {$takeaway}\n";
        }
        $output .= "\n";
    }
    
    if (!empty($data['cta_suggestion'])) {
        $output .= "---\n\n## Call to Action\n\n";
        $output .= $data['cta_suggestion'] . "\n";
    }
    
    return $output;
}

/**
 * Revise an outline based on user feedback.
 *
 * @param array $args {
 *     Arguments for outline revision.
 *     @type int    $asset_id        Asset ID.
 *     @type string $current_outline Current outline text.
 *     @type string $feedback        User feedback for revision.
 * }
 * @return array|WP_Error Array with 'outline' on success.
 */
public function revise_outline($args) {
    $defaults = array(
        'asset_id'        => 0,
        'current_outline' => '',
        'feedback'        => '',
    );
    
    $args = wp_parse_args($args, $defaults);
    
    if (empty($args['asset_id']) || empty($args['current_outline']) || empty($args['feedback'])) {
        return new WP_Error('missing_required', __('Missing required parameters for outline revision.', 'directreach'));
    }
    
    // Get asset details for context
    $asset = $this->get_asset($args['asset_id']);
    if (is_wp_error($asset)) {
        return $asset;
    }
    
    $prompt = <<<PROMPT
You are revising a content outline based on feedback.

CURRENT OUTLINE:
{$args['current_outline']}

USER FEEDBACK:
{$args['feedback']}

TASK:
Revise the outline to address the feedback while maintaining the overall structure and quality. Make specific changes based on the feedback provided.

OUTPUT FORMAT:
Respond with a JSON object in this exact structure:
{
    "title": "The revised article title (if changed, otherwise keep original)",
    "sections": [
        {
            "heading": "Section Heading",
            "key_points": [
                "Key point 1",
                "Key point 2"
            ],
            "suggested_data": "Relevant statistic or data point to include",
            "estimated_words": 400
        }
    ],
    "total_estimated_words": 2500,
    "target_audience": "Description of primary audience",
    "key_takeaways": [
        "Main takeaway 1",
        "Main takeaway 2"
    ],
    "cta_suggestion": "Suggested call-to-action",
    "revision_notes": "Brief explanation of changes made"
}

Generate the revised outline now:
PROMPT;

    $response = $this->call_gemini_api($prompt, array(
        'temperature'   => 0.7,
        'max_tokens'    => 2000,
        'response_type' => 'application/json',
        'timeout'       => 30,
    ));
    
    if (is_wp_error($response)) {
        return $response;
    }
    
    // Parse the response
    $data = json_decode($response, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        $data = $this->extract_json_from_response($response);
        if ($data === null) {
            return new WP_Error('parse_error', __('Failed to parse revised outline.', 'directreach'));
        }
    }
    
    $outline_text = $this->format_outline_as_text($data);
    
    // Update the asset
    $this->update_asset_outline($args['asset_id'], $outline_text, $data['title'] ?? '');
    
    // Clear the cache for this asset
    $this->clear_outline_cache($args['asset_id']);
    
    return array(
        'outline'        => $outline_text,
        'title'          => sanitize_text_field($data['title'] ?? ''),
        'revision_notes' => $data['revision_notes'] ?? '',
    );
}

// ============================================================================
// CONTENT GENERATION METHODS
// ============================================================================

/**
 * Generate full content from an approved outline.
 *
 * @param array $args {
 *     Arguments for content generation.
 *     @type int    $asset_id Asset ID with approved outline.
 *     @type string $outline  The approved outline text.
 * }
 * @return array|WP_Error Array with 'content', 'title' on success.
 */
public function generate_content($args) {
    $defaults = array(
        'asset_id' => 0,
        'outline'  => '',
    );
    
    $args = wp_parse_args($args, $defaults);
    
    if (empty($args['asset_id']) || empty($args['outline'])) {
        return new WP_Error('missing_required', __('Missing required parameters for content generation.', 'directreach'));
    }
    
    // Get asset details
    $asset = $this->get_asset($args['asset_id']);
    if (is_wp_error($asset)) {
        return $asset;
    }
    
    // Get journey circle context
    $context = $this->get_content_context($asset);
    
    $prompt = $this->build_content_prompt($args['outline'], $asset, $context);
    
    // Content generation needs longer timeout
    $response = $this->call_gemini_api($prompt, array(
        'temperature'   => 0.75,
        'max_tokens'    => 8000,
        'response_type' => 'text/plain', // HTML content, not JSON
        'timeout'       => 60,
    ));
    
    if (is_wp_error($response)) {
        return $response;
    }
    
    // Clean and validate the content
    $content = $this->clean_generated_content($response);
    
    // Update asset with draft content
    $update_result = $this->update_asset_content($args['asset_id'], $content, 'draft');
    if (is_wp_error($update_result)) {
        return $update_result;
    }
    
    return array(
        'content' => $content,
        'title'   => $asset->title,
    );
}

/**
 * Build the prompt for content generation.
 *
 * @param string   $outline The approved outline.
 * @param object   $asset   Asset object.
 * @param array    $context Journey circle context.
 * @return string The formatted prompt.
 */
private function build_content_prompt($outline, $asset, $context) {
    $word_targets = array(
        'article_long'  => '2000-3000',
        'article_short' => '800-1200',
        'infographic'   => '500-800',
    );
    
    $word_target = $word_targets[$asset->asset_type] ?? '1500-2000';
    
    $prompt = <<<PROMPT
You are an expert content writer creating professional, engaging content for B2B audiences.

CONTENT CONTEXT:
- Service Area: {$context['service_area_name']}
- Target Industries: {$context['industries']}
- Topic: {$asset->title}
- Content Type: {$asset->asset_type}
- Target Length: {$word_target} words

APPROVED OUTLINE:
{$outline}

BACKGROUND INFORMATION:
{$context['brain_summary']}

TASK:
Write the complete article following the approved outline. Create professional, engaging content that:
1. Addresses the target audience's pain points
2. Provides actionable insights and solutions
3. Includes relevant examples and data points
4. Maintains a professional yet approachable tone
5. Flows naturally from section to section

FORMATTING REQUIREMENTS:
- Use proper HTML formatting (h2, h3, p, ul, li, strong, em)
- Start with a compelling introduction (no H1, title is added separately)
- Use H2 for main sections, H3 for subsections
- Include a conclusion with clear takeaways
- Add a call-to-action at the end
- Use proper paragraph breaks for readability

OUTPUT:
Write the complete article content in HTML format. Do not include markdown, only clean HTML.

Begin writing the article:
PROMPT;

    return $prompt;
}

/**
 * Clean and validate generated content.
 *
 * @param string $content Raw generated content.
 * @return string Cleaned HTML content.
 */
private function clean_generated_content($content) {
    // Remove any markdown code fences
    $content = preg_replace('/^```html?\s*/i', '', $content);
    $content = preg_replace('/\s*```$/i', '', $content);
    
    // Ensure content starts with proper HTML
    $content = trim($content);
    
    // Basic HTML sanitization while preserving structure
    $allowed_tags = array(
        'h2'     => array('class' => array(), 'id' => array()),
        'h3'     => array('class' => array(), 'id' => array()),
        'h4'     => array('class' => array(), 'id' => array()),
        'p'      => array('class' => array()),
        'ul'     => array('class' => array()),
        'ol'     => array('class' => array()),
        'li'     => array('class' => array()),
        'strong' => array(),
        'em'     => array(),
        'b'      => array(),
        'i'      => array(),
        'a'      => array('href' => array(), 'title' => array(), 'target' => array()),
        'br'     => array(),
        'hr'     => array(),
        'blockquote' => array('class' => array()),
        'div'    => array('class' => array()),
        'span'   => array('class' => array()),
    );
    
    $content = wp_kses($content, $allowed_tags);
    
    return $content;
}

/**
 * Revise content based on user feedback.
 *
 * @param array $args {
 *     Arguments for content revision.
 *     @type int    $asset_id        Asset ID.
 *     @type string $current_content Current content HTML.
 *     @type string $feedback        User feedback for revision.
 * }
 * @return array|WP_Error Array with 'content' on success.
 */
public function revise_content($args) {
    $defaults = array(
        'asset_id'        => 0,
        'current_content' => '',
        'feedback'        => '',
    );
    
    $args = wp_parse_args($args, $defaults);
    
    if (empty($args['asset_id']) || empty($args['current_content']) || empty($args['feedback'])) {
        return new WP_Error('missing_required', __('Missing required parameters for content revision.', 'directreach'));
    }
    
    $asset = $this->get_asset($args['asset_id']);
    if (is_wp_error($asset)) {
        return $asset;
    }
    
    $prompt = <<<PROMPT
You are revising article content based on user feedback.

CURRENT CONTENT:
{$args['current_content']}

USER FEEDBACK:
{$args['feedback']}

TASK:
Revise the content to address the feedback while:
1. Maintaining the overall structure and flow
2. Keeping the same professional tone
3. Making specific changes based on the feedback
4. Preserving any sections that weren't mentioned in feedback

OUTPUT:
Provide the complete revised article in clean HTML format. Do not include markdown, only HTML.

Write the revised content:
PROMPT;

    $response = $this->call_gemini_api($prompt, array(
        'temperature'   => 0.7,
        'max_tokens'    => 8000,
        'response_type' => 'text/plain',
        'timeout'       => 60,
    ));
    
    if (is_wp_error($response)) {
        return $response;
    }
    
    $content = $this->clean_generated_content($response);
    
    // Update asset content (still draft status)
    $this->update_asset_content($args['asset_id'], $content, 'draft');
    
    return array(
        'content' => $content,
    );
}

// ============================================================================
// HELPER METHODS
// ============================================================================

/**
 * Get the cache key for an outline.
 *
 * @param array $args Outline generation arguments.
 * @return string Cache key.
 */
private function get_outline_cache_key($args) {
    $key_parts = array(
        'dr_outline',
        $args['journey_circle_id'],
        $args['linked_to_type'],
        $args['linked_to_id'],
        $args['asset_type'],
    );
    return implode('_', $key_parts);
}

/**
 * Clear outline cache for an asset.
 *
 * @param int $asset_id Asset ID.
 */
private function clear_outline_cache($asset_id) {
    $asset = $this->get_asset($asset_id);
    if (!is_wp_error($asset)) {
        $key = "dr_outline_{$asset->journey_circle_id}_{$asset->linked_to_type}_{$asset->linked_to_id}_{$asset->asset_type}";
        delete_transient($key);
    }
}

/**
 * Summarize brain content for prompts.
 *
 * @param array $brain_content Array of brain content items.
 * @return string Summarized content.
 */
private function summarize_brain_content($brain_content) {
    if (empty($brain_content)) {
        return '';
    }
    
    $summaries = array();
    foreach ($brain_content as $item) {
        $type = $item['type'] ?? 'unknown';
        $content = $item['content'] ?? $item['value'] ?? '';
        
        if (empty($content)) {
            continue;
        }
        
        // Truncate long content
        if (strlen($content) > 1000) {
            $content = substr($content, 0, 1000) . '...';
        }
        
        $summaries[] = "[{$type}] {$content}";
    }
    
    return implode("\n\n", $summaries);
}

/**
 * Get content context from journey circle.
 *
 * @param object $asset Asset object.
 * @return array Context data.
 */
private function get_content_context($asset) {
    global $wpdb;
    
    $table_circles = $wpdb->prefix . 'dr_journey_circles';
    $table_service = $wpdb->prefix . 'dr_service_areas';
    
    $circle = $wpdb->get_row($wpdb->prepare(
        "SELECT jc.*, sa.name as service_area_name 
         FROM {$table_circles} jc
         LEFT JOIN {$table_service} sa ON jc.service_area_id = sa.id
         WHERE jc.id = %d",
        $asset->journey_circle_id
    ));
    
    $industries = '';
    if ($circle && !empty($circle->industries)) {
        $industry_ids = json_decode($circle->industries, true);
        if (is_array($industry_ids)) {
            // Get industry names (assuming they're stored or use IDs)
            $industries = implode(', ', array_map('strval', $industry_ids));
        }
    }
    
    $brain_content = array();
    if ($circle && !empty($circle->brain_content)) {
        $brain_content = json_decode($circle->brain_content, true) ?: array();
    }
    
    return array(
        'service_area_name' => $circle->service_area_name ?? 'Professional Services',
        'industries'        => $industries ?: 'General Business',
        'brain_summary'     => $this->summarize_brain_content($brain_content),
    );
}

/**
 * Create or update an asset record.
 *
 * @param array  $args    Generation arguments.
 * @param string $outline Generated outline.
 * @param string $title   Generated title.
 * @return int|WP_Error Asset ID on success.
 */
private function create_or_update_asset($args, $outline, $title) {
    global $wpdb;
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    // Check if asset already exists
    $existing = $wpdb->get_var($wpdb->prepare(
        "SELECT id FROM {$table} 
         WHERE journey_circle_id = %d 
         AND linked_to_type = %s 
         AND linked_to_id = %d 
         AND asset_type = %s",
        $args['journey_circle_id'],
        $args['linked_to_type'],
        $args['linked_to_id'],
        $args['asset_type']
    ));
    
    $data = array(
        'journey_circle_id' => absint($args['journey_circle_id']),
        'linked_to_type'    => sanitize_text_field($args['linked_to_type']),
        'linked_to_id'      => absint($args['linked_to_id']),
        'asset_type'        => sanitize_text_field($args['asset_type']),
        'title'             => sanitize_text_field($title),
        'outline'           => $outline,
        'status'            => 'outline',
        'updated_at'        => current_time('mysql'),
    );
    
    if ($existing) {
        $result = $wpdb->update(
            $table,
            $data,
            array('id' => $existing),
            array('%d', '%s', '%d', '%s', '%s', '%s', '%s', '%s'),
            array('%d')
        );
        
        return $result !== false ? (int) $existing : new WP_Error('db_error', __('Failed to update asset.', 'directreach'));
    }
    
    $data['created_at'] = current_time('mysql');
    
    $result = $wpdb->insert(
        $table,
        $data,
        array('%d', '%s', '%d', '%s', '%s', '%s', '%s', '%s', '%s')
    );
    
    return $result ? $wpdb->insert_id : new WP_Error('db_error', __('Failed to create asset.', 'directreach'));
}

/**
 * Update asset outline.
 *
 * @param int    $asset_id Asset ID.
 * @param string $outline  New outline.
 * @param string $title    New title (optional).
 */
private function update_asset_outline($asset_id, $outline, $title = '') {
    global $wpdb;
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    $data = array(
        'outline'    => $outline,
        'updated_at' => current_time('mysql'),
    );
    
    if (!empty($title)) {
        $data['title'] = sanitize_text_field($title);
    }
    
    $wpdb->update($table, $data, array('id' => $asset_id));
}

/**
 * Update asset content.
 *
 * @param int    $asset_id Asset ID.
 * @param string $content  Content HTML.
 * @param string $status   New status.
 * @return bool|WP_Error True on success.
 */
private function update_asset_content($asset_id, $content, $status = 'draft') {
    global $wpdb;
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    $result = $wpdb->update(
        $table,
        array(
            'content'    => $content,
            'status'     => $status,
            'updated_at' => current_time('mysql'),
        ),
        array('id' => $asset_id),
        array('%s', '%s', '%s'),
        array('%d')
    );
    
    return $result !== false ? true : new WP_Error('db_error', __('Failed to update asset content.', 'directreach'));
}

/**
 * Get asset by ID.
 *
 * @param int $asset_id Asset ID.
 * @return object|WP_Error Asset object on success.
 */
private function get_asset($asset_id) {
    global $wpdb;
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    $asset = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$table} WHERE id = %d",
        $asset_id
    ));
    
    if (!$asset) {
        return new WP_Error('not_found', __('Asset not found.', 'directreach'));
    }
    
    return $asset;
}

/**
 * Approve asset content (change status to approved).
 *
 * @param int $asset_id Asset ID.
 * @return bool|WP_Error True on success.
 */
public function approve_asset($asset_id) {
    global $wpdb;
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    $result = $wpdb->update(
        $table,
        array(
            'status'     => 'approved',
            'updated_at' => current_time('mysql'),
        ),
        array('id' => $asset_id),
        array('%s', '%s'),
        array('%d')
    );
    
    return $result !== false ? true : new WP_Error('db_error', __('Failed to approve asset.', 'directreach'));
}

/**
 * Mark asset as published with URL.
 *
 * @param int    $asset_id Asset ID.
 * @param string $url      Published URL.
 * @return bool|WP_Error True on success.
 */
public function publish_asset($asset_id, $url) {
    global $wpdb;
    $table = $wpdb->prefix . 'dr_journey_assets';
    
    $result = $wpdb->update(
        $table,
        array(
            'url'        => esc_url_raw($url),
            'status'     => 'published',
            'updated_at' => current_time('mysql'),
        ),
        array('id' => $asset_id),
        array('%s', '%s', '%s'),
        array('%d')
    );
    
    return $result !== false ? true : new WP_Error('db_error', __('Failed to publish asset.', 'directreach'));
}

/**
 * Extract JSON from a response that may contain extra text.
 *
 * @param string $response Raw response text.
 * @return array|null Parsed JSON or null.
 */
private function extract_json_from_response($response) {
    // Try to find JSON object
    if (preg_match('/\{[\s\S]*\}/', $response, $matches)) {
        $potential_json = $matches[0];
        $data = json_decode($potential_json, true);
        if (json_last_error() === JSON_ERROR_NONE) {
            return $data;
        }
    }
    
    return null;
}
