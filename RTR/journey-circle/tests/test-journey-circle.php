<?php
/**
 * Journey Circle Tests
 *
 * @package Journey_Circle
 */

class Journey_Circle_Test extends WP_UnitTestCase {

    /**
     * Service Area Manager instance
     */
    protected $service_area_manager;
    
    /**
     * Journey Circle Manager instance
     */
    protected $journey_manager;
    
    /**
     * Brain Content Manager instance
     */
    protected $brain_content_manager;

    /**
     * Setup test environment
     */
    public function setUp(): void {
        parent::setUp();
        
        $this->service_area_manager = new Service_Area_Manager();
        $this->journey_manager = new Journey_Circle_Manager();
        $this->brain_content_manager = new Brain_Content_Manager();
    }

    /**
     * Test: Custom post types are registered
     */
    public function test_custom_post_types_registered() {
        $post_types = get_post_types();
        
        $this->assertContains( 'jc_service_area', $post_types );
        $this->assertContains( 'jc_journey_circle', $post_types );
        $this->assertContains( 'jc_problem', $post_types );
        $this->assertContains( 'jc_solution', $post_types );
        $this->assertContains( 'jc_offer', $post_types );
        $this->assertContains( 'jc_brain_content', $post_types );
    }

    /**
     * Test: Custom taxonomies are registered
     */
    public function test_custom_taxonomies_registered() {
        $taxonomies = get_taxonomies();
        
        $this->assertContains( 'jc_industry', $taxonomies );
        $this->assertContains( 'jc_asset_type', $taxonomies );
        $this->assertContains( 'jc_status', $taxonomies );
    }

    /**
     * Test: Create service area
     */
    public function test_create_service_area() {
        $args = array(
            'title'       => 'Cloud Migration Services',
            'description' => 'Helping enterprises migrate to cloud infrastructure',
            'client_id'   => 123,
            'status'      => 'active',
        );
        
        $service_area_id = $this->service_area_manager->create( $args );
        
        $this->assertIsInt( $service_area_id );
        $this->assertGreaterThan( 0, $service_area_id );
        
        // Verify data was saved correctly
        $service_area = $this->service_area_manager->get( $service_area_id );
        
        $this->assertEquals( $args['title'], $service_area['title'] );
        $this->assertEquals( $args['description'], $service_area['description'] );
        $this->assertEquals( $args['client_id'], $service_area['client_id'] );
        $this->assertEquals( $args['status'], $service_area['status'] );
    }

    /**
     * Test: Create service area without title fails
     */
    public function test_create_service_area_without_title_fails() {
        $args = array(
            'description' => 'Missing title',
        );
        
        $result = $this->service_area_manager->create( $args );
        
        $this->assertInstanceOf( WP_Error::class, $result );
        $this->assertEquals( 'missing_title', $result->get_error_code() );
    }

    /**
     * Test: Get service areas by client
     */
    public function test_get_service_areas_by_client() {
        $client_id = 456;
        
        // Create multiple service areas
        $this->service_area_manager->create( array(
            'title'     => 'Service Area 1',
            'client_id' => $client_id,
        ) );
        
        $this->service_area_manager->create( array(
            'title'     => 'Service Area 2',
            'client_id' => $client_id,
        ) );
        
        $service_areas = $this->service_area_manager->get_by_client( $client_id );
        
        $this->assertCount( 2, $service_areas );
        $this->assertEquals( $client_id, $service_areas[0]['client_id'] );
        $this->assertEquals( $client_id, $service_areas[1]['client_id'] );
    }

    /**
     * Test: Create journey circle
     */
    public function test_create_journey_circle() {
        // First create a service area
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        $args = array(
            'service_area_id' => $service_area_id,
            'industries'      => array( 101, 102 ),
            'brain_content'   => array(),
            'status'          => 'incomplete',
        );
        
        $journey_id = $this->journey_manager->create( $args );
        
        $this->assertIsInt( $journey_id );
        $this->assertGreaterThan( 0, $journey_id );
        
        // Verify data
        $journey = $this->journey_manager->get( $journey_id );
        
        $this->assertEquals( $service_area_id, $journey['service_area_id'] );
        $this->assertEquals( $args['status'], $journey['status'] );
    }

    /**
     * Test: Service area can only have one journey circle
     */
    public function test_service_area_one_journey_circle_limit() {
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        // Create first journey circle - should succeed
        $journey_id_1 = $this->journey_manager->create( array(
            'service_area_id' => $service_area_id,
        ) );
        
        $this->assertIsInt( $journey_id_1 );
        
        // Try to create second journey circle - should fail
        $journey_id_2 = $this->journey_manager->create( array(
            'service_area_id' => $service_area_id,
        ) );
        
        $this->assertInstanceOf( WP_Error::class, $journey_id_2 );
        $this->assertEquals( 'circle_exists', $journey_id_2->get_error_code() );
    }

