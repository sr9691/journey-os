/**
 * Service Area Manager - JavaScript Module
 * 
 * Handles service area selection and creation for Journey Circle
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0
 */

(function($) {
    'use strict';

    class ServiceAreaManager {
        constructor(workflow) {
            this.workflow = workflow;
            this.serviceAreas = [];
            this.selectedServiceAreaId = null;
            
            this.init();
        }

        /**
         * Initialize service area manager
         */
        init() {
            this.bindEvents();
            this.loadServiceAreas();
            
            console.log('Service Area Manager initialized');
        }

        /**
         * Bind event handlers
         */
        bindEvents() {
            // Create service area form
            $('#jc-create-service-area-form').on('submit', (e) => {
                e.preventDefault();
                this.createServiceArea();
            });

            // Select service area
            $(document).on('click', '.jc-service-area-card', (e) => {
                const serviceAreaId = $(e.currentTarget).data('id');
                this.selectServiceArea(serviceAreaId);
            });

            // Restore state
            $(document).on('jc:restoreState', (e, state) => {
                if (state.serviceAreaId) {
                    this.selectedServiceAreaId = state.serviceAreaId;
                    this.highlightSelectedServiceArea();
                }
            });

            // When entering step 2, load service areas
            $(document).on('jc:stepChanged', (e, step) => {
                if (step === 2) {
                    this.loadServiceAreas();
                }
            });
        }

        /**
         * Load service areas for current client
         */
        async loadServiceAreas() {
            const $list = $('#jc-service-area-list');
            
            try {
                // Show loading state
                $list.html(`
                    <div class="jc-loading-state">
                        <i class="fas fa-spinner fa-spin"></i>
                        <p>Loading service areas...</p>
                    </div>
                `);

                // Fetch service areas
                const response = await fetch(
                    `${this.workflow.config.restUrl}/service-areas?client_id=${this.workflow.config.clientId}`,
                    {
                        headers: {
                            'X-WP-Nonce': this.workflow.config.restNonce
                        }
                    }
                );

                if (!response.ok) {
                    throw new Error('Failed to load service areas');
                }

                this.serviceAreas = await response.json();
                this.renderServiceAreaList();

            } catch (error) {
                console.error('Error loading service areas:', error);
                $list.html(`
                    <div class="jc-error-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Error loading service areas. Please try again.</p>
                        <button type="button" class="button button-secondary jc-retry-load">
                            <i class="fas fa-redo"></i> Retry
                        </button>
                    </div>
                `);
                
                $('.jc-retry-load').on('click', () => this.loadServiceAreas());
            }
        }

        /**
         * Render service area list
         */
        renderServiceAreaList() {
            const $list = $('#jc-service-area-list');
            
            if (this.serviceAreas.length === 0) {
                $list.html(`
                    <div class="jc-empty-state">
                        <i class="fas fa-folder-open"></i>
                        <p>No service areas found</p>
                        <p class="jc-help-text">Create your first service area below to get started.</p>
                    </div>
                `);
                return;
            }

            $list.empty();
            
            this.serviceAreas.forEach(serviceArea => {
                const $card = this.createServiceAreaCard(serviceArea);
                $list.append($card);
            });

            // Highlight selected service area
            this.highlightSelectedServiceArea();
        }

        /**
         * Create service area card HTML
         */
        createServiceAreaCard(serviceArea) {
            const isSelected = serviceArea.id === this.selectedServiceAreaId;
            const hasJourneyCircle = serviceArea.has_journey_circle || false;
            
            return $(`
                <div class="jc-service-area-card ${isSelected ? 'selected' : ''}" 
                     data-id="${serviceArea.id}">
                    <div class="jc-sa-card-header">
                        <h4>${this.escapeHtml(serviceArea.name)}</h4>
                        ${hasJourneyCircle ? '<span class="jc-sa-badge">Has Journey Circle</span>' : ''}
                    </div>
                    ${serviceArea.description ? `
                        <div class="jc-sa-card-description">
                            ${this.escapeHtml(serviceArea.description)}
                        </div>
                    ` : ''}
                    <div class="jc-sa-card-footer">
                        <span class="jc-sa-status jc-sa-status-${serviceArea.status}">
                            ${this.formatStatus(serviceArea.status)}
                        </span>
                        <span class="jc-sa-date">
                            Created ${this.formatDate(serviceArea.created_at)}
                        </span>
                    </div>
                    ${isSelected ? `
                        <div class="jc-sa-selected-indicator">
                            <i class="fas fa-check-circle"></i> Selected
                        </div>
                    ` : ''}
                </div>
            `);
        }

        /**
         * Create new service area
         */
        async createServiceArea() {
            const $form = $('#jc-create-service-area-form');
            const $submitBtn = $('.jc-create-sa-btn');
            const originalBtnText = $submitBtn.html();
            
            // Get form data
            const name = $('#jc-sa-name').val().trim();
            const description = $('#jc-sa-description').val().trim();

            // Validate
            if (!name) {
                this.workflow.showNotification('Please enter a service area name', 'error');
                return;
            }

            try {
                // Show loading state
                $submitBtn.prop('disabled', true)
                    .html('<i class="fas fa-spinner fa-spin"></i> Creating...');

                // Create service area via API
                const response = await fetch(`${this.workflow.config.restUrl}/service-areas`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': this.workflow.config.restNonce
                    },
                    body: JSON.stringify({
                        client_id: this.workflow.config.clientId,
                        title: name,
                        description: description,
                        status: 'draft'
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.message || 'Failed to create service area');
                }

                const newServiceArea = await response.json();
                
                // Add to list
                this.serviceAreas.push(newServiceArea);
                this.renderServiceAreaList();
                
                // Clear form
                $form[0].reset();
                
                // Auto-select the new service area
                this.selectServiceArea(newServiceArea.id);
                
                this.workflow.showNotification('Service area created successfully', 'success');

            } catch (error) {
                console.error('Error creating service area:', error);
                this.workflow.showNotification(`Error: ${error.message}`, 'error');
            } finally {
                $submitBtn.prop('disabled', false).html(originalBtnText);
            }
        }

        /**
         * Select service area
         */
        async selectServiceArea(serviceAreaId) {
            this.selectedServiceAreaId = serviceAreaId;
            
            // Update UI
            this.highlightSelectedServiceArea();
            
            // Save to workflow state
            this.workflow.updateState('serviceAreaId', serviceAreaId);
            
            // Create or load journey circle for this service area
            await this.ensureJourneyCircle(serviceAreaId);
            
            this.workflow.showNotification('Service area selected', 'success');
        }

        /**
         * Ensure journey circle exists for service area
         */
        async ensureJourneyCircle(serviceAreaId) {
            try {
                // Check if journey circle exists
                const response = await fetch(
                    `${this.workflow.config.restUrl}/journey-circles?service_area_id=${serviceAreaId}`,
                    {
                        headers: {
                            'X-WP-Nonce': this.workflow.config.restNonce
                        }
                    }
                );

                if (response.ok) {
                    const journeyCircle = await response.json();
                    
                    if (journeyCircle && journeyCircle.id) {
                        // Journey circle exists, load its data
                        this.loadJourneyCircleData(journeyCircle);
                        return;
                    }
                }

                // Journey circle doesn't exist, create it
                await this.createJourneyCircle(serviceAreaId);

            } catch (error) {
                console.error('Error ensuring journey circle:', error);
            }
        }

        /**
         * Create journey circle for service area
         */
        async createJourneyCircle(serviceAreaId) {
            try {
                const response = await fetch(`${this.workflow.config.restUrl}/journey-circles`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': this.workflow.config.restNonce
                    },
                    body: JSON.stringify({
                        service_area_id: serviceAreaId,
                        industries: [],
                        brain_content: this.workflow.getState('brainContent') || [],
                        status: 'incomplete'
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to create journey circle');
                }

                const journeyCircle = await response.json();
                console.log('Journey circle created:', journeyCircle);

                // Store the journey circle ID in workflow state
                if (journeyCircle && journeyCircle.id) {
                    this.workflow.updateState('journeyCircleId', journeyCircle.id);
                    this.loadJourneyCircleData(journeyCircle);
                }

            } catch (error) {
                console.error('Error creating journey circle:', error);
                this.workflow.showNotification('Error creating journey circle', 'error');
            }
        }

        /**
         * Load journey circle data into state
         */
        loadJourneyCircleData(journeyCircle) {
            // Store journey circle ID
            this.workflow.updateState('journeyCircleId', journeyCircle.id);
            
            // Update workflow state with existing journey circle data
            if (journeyCircle.industries) {
                this.workflow.updateState('industries', journeyCircle.industries);
            }
            if (journeyCircle.primary_problem_id) {
                this.workflow.updateState('primaryProblemId', journeyCircle.primary_problem_id);
            }
            // Load problems, solutions, offers if they exist
            // This will be expanded as we implement more steps
            
            console.log('Journey circle data loaded:', journeyCircle);
        }

        /**
         * Highlight selected service area
         */
        highlightSelectedServiceArea() {
            $('.jc-service-area-card').removeClass('selected');
            $(`.jc-service-area-card[data-id="${this.selectedServiceAreaId}"]`).addClass('selected');
        }

        /**
         * Format status
         */
        formatStatus(status) {
            const statusMap = {
                'active': 'Active',
                'draft': 'Draft',
                'archived': 'Archived'
            };
            return statusMap[status] || status;
        }

        /**
         * Format date
         */
        formatDate(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) {
                return 'today';
            } else if (diffDays === 1) {
                return 'yesterday';
            } else if (diffDays < 7) {
                return `${diffDays} days ago`;
            } else if (diffDays < 30) {
                return `${Math.floor(diffDays / 7)} weeks ago`;
            } else {
                return date.toLocaleDateString();
            }
        }

        /**
         * Escape HTML
         */
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Initialize when workflow is ready
    $(document).ready(function() {
        if (window.drJourneyCircle) {
            window.drServiceAreaManager = new ServiceAreaManager(window.drJourneyCircle);
        }
    });

})(jQuery);