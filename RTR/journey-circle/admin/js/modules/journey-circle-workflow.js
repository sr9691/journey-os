/**
 * Journey Circle Workflow State Machine
 * 
 * Manages the 11-step workflow including:
 * - Step navigation
 * - State persistence (localStorage + API)
 * - Validation
 * - Progress tracking
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0
 */

(function($) {
    'use strict';

    /**
     * Journey Circle Workflow Manager
     */
    class JourneyCircleWorkflow {
        constructor(config) {
            this.config = config;
            this.currentStep = 1;
            this.totalSteps = 11;
            this.state = this.loadState();
            this.autoSaveInterval = null;
            
            this.init();
        }

        /**
         * Initialize workflow
         */
        init() {
            this.bindEvents();
            this.restoreState();
            this.startAutoSave();
            this.updateUI();
            
            console.log('Journey Circle Workflow initialized', this.state);
        }

        /**
         * Bind event handlers
         */
        bindEvents() {
            // Navigation buttons
            $('.jc-next-btn').on('click', () => this.goToNextStep());
            $('.jc-prev-btn').on('click', () => this.goToPreviousStep());
            $('.jc-return-btn').on('click', () => this.returnToCampaignBuilder());
            
            // Progress step clicks
            $('.jc-progress-step').on('click', (e) => {
                const step = $(e.currentTarget).data('step');
                if (step <= this.getMaxAccessibleStep()) {
                    this.goToStep(step);
                }
            });
            
            // Browser back button / page unload
            $(window).on('beforeunload', () => {
                this.saveState();
            });
        }

        /**
         * Navigate to specific step
         */
        goToStep(stepNumber) {
            if (stepNumber < 1 || stepNumber > this.totalSteps) {
                return;
            }

            // Validate current step before proceeding
            if (stepNumber > this.currentStep && !this.validateCurrentStep()) {
                return;
            }

            // Hide current step
            $(`#jc-step-${this.currentStep}`).fadeOut(200, () => {
                // Update current step
                this.currentStep = stepNumber;
                
                // Show new step
                $(`#jc-step-${this.currentStep}`).fadeIn(200);
                
                // Update UI
                this.updateUI();
                
                // Scroll to top
                $('.jc-main-content').animate({ scrollTop: 0 }, 300);
                
                // Trigger step change event
                $(document).trigger('jc:stepChanged', [this.currentStep]);
                
                // Save state
                this.saveState();
            });
        }

        /**
         * Go to next step
         */
        goToNextStep() {
            if (this.currentStep < this.totalSteps && this.validateCurrentStep()) {
                this.goToStep(this.currentStep + 1);
            }
        }

        /**
         * Go to previous step
         */
        goToPreviousStep() {
            if (this.currentStep > 1) {
                this.goToStep(this.currentStep - 1);
            }
        }

        /**
         * Validate current step
         */
        validateCurrentStep() {
            let isValid = true;
            let errorMessage = '';

            switch (this.currentStep) {
                case 1: // Brain Content
                    if (!this.state.brainContent || this.state.brainContent.length === 0) {
                        isValid = false;
                        errorMessage = 'Please add at least one resource (URL, text, or file) before proceeding.';
                    }
                    break;

                case 2: // Service Area
                    if (!this.state.serviceAreaId) {
                        isValid = false;
                        errorMessage = 'Please select or create a service area before proceeding.';
                    }
                    break;

                case 3: // Existing Assets (optional)
                    // This step is optional, always valid
                    isValid = true;
                    break;

                // Add validation for other steps as they're implemented
            }

            if (!isValid) {
                this.showNotification(errorMessage, 'error');
            }

            return isValid;
        }

        /**
         * Get maximum accessible step based on completed steps
         */
        getMaxAccessibleStep() {
            // Allow navigation back to any previous step
            // But only forward if current step is valid
            let maxStep = 1;
            
            if (this.state.brainContent && this.state.brainContent.length > 0) {
                maxStep = 2;
            }
            if (this.state.serviceAreaId) {
                maxStep = 3;
            }
            // Add more conditions as steps are implemented
            
            return Math.max(maxStep, this.currentStep);
        }

        /**
         * Update UI elements
         */
        updateUI() {
            // Update progress indicator
            this.updateProgressIndicator();
            
            // Update step indicator
            $('.jc-current-step').text(this.currentStep);
            
            // Update navigation buttons
            this.updateNavigationButtons();
            
            // Update progress bar
            const progressPercent = ((this.currentStep - 1) / (this.totalSteps - 1)) * 100;
            $('.jc-progress-fill').css('width', `${progressPercent}%`);
        }

        /**
         * Update progress step indicator
         */
        updateProgressIndicator() {
            $('.jc-progress-step').each((index, element) => {
                const $step = $(element);
                const step = $step.data('step');
                
                $step.removeClass('active completed accessible');
                
                if (step === this.currentStep) {
                    $step.addClass('active');
                } else if (step < this.currentStep) {
                    $step.addClass('completed');
                } else if (step <= this.getMaxAccessibleStep()) {
                    $step.addClass('accessible');
                }
            });
        }

        /**
         * Update navigation buttons
         */
        updateNavigationButtons() {
            // Previous button
            if (this.currentStep === 1) {
                $('.jc-prev-btn').prop('disabled', true);
            } else {
                $('.jc-prev-btn').prop('disabled', false);
            }

            // Next button
            const $nextBtn = $('.jc-next-btn');
            if (this.currentStep === this.totalSteps) {
                $nextBtn.html('<i class="fas fa-check"></i> Complete Journey');
                $nextBtn.removeClass('button-primary').addClass('button-success');
            } else {
                $nextBtn.html('Next <i class="fas fa-arrow-right"></i>');
                $nextBtn.removeClass('button-success').addClass('button-primary');
            }
        }

        /**
         * Load state from localStorage
         */
        loadState() {
            const stateKey = `dr_journey_circle_${this.config.clientId}`;
            const savedState = localStorage.getItem(stateKey);
            
            if (savedState) {
                try {
                    return JSON.parse(savedState);
                } catch (e) {
                    console.error('Error parsing saved state:', e);
                }
            }
            
            // Default state
            return {
                clientId: this.config.clientId,
                serviceAreaId: this.config.serviceAreaId || null,
                currentStep: 1,
                brainContent: [],
                existingAssets: [],
                industries: [],
                primaryProblemId: null,
                problems: [],
                solutions: [],
                offers: [],
                assets: {},
                lastSaved: null
            };
        }

        /**
         * Save state to localStorage
         */
        saveState() {
            const stateKey = `dr_journey_circle_${this.config.clientId}`;
            this.state.currentStep = this.currentStep;
            this.state.lastSaved = new Date().toISOString();
            
            try {
                localStorage.setItem(stateKey, JSON.stringify(this.state));
                console.log('State saved to localStorage', this.state);
            } catch (e) {
                console.error('Error saving state:', e);
            }
        }

        /**
         * Restore state from localStorage
         */
        restoreState() {
            if (this.state.currentStep && this.state.currentStep !== this.currentStep) {
                this.currentStep = this.state.currentStep;
                $(`#jc-step-${this.currentStep}`).show();
                $('#jc-step-1').hide();
            }
            
            // Trigger restore events for each module
            $(document).trigger('jc:restoreState', [this.state]);
        }

        /**
         * Sync state with API
         */
        async syncStateToAPI() {
            if (!this.state.serviceAreaId) {
                return; // Can't sync without service area
            }

            try {
                const response = await fetch(`${this.config.restUrl}/journey-circles/${this.state.serviceAreaId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': this.config.restNonce
                    },
                    body: JSON.stringify({
                        brain_content: this.state.brainContent,
                        industries: this.state.industries,
                        primary_problem_id: this.state.primaryProblemId
                    })
                });

                if (!response.ok) {
                    throw new Error('API sync failed');
                }

                console.log('State synced to API');
            } catch (error) {
                console.error('Error syncing state to API:', error);
            }
        }

        /**
         * Start auto-save interval
         */
        startAutoSave() {
            // Save every 30 seconds
            this.autoSaveInterval = setInterval(() => {
                this.saveState();
                this.syncStateToAPI();
            }, 30000);
        }

        /**
         * Stop auto-save interval
         */
        stopAutoSave() {
            if (this.autoSaveInterval) {
                clearInterval(this.autoSaveInterval);
                this.autoSaveInterval = null;
            }
        }

        /**
         * Return to Campaign Builder
         */
        returnToCampaignBuilder() {
            // Save state before leaving
            this.saveState();
            this.stopAutoSave();
            
            // Check if journey is complete
            const isComplete = this.isJourneyComplete();
            
            if (isComplete) {
                // Store completion data in sessionStorage
                sessionStorage.setItem('dr_journey_completed', JSON.stringify({
                    success: true,
                    clientId: this.state.clientId,
                    serviceAreaId: this.state.serviceAreaId,
                    circleComplete: true
                }));
            }
            
            // Navigate back
            window.location.href = this.config.campaignBuilderUrl;
        }

        /**
         * Check if journey is complete
         */
        isJourneyComplete() {
            return this.state.problems.length === 5 &&
                   this.state.solutions.length === 5 &&
                   this.state.offers.length > 0;
        }

        /**
         * Show notification
         */
        showNotification(message, type = 'info') {
            const $notification = $('<div>')
                .addClass(`jc-notification jc-notification-${type}`)
                .html(`
                    <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
                    <span>${message}</span>
                    <button type="button" class="jc-notification-close">
                        <i class="fas fa-times"></i>
                    </button>
                `)
                .appendTo('.dr-journey-circle-creator');

            $notification.find('.jc-notification-close').on('click', function() {
                $(this).closest('.jc-notification').fadeOut(200, function() {
                    $(this).remove();
                });
            });

            setTimeout(() => {
                $notification.fadeOut(200, function() {
                    $(this).remove();
                });
            }, 5000);
        }

        /**
         * Update state property
         */
        updateState(key, value) {
            this.state[key] = value;
            this.saveState();
        }

        /**
         * Get state property
         */
        getState(key) {
            return this.state[key];
        }
    }

    // Initialize when document is ready
    $(document).ready(function() {
        if (typeof drJourneyCircleConfig !== 'undefined') {
            window.drJourneyCircle = new JourneyCircleWorkflow(drJourneyCircleConfig);
        }
    });

})(jQuery);