    /**
     * Test: Add problem to journey circle
     */
    public function test_add_problem_to_journey_circle() {
        // Create service area and journey circle
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        $journey_id = $this->journey_manager->create( array(
            'service_area_id' => $service_area_id,
        ) );
        
        // Add problem
        $problem_args = array(
            'title'       => 'Legacy infrastructure costs',
            'description' => 'High maintenance costs for legacy systems',
            'is_primary'  => true,
        );
        
        $problem_id = $this->journey_manager->add_problem( $journey_id, $problem_args );
        
        $this->assertIsInt( $problem_id );
        $this->assertGreaterThan( 0, $problem_id );
        
        // Verify problem was added
        $journey = $this->journey_manager->get( $journey_id );
        $this->assertCount( 1, $journey['problems'] );
        $this->assertEquals( $problem_args['title'], $journey['problems'][0]['title'] );
        $this->assertTrue( $journey['problems'][0]['is_primary'] );
    }

    /**
     * Test: Journey circle problem limit (5 problems max)
     */
    public function test_journey_circle_problem_limit() {
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        $journey_id = $this->journey_manager->create( array(
            'service_area_id' => $service_area_id,
        ) );
        
        // Add 5 problems (should all succeed)
        for ( $i = 1; $i <= 5; $i++ ) {
            $result = $this->journey_manager->add_problem( $journey_id, array(
                'title' => "Problem $i",
            ) );
            
            $this->assertIsInt( $result );
        }
        
        // Try to add 6th problem (should fail)
        $result = $this->journey_manager->add_problem( $journey_id, array(
            'title' => 'Problem 6',
        ) );
        
        $this->assertInstanceOf( WP_Error::class, $result );
        $this->assertEquals( 'max_problems', $result->get_error_code() );
    }

    /**
     * Test: Add solution to problem
     */
    public function test_add_solution_to_problem() {
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        $journey_id = $this->journey_manager->create( array(
            'service_area_id' => $service_area_id,
        ) );
        
        $problem_id = $this->journey_manager->add_problem( $journey_id, array(
            'title' => 'Test Problem',
        ) );
        
        // Add solution
        $solution_args = array(
            'title'       => 'Cloud Migration Strategy',
            'description' => 'Migrate to AWS infrastructure',
        );
        
        $solution_id = $this->journey_manager->add_solution( $journey_id, $problem_id, $solution_args );
        
        $this->assertIsInt( $solution_id );
        $this->assertGreaterThan( 0, $solution_id );
        
        // Verify solution was added
        $journey = $this->journey_manager->get( $journey_id );
        $this->assertCount( 1, $journey['solutions'] );
        $this->assertEquals( $solution_args['title'], $journey['solutions'][0]['title'] );
        $this->assertEquals( $problem_id, $journey['solutions'][0]['problem_id'] );
    }

    /**
     * Test: Problem can only have one solution (1:1 relationship)
     */
    public function test_problem_one_solution_limit() {
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        $journey_id = $this->journey_manager->create( array(
            'service_area_id' => $service_area_id,
        ) );
        
        $problem_id = $this->journey_manager->add_problem( $journey_id, array(
            'title' => 'Test Problem',
        ) );
        
        // Add first solution (should succeed)
        $solution_id_1 = $this->journey_manager->add_solution( $journey_id, $problem_id, array(
            'title' => 'Solution 1',
        ) );
        
        $this->assertIsInt( $solution_id_1 );
        
        // Try to add second solution (should fail)
        $solution_id_2 = $this->journey_manager->add_solution( $journey_id, $problem_id, array(
            'title' => 'Solution 2',
        ) );
        
        $this->assertInstanceOf( WP_Error::class, $solution_id_2 );
        $this->assertEquals( 'solution_exists', $solution_id_2->get_error_code() );
    }

    /**
     * Test: Add offer to solution
     */
    public function test_add_offer_to_solution() {
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        $journey_id = $this->journey_manager->create( array(
            'service_area_id' => $service_area_id,
        ) );
        
        $problem_id = $this->journey_manager->add_problem( $journey_id, array(
            'title' => 'Test Problem',
        ) );
        
        $solution_id = $this->journey_manager->add_solution( $journey_id, $problem_id, array(
            'title' => 'Test Solution',
        ) );
        
        // Add offer
        $offer_args = array(
            'title'       => 'Free Consultation',
            'url'         => 'https://example.com/consultation',
            'description' => '30-minute free consultation',
        );
        
        $offer_id = $this->journey_manager->add_offer( $journey_id, $solution_id, $offer_args );
        
        $this->assertIsInt( $offer_id );
        $this->assertGreaterThan( 0, $offer_id );
        
        // Verify offer was added
        $journey = $this->journey_manager->get( $journey_id );
        $this->assertCount( 1, $journey['offers'] );
        $this->assertEquals( $offer_args['title'], $journey['offers'][0]['title'] );
        $this->assertEquals( $offer_args['url'], $journey['offers'][0]['url'] );
    }

