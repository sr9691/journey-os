/**
 * Journey Completion Module
 * 
 * Iteration 10: Step 11 - Repeat Workflow & Journey Completion
 * 
 * Handles:
 * - Displaying asset completion grid for problems and solutions
 * - Selecting next item for content creation
 * - Tracking overall completion progress
 * - Journey completion validation and celebration
 * - Return navigation to Campaign Builder
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

class JourneyCompletion {
    /**
     * Constructor
     * 
     * @param {Object} config Configuration object
     * @param {number} config.journeyCircleId Journey circle ID
     * @param {number} config.clientId Client ID
     * @param {number} config.serviceAreaId Service area ID
     * @param {string} config.serviceAreaName Service area name
     * @param {string} config.apiBase REST API base URL
     * @param {string} config.nonce WordPress nonce
     */
    constructor(config) {
        this.journeyCircleId = config.journeyCircleId;
        this.clientId = config.clientId;
        this.serviceAreaId = config.serviceAreaId;
        this.serviceAreaName = config.serviceAreaName;
        this.apiBase = config.apiBase || '/wp-json/directreach/v2';
        this.nonce = config.nonce;
        
        // Completion state
        this.completionStatus = null;
        this.selectedItem = null;
        
        // DOM references
        this.container = null;
        
        // Bind methods
        this.init = this.init.bind(this);
        this.render = this.render.bind(this);
        this.loadCompletionStatus = this.loadCompletionStatus.bind(this);
        this.handleItemSelect = this.handleItemSelect.bind(this);
        this.handleCreateContent = this.handleCreateContent.bind(this);
        this.handleCompleteJourney = this.handleCompleteJourney.bind(this);
        this.navigateToCampaignBuilder = this.navigateToCampaignBuilder.bind(this);
    }

    /**
     * Initialize the module
     * 
     * @param {HTMLElement} container Container element
     */
    async init(container) {
        this.container = container;
        
        try {
            await this.loadCompletionStatus();
            this.render();
            this.attachEventListeners();
        } catch (error) {
            console.error('Failed to initialize journey completion:', error);
            this.renderError(error.message);
        }
    }

    /**
     * Load completion status from API
     */
    async loadCompletionStatus() {
        const response = await fetch(
            `${this.apiBase}/journey-circles/${this.journeyCircleId}/completion-status`,
            {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-WP-Nonce': this.nonce,
                },
            }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to load completion status');
        }

        this.completionStatus = await response.json();
        return this.completionStatus;
    }

    /**
     * Render the completion UI
     */
    render() {
        if (!this.completionStatus) {
            this.container.innerHTML = '<div class="jc-loading">Loading completion status...</div>';
            return;
        }

        const { problems, solutions, completion_percentage, is_complete } = this.completionStatus;

        this.container.innerHTML = `
            <div class="jc-completion-wrapper">
                <!-- Progress Header -->
                <div class="jc-completion-header">
                    <h2>Journey Circle Progress</h2>
                    <div class="jc-progress-overview">
                        <div class="jc-progress-bar-wrapper">
                            <div class="jc-progress-bar">
                                <div class="jc-progress-fill" style="width: ${completion_percentage}%"></div>
                            </div>
                            <span class="jc-progress-text">${completion_percentage}% Complete</span>
                        </div>
                        <div class="jc-progress-stats">
                            <span class="jc-stat">
                                <i class="fas fa-exclamation-circle"></i>
                                Problems: ${problems.completed}/${problems.total}
                            </span>
                            <span class="jc-stat">
                                <i class="fas fa-lightbulb"></i>
                                Solutions: ${solutions.completed}/${solutions.total}
                            </span>
                        </div>
                    </div>
                </div>

                ${is_complete ? this.renderCompletionCelebration() : this.renderAssetGrid()}
            </div>
        `;
    }

    /**
     * Render the asset grid for selecting items
     */
    renderAssetGrid() {
        const { problems, solutions } = this.completionStatus;

        return `
            <div class="jc-asset-grid-section">
                <div class="jc-section-intro">
                    <h3>Select an Item to Create Content</h3>
                    <p>Choose a problem or solution that still needs content. Items with a green checkmark are complete.</p>
                </div>

                <!-- Problems Grid -->
                <div class="jc-grid-group">
                    <h4><i class="fas fa-exclamation-circle jc-icon-problem"></i> Problems (Outer Ring)</h4>
                    <div class="jc-item-grid">
                        ${problems.items.map(problem => this.renderGridItem(problem, 'problem')).join('')}
                    </div>
                </div>

                <!-- Solutions Grid -->
                <div class="jc-grid-group">
                    <h4><i class="fas fa-lightbulb jc-icon-solution"></i> Solutions (Middle Ring)</h4>
                    <div class="jc-item-grid">
                        ${solutions.items.map(solution => this.renderGridItem(solution, 'solution')).join('')}
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="jc-completion-actions">
                    <button class="btn btn-primary jc-create-content-btn" disabled>
                        <i class="fas fa-magic"></i> Create Content for Selected Item
                    </button>
                    ${this.canComplete() ? `
                        <button class="btn btn-success jc-complete-journey-btn">
                            <i class="fas fa-check-circle"></i> Complete Journey
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Render a single grid item (problem or solution)
     * 
     * @param {Object} item Problem or solution object
     * @param {string} type 'problem' or 'solution'
     */
    renderGridItem(item, type) {
        const isComplete = item.is_complete;
        const isPrimary = type === 'problem' && item.is_primary;
        const statusClass = isComplete ? 'complete' : 'pending';
        const statusIcon = isComplete ? 'fa-check-circle' : 'fa-circle';
        const statusText = isComplete ? 'Complete' : 'Needs Content';

        return `
            <div class="jc-grid-item ${statusClass} ${isPrimary ? 'primary' : ''}" 
                 data-type="${type}" 
                 data-id="${item.id}"
                 data-title="${this.escapeHtml(item.title)}">
                <div class="jc-item-header">
                    <span class="jc-item-position">${item.position + 1}</span>
                    ${isPrimary ? '<span class="jc-primary-badge">Primary</span>' : ''}
                    <span class="jc-item-status ${statusClass}">
                        <i class="fas ${statusIcon}"></i>
                    </span>
                </div>
                <div class="jc-item-title">${this.escapeHtml(item.title)}</div>
                <div class="jc-item-meta">
                    <span class="jc-status-text">${statusText}</span>
                    ${item.asset_count > 0 ? `<span class="jc-asset-count">${item.asset_count} asset(s)</span>` : ''}
                </div>
                ${item.asset_urls && item.asset_urls.length > 0 ? `
                    <div class="jc-item-urls">
                        ${item.asset_urls.map(url => `
                            <a href="${this.escapeHtml(url)}" target="_blank" class="jc-url-link" title="${this.escapeHtml(url)}">
                                <i class="fas fa-external-link-alt"></i>
                            </a>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Render completion celebration UI
     */
    renderCompletionCelebration() {
        const { problems, solutions, assets } = this.completionStatus;

        return `
            <div class="jc-celebration">
                <div class="jc-celebration-icon">
                    <i class="fas fa-trophy"></i>
                </div>
                <h2>🎉 Journey Circle Complete!</h2>
                <p>Congratulations! You've successfully created content for all problems and solutions.</p>
                
                <div class="jc-completion-summary">
                    <div class="jc-summary-stat">
                        <span class="jc-summary-number">${problems.completed}</span>
                        <span class="jc-summary-label">Problems</span>
                    </div>
                    <div class="jc-summary-stat">
                        <span class="jc-summary-number">${solutions.completed}</span>
                        <span class="jc-summary-label">Solutions</span>
                    </div>
                    <div class="jc-summary-stat">
                        <span class="jc-summary-number">${assets.total}</span>
                        <span class="jc-summary-label">Assets Created</span>
                    </div>
                </div>

                <div class="jc-completion-actions">
                    <button class="btn btn-success btn-lg jc-return-btn">
                        <i class="fas fa-arrow-left"></i> Return to Campaign Builder
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Check if journey can be marked as complete
     */
    canComplete() {
        if (!this.completionStatus) return false;
        const { problems, solutions } = this.completionStatus;
        return problems.completed >= 5 && solutions.completed >= 5;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Grid item selection
        this.container.querySelectorAll('.jc-grid-item').forEach(item => {
            item.addEventListener('click', (e) => this.handleItemSelect(e, item));
        });

        // Create content button
        const createBtn = this.container.querySelector('.jc-create-content-btn');
        if (createBtn) {
            createBtn.addEventListener('click', this.handleCreateContent);
        }

        // Complete journey button
        const completeBtn = this.container.querySelector('.jc-complete-journey-btn');
        if (completeBtn) {
            completeBtn.addEventListener('click', this.handleCompleteJourney);
        }

        // Return button
        const returnBtn = this.container.querySelector('.jc-return-btn');
        if (returnBtn) {
            returnBtn.addEventListener('click', this.navigateToCampaignBuilder);
        }
    }

    /**
     * Handle item selection
     * 
     * @param {Event} e Click event
     * @param {HTMLElement} item Grid item element
     */
    handleItemSelect(e, item) {
        // Remove previous selection
        this.container.querySelectorAll('.jc-grid-item.selected').forEach(el => {
            el.classList.remove('selected');
        });

        // Select this item
        item.classList.add('selected');
        
        this.selectedItem = {
            type: item.dataset.type,
            id: parseInt(item.dataset.id, 10),
            title: item.dataset.title,
        };

        // Enable create button
        const createBtn = this.container.querySelector('.jc-create-content-btn');
        if (createBtn) {
            createBtn.disabled = false;
        }

        // Dispatch selection event
        this.dispatchEvent('itemSelected', this.selectedItem);
    }

    /**
     * Handle create content button click
     */
    handleCreateContent() {
        if (!this.selectedItem) return;

        // Dispatch event to navigate to Step 9 with selected item
        this.dispatchEvent('createContent', {
            linkedToType: this.selectedItem.type,
            linkedToId: this.selectedItem.id,
            title: this.selectedItem.title,
        });
    }

    /**
     * Handle complete journey button click
     */
    async handleCompleteJourney() {
        if (!this.canComplete()) {
            this.showNotification('Cannot complete journey yet. Please create content for all items.', 'warning');
            return;
        }

        const completeBtn = this.container.querySelector('.jc-complete-journey-btn');
        if (completeBtn) {
            completeBtn.disabled = true;
            completeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Completing...';
        }

        try {
            const response = await fetch(
                `${this.apiBase}/journey-circles/${this.journeyCircleId}/complete`,
                {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': this.nonce,
                    },
                }
            );

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to complete journey');
            }

            const result = await response.json();

            // Store completion data in sessionStorage for Campaign Builder
            this.storeCompletionData(result.completion_data);

            // Re-render with celebration
            this.completionStatus.is_complete = true;
            this.completionStatus.current_status = 'complete';
            this.render();
            this.attachEventListeners();

            this.dispatchEvent('journeyComplete', result.completion_data);

        } catch (error) {
            console.error('Failed to complete journey:', error);
            this.showNotification(error.message, 'error');
            
            if (completeBtn) {
                completeBtn.disabled = false;
                completeBtn.innerHTML = '<i class="fas fa-check-circle"></i> Complete Journey';
            }
        }
    }

    /**
     * Store completion data in sessionStorage
     * 
     * @param {Object} completionData Completion data from API
     */
    storeCompletionData(completionData) {
        const storageData = {
            success: true,
            timestamp: new Date().toISOString(),
            ...completionData,
        };

        sessionStorage.setItem('dr_journey_completed', JSON.stringify(storageData));
    }

    /**
     * Navigate back to Campaign Builder
     */
    navigateToCampaignBuilder() {
        // Ensure completion data is stored
        if (this.completionStatus && this.completionStatus.is_complete) {
            this.storeCompletionData({
                clientId: this.clientId,
                serviceAreaId: this.serviceAreaId,
                serviceAreaName: this.serviceAreaName,
                circleComplete: true,
                problemCount: this.completionStatus.problems.completed,
                solutionCount: this.completionStatus.solutions.completed,
                assetCount: this.completionStatus.assets.total,
            });
        }

        // Navigate to Campaign Builder
        window.location.href = `${window.location.origin}/wp-admin/admin.php?page=dr-campaign-builder&journey_success=1`;
    }

    /**
     * Refresh completion status and re-render
     */
    async refresh() {
        try {
            await this.loadCompletionStatus();
            this.render();
            this.attachEventListeners();
        } catch (error) {
            console.error('Failed to refresh completion status:', error);
        }
    }

    /**
     * Render error state
     * 
     * @param {string} message Error message
     */
    renderError(message) {
        this.container.innerHTML = `
            <div class="jc-error">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${this.escapeHtml(message)}</p>
                <button class="btn btn-secondary jc-retry-btn">
                    <i class="fas fa-redo"></i> Retry
                </button>
            </div>
        `;

        this.container.querySelector('.jc-retry-btn')?.addEventListener('click', () => {
            this.init(this.container);
        });
    }

    /**
     * Show notification
     * 
     * @param {string} message Notification message
     * @param {string} type Notification type (success, error, warning, info)
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `jc-notification jc-notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'times' : type === 'warning' ? 'exclamation' : 'info'}-circle"></i>
            <span>${this.escapeHtml(message)}</span>
        `;

        this.container.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    /**
     * Dispatch custom event
     * 
     * @param {string} eventName Event name
     * @param {Object} detail Event detail
     */
    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(`journeyCompletion:${eventName}`, {
            detail,
            bubbles: true,
        });
        this.container.dispatchEvent(event);
    }

    /**
     * Escape HTML to prevent XSS
     * 
     * @param {string} text Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JourneyCompletion;
}

// Also attach to window for direct script usage
window.JourneyCompletion = JourneyCompletion;
