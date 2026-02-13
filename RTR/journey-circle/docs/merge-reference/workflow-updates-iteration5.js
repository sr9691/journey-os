/**
 * Journey Circle Workflow Updates - Iteration 5
 * 
 * This file contains the additions to journey-circle-workflow.js
 * for Steps 4-6: Industry, Primary Problem, Problem Titles
 * 
 * Integration Instructions:
 * 1. Add these methods to the JourneyCircleWorkflow class
 * 2. Import ProblemSolutionManager in the workflow
 * 3. Initialize the manager in the constructor
 * 
 * @package DirectReach
 * @subpackage JourneyCircle
 * @since 2.0.0
 */

// ============================================================================
// ADD TO CONSTRUCTOR - after existing managers
// ============================================================================

/*
 * Add to constructor after line where serviceAreaManager is initialized:
 * 
 * // Initialize Problem/Solution Manager
 * this.problemSolutionManager = new ProblemSolutionManager(this, {
 *     apiBase: this.config.apiBase,
 *     nonce: this.config.nonce
 * });
 * 
 * // Load saved state into manager
 * const savedState = this.getState();
 * if (savedState) {
 *     this.problemSolutionManager.loadFromState(savedState);
 * }
 */


// ============================================================================
// UPDATED renderCurrentStep METHOD
// ============================================================================

/**
 * Updated renderCurrentStep method - ADD Step 4, 5, 6 cases
 * Replace the existing renderCurrentStep method with this
 */
renderCurrentStep() {
    const container = document.getElementById('jc-step-content');
    if (!container) return;

    // Hide all step contents first
    container.querySelectorAll('.jc-step-container').forEach(el => {
        el.style.display = 'none';
    });

    // Show current step
    const currentStepEl = document.getElementById(`step-${this.currentStep}-content`);
    if (currentStepEl) {
        currentStepEl.style.display = 'block';
    }

    // Initialize step-specific functionality
    switch (this.currentStep) {
        case 1:
            this.initStep1();
            break;
        case 2:
            this.initStep2();
            break;
        case 3:
            this.initStep3();
            break;
        case 4:
            this.initStep4();
            break;
        case 5:
            this.initStep5();
            break;
        case 6:
            this.initStep6();
            break;
        // Steps 7-11 will be added in future iterations
    }

    // Update navigation buttons
    this.updateNavigationButtons();

    // Update progress indicator
    this.updateProgressIndicator();

    // Update canvas visualization
    this.updateCanvasVisualization();
}


// ============================================================================
// STEP 4, 5, 6 INITIALIZATION METHODS
// ============================================================================

/**
 * Initialize Step 4: Industry Selection
 */
initStep4() {
    // Render step content if not already rendered
    this.ensureStepContentExists(4, this.getStep4HTML());

    // Initialize the problem/solution manager for this step
    if (this.problemSolutionManager) {
        this.problemSolutionManager.initStep4();
    }
}

/**
 * Initialize Step 5: Primary Problem Selection
 */
initStep5() {
    // Ensure step 4 was completed
    const state = this.getState();
    if (!state.industries || state.industries.length === 0) {
        this.showNotification('Please complete Step 4 first.', 'warning');
        this.goToStep(4);
        return;
    }

    // Render step content if not already rendered
    this.ensureStepContentExists(5, this.getStep5HTML());

    // Initialize the problem/solution manager for this step
    if (this.problemSolutionManager) {
        this.problemSolutionManager.initStep5();
    }
}

/**
 * Initialize Step 6: Problem Title Selection
 */
initStep6() {
    // Ensure step 5 was completed
    const state = this.getState();
    if (!state.primaryProblemId) {
        this.showNotification('Please select a primary problem first.', 'warning');
        this.goToStep(5);
        return;
    }

    // Render step content if not already rendered
    this.ensureStepContentExists(6, this.getStep6HTML());

    // Initialize the problem/solution manager for this step
    if (this.problemSolutionManager) {
        this.problemSolutionManager.initStep6();
    }
}


// ============================================================================
// STEP HTML TEMPLATES
// ============================================================================

/**
 * Get Step 4 HTML content
 */
getStep4HTML() {
    return `
        <div id="step-4-content" class="jc-step-container">
            <!-- Content will be rendered by ProblemSolutionManager -->
        </div>
    `;
}

/**
 * Get Step 5 HTML content
 */
getStep5HTML() {
    return `
        <div id="step-5-content" class="jc-step-container">
            <!-- Content will be rendered by ProblemSolutionManager -->
        </div>
    `;
}

/**
 * Get Step 6 HTML content
 */
getStep6HTML() {
    return `
        <div id="step-6-content" class="jc-step-container">
            <!-- Content will be rendered by ProblemSolutionManager -->
        </div>
    `;
}

/**
 * Ensure step content container exists
 */
ensureStepContentExists(step, html) {
    const container = document.getElementById('jc-step-content');
    if (!container) return;

    let stepContent = document.getElementById(`step-${step}-content`);
    if (!stepContent) {
        const wrapper = document.createElement('div');
        wrapper.innerHTML = html;
        container.appendChild(wrapper.firstElementChild);
    }
}