    /**
     * Test: Add brain content (URL)
     */
    public function test_add_brain_content_url() {
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        $content_args = array(
            'type'  => 'url',
            'value' => 'https://example.com/cloud-guide',
            'title' => 'Cloud Migration Guide',
        );
        
        $content_id = $this->brain_content_manager->add_content( $service_area_id, $content_args );
        
        $this->assertIsInt( $content_id );
        $this->assertGreaterThan( 0, $content_id );
        
        // Verify content was added
        $content_items = $this->brain_content_manager->get_by_service_area( $service_area_id );
        $this->assertCount( 1, $content_items );
        $this->assertEquals( $content_args['type'], $content_items[0]['type'] );
        $this->assertEquals( $content_args['value'], $content_items[0]['value'] );
    }

    /**
     * Test: Add brain content (text)
     */
    public function test_add_brain_content_text() {
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        $content_args = array(
            'type'  => 'text',
            'value' => 'This is some brain content text that will be used for AI generation.',
        );
        
        $content_id = $this->brain_content_manager->add_content( $service_area_id, $content_args );
        
        $this->assertIsInt( $content_id );
        
        // Verify content
        $content_items = $this->brain_content_manager->get_by_service_area( $service_area_id );
        $this->assertCount( 1, $content_items );
        $this->assertEquals( 'text', $content_items[0]['type'] );
    }

    /**
     * Test: Invalid URL for brain content fails
     */
    public function test_invalid_url_brain_content_fails() {
        $service_area_id = $this->service_area_manager->create( array(
            'title' => 'Test Service Area',
        ) );
        
        $result = $this->brain_content_manager->add_content( $service_area_id, array(
            'type'  => 'url',
            'value' => 'not-a-valid-url',
        ) );
        
        $this->assertInstanceOf( WP_Error::class, $result );
        $this->assertEquals( 'invalid_url', $result->get_error_code() );
    }

    /**
     * Test: Complete journey circle workflow
     */
    public function test_complete_journey_circle_workflow() {
        // 1. Create service area
        $service_area_id = $this->service_area_manager->create( array(
            'title'       => 'Cloud Migration Services',
            'description' => 'Complete cloud migration solution',
            'client_id'   => 789,
        ) );
        
        $this->assertIsInt( $service_area_id );
        
        // 2. Add brain content
        $this->brain_content_manager->add_content( $service_area_id, array(
            'type'  => 'url',
            'value' => 'https://example.com/cloud-guide',
        ) );
        
        // 3. Create journey circle
        $journey_id = $this->journey_manager->create( array(
            'service_area_id' => $service_area_id,
            'industries'      => array( 101, 102, 103 ),
        ) );
        
        $this->assertIsInt( $journey_id );
        
        // 4. Add 5 problems
        $problem_ids = array();
        for ( $i = 1; $i <= 5; $i++ ) {
            $problem_ids[] = $this->journey_manager->add_problem( $journey_id, array(
                'title'      => "Problem $i",
                'is_primary' => ( $i === 1 ),
            ) );
        }
        
        $this->assertCount( 5, $problem_ids );
        
        // 5. Add 5 solutions (one per problem)
        $solution_ids = array();
        foreach ( $problem_ids as $problem_id ) {
            $solution_ids[] = $this->journey_manager->add_solution( $journey_id, $problem_id, array(
                'title' => 'Solution for problem ' . $problem_id,
            ) );
        }
        
        $this->assertCount( 5, $solution_ids );
        
        // 6. Add offers to each solution
        foreach ( $solution_ids as $solution_id ) {
            $this->journey_manager->add_offer( $journey_id, $solution_id, array(
                'title' => 'Offer for solution ' . $solution_id,
                'url'   => 'https://example.com/offer-' . $solution_id,
            ) );
        }
        
        // 7. Verify complete journey circle
        $journey = $this->journey_manager->get( $journey_id );
        
        $this->assertCount( 5, $journey['problems'] );
        $this->assertCount( 5, $journey['solutions'] );
        $this->assertCount( 5, $journey['offers'] );
        $this->assertEquals( $service_area_id, $journey['service_area_id'] );
        $this->assertNotEmpty( $journey['primary_problem_id'] );
    }
}