// ============================================================================
// UPDATED VALIDATION METHOD
// ============================================================================

/**
 * Updated validateCurrentStep method - ADD Step 4, 5, 6 cases
 * Replace the existing validateCurrentStep method with this
 */
validateCurrentStep() {
    switch (this.currentStep) {
        case 1:
            return this.validateStep1();
        case 2:
            return this.validateStep2();
        case 3:
            return this.validateStep3();
        case 4:
            return this.validateStep4();
        case 5:
            return this.validateStep5();
        case 6:
            return this.validateStep6();
        default:
            return { valid: true };
    }
}

/**
 * Validate Step 4: Industry Selection
 */
validateStep4() {
    if (this.problemSolutionManager) {
        return this.problemSolutionManager.validateStep4();
    }
    return { valid: true };
}

/**
 * Validate Step 5: Primary Problem Selection
 */
validateStep5() {
    if (this.problemSolutionManager) {
        return this.problemSolutionManager.validateStep5();
    }
    return { valid: true };
}

/**
 * Validate Step 6: Problem Title Selection
 */
validateStep6() {
    if (this.problemSolutionManager) {
        const result = this.problemSolutionManager.validateStep6();
        
        // If validation passes, save problems to database
        if (result.valid) {
            this.saveProblemsToDatabase();
        }
        
        return result;
    }
    return { valid: true };
}

/**
 * Save problems to database
 */
async saveProblemsToDatabase() {
    if (this.problemSolutionManager) {
        try {
            await this.problemSolutionManager.saveProblemsToDatabase();
            this.showNotification('Problems saved successfully!', 'success');
        } catch (error) {
            console.error('Error saving problems:', error);
            // Don't block navigation, just log the error
        }
    }
}


// ============================================================================
// UPDATED CANVAS VISUALIZATION
// ============================================================================

/**
 * Updated updateCanvasVisualization method
 * Add call to update problems on canvas
 */
updateCanvasVisualization() {
    if (!this.renderer) return;

    const state = this.getState();

    // Update problems on canvas (Steps 4-6)
    if (state.selectedProblems && state.selectedProblems.length > 0) {
        this.renderer.updateProblems(state.selectedProblems);
    }

    // Redraw the canvas
    this.renderer.draw();
}


// ============================================================================
// UPDATED STATE MANAGEMENT
// ============================================================================

/**
 * Updated getState method - ensure new fields are included
 * Add these fields to the default state
 */
getDefaultState() {
    return {
        clientId: null,
        serviceAreaId: null,
        journeyCircleId: null,
        currentStep: 1,
        // Step 1: Brain Content
        brainContent: [],
        // Step 2: Service Area
        serviceArea: null,
        // Step 3: Existing Assets
        existingAssets: [],
        // Step 4: Industries (NEW)
        industries: [],
        // Step 5: Primary Problem (NEW)
        primaryProblemId: null,
        primaryProblem: null,
        // Step 6: Selected Problems (NEW)
        selectedProblems: [],
        // Steps 7-11 will be added in future iterations
        solutions: [],
        offers: [],
        assets: {},
        // Metadata
        lastSaved: null,
        status: 'incomplete'
    };
}


// ============================================================================
// UPDATED STEP DEFINITIONS
// ============================================================================

/**
 * Step definitions array - update with accurate info
 */
const STEP_DEFINITIONS = [
    {
        number: 1,
        title: 'Brain Content',
        shortTitle: 'Brain',
        description: 'Add URLs, text, and files',
        icon: 'fa-brain'
    },
    {
        number: 2,
        title: 'Service Area',
        shortTitle: 'Service',
        description: 'Select or create a service area',
        icon: 'fa-bullseye'
    },
    {
        number: 3,
        title: 'Assets',
        shortTitle: 'Assets',
        description: 'Upload existing assets',
        icon: 'fa-file-upload'
    },
    {
        number: 4,
        title: 'Industries',
        shortTitle: 'Industry',
        description: 'Select target industries',
        icon: 'fa-industry'
    },
    {
        number: 5,
        title: 'Primary Problem',
        shortTitle: 'Primary',
        description: 'Designate the main problem',
        icon: 'fa-star'
    },
    {
        number: 6,
        title: 'Problem Titles',
        shortTitle: 'Problems',
        description: 'Select 5 problem titles',
        icon: 'fa-exclamation-circle'
    },
    {
        number: 7,
        title: 'Solution Titles',
        shortTitle: 'Solutions',
        description: 'Select solutions for problems',
        icon: 'fa-lightbulb'
    },
    {
        number: 8,
        title: 'Offer Mapping',
        shortTitle: 'Offers',
        description: 'Map offers to solutions',
        icon: 'fa-gift'
    },
    {
        number: 9,
        title: 'Content Creation',
        shortTitle: 'Content',
        description: 'Create assets with AI',
        icon: 'fa-magic'
    },
    {
        number: 10,
        title: 'Export & Link',
        shortTitle: 'Export',
        description: 'Link published content',
        icon: 'fa-link'
    },
    {
        number: 11,
        title: 'Complete',
        shortTitle: 'Done',
        description: 'Finish and repeat',
        icon: 'fa-check-circle'
    }
];
