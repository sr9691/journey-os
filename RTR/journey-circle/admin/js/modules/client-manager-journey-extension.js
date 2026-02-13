/**
 * Client Manager Extensions for Journey Circle Integration
 * 
 * Iteration 10: Campaign Builder Integration
 * 
 * Extends the existing client-manager.js to:
 * - Handle return from Journey Circle with success notification
 * - Display journey status badges on client cards
 * - Check and display sessionStorage completion data
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

/**
 * Journey integration module for Campaign Builder
 */
const JourneyIntegration = {
    /**
     * Initialize journey integration
     * Call this on Campaign Builder page load
     */
    init() {
        this.checkJourneyCompletion();
        this.enhanceClientCards();
    },

    /**
     * Check for journey completion data in sessionStorage
     */
    checkJourneyCompletion() {
        // Check URL parameter first
        const urlParams = new URLSearchParams(window.location.search);
        const journeySuccess = urlParams.get('journey_success');

        // Check sessionStorage
        const completionData = sessionStorage.getItem('dr_journey_completed');

        if (journeySuccess === '1' && completionData) {
            try {
                const data = JSON.parse(completionData);
                if (data.success) {
                    this.showSuccessBanner(data);
                    this.updateClientCard(data);
                    
                    // Clear sessionStorage
                    sessionStorage.removeItem('dr_journey_completed');
                    
                    // Clean up URL
                    this.cleanupUrl();
                }
            } catch (error) {
                console.error('Failed to parse journey completion data:', error);
            }
        }
    },

    /**
     * Show success banner at top of page
     * 
     * @param {Object} data Completion data
     */
    showSuccessBanner(data) {
        const banner = document.createElement('div');
        banner.className = 'dr-journey-success-banner';
        banner.innerHTML = `
            <i class="fas fa-trophy"></i>
            <div class="banner-content">
                <h4>Journey Circle Complete!</h4>
                <p>
                    ${data.serviceAreaName ? `"${this.escapeHtml(data.serviceAreaName)}" ` : ''}
                    completed with ${data.problemCount || 5} problems, 
                    ${data.solutionCount || 5} solutions, 
                    and ${data.assetCount || 0} content assets.
                </p>
            </div>
            <button class="close-banner" title="Dismiss">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Insert at top of main content
        const mainContent = document.querySelector('.dr-campaign-builder-wrap') || 
                           document.querySelector('.wrap') ||
                           document.querySelector('#wpbody-content');
        
        if (mainContent) {
            mainContent.insertBefore(banner, mainContent.firstChild);
        }

        // Close button handler
        banner.querySelector('.close-banner').addEventListener('click', () => {
            banner.classList.add('fade-out');
            setTimeout(() => banner.remove(), 300);
        });

        // Auto-dismiss after 10 seconds
        setTimeout(() => {
            if (banner.parentNode) {
                banner.classList.add('fade-out');
                setTimeout(() => banner.remove(), 300);
            }
        }, 10000);
    },

    /**
     * Update client card with journey badge
     * 
     * @param {Object} data Completion data
     */
    updateClientCard(data) {
        if (!data.clientId) return;

        const clientCard = document.querySelector(`.client-card[data-client-id="${data.clientId}"]`);
        if (!clientCard) return;

        // Add or update badge
        this.addJourneyBadge(clientCard, 'complete');
    },

    /**
     * Enhance all client cards with journey status
     * Fetches journey status from API if needed
     */
    async enhanceClientCards() {
        const clientCards = document.querySelectorAll('.client-card');
        
        if (clientCards.length === 0) return;

        // Collect client IDs
        const clientIds = Array.from(clientCards).map(card => {
            return parseInt(card.dataset.clientId, 10);
        }).filter(id => !isNaN(id));

        if (clientIds.length === 0) return;

        try {
            // Fetch journey statuses for all clients
            const statuses = await this.fetchJourneyStatuses(clientIds);
            
            // Apply badges to cards
            clientCards.forEach(card => {
                const clientId = parseInt(card.dataset.clientId, 10);
                if (statuses[clientId]) {
                    this.addJourneyBadge(card, statuses[clientId]);
                }
            });
        } catch (error) {
            console.warn('Failed to fetch journey statuses:', error);
        }
    },

    /**
     * Fetch journey statuses for multiple clients
     * 
     * @param {Array<number>} clientIds Array of client IDs
     * @returns {Promise<Object>} Map of clientId -> status
     */
    async fetchJourneyStatuses(clientIds) {
        // This endpoint would need to be implemented in the REST API
        // For now, we'll return an empty object and rely on individual card data
        
        const nonce = window.drCampaignBuilder?.nonce || 
                     document.querySelector('[data-nonce]')?.dataset.nonce;
        
        if (!nonce) {
            return {};
        }

        try {
            const response = await fetch(
                `/wp-json/directreach/v2/clients/journey-statuses?client_ids=${clientIds.join(',')}`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': nonce,
                    },
                }
            );

            if (!response.ok) {
                return {};
            }

            return await response.json();
        } catch (error) {
            return {};
        }
    },

    /**
     * Add journey badge to a client card
     * 
     * @param {HTMLElement} card Client card element
     * @param {string} status Journey status (complete, in-progress, incomplete)
     */
    addJourneyBadge(card, status) {
        // Remove existing badge if any
        const existingBadge = card.querySelector('.jc-journey-badge');
        if (existingBadge) {
            existingBadge.remove();
        }

        // Don't add badge for incomplete/no journey
        if (!status || status === 'none') {
            return;
        }

        // Create badge
        const badge = document.createElement('span');
        badge.className = `jc-journey-badge ${status}`;

        switch (status) {
            case 'complete':
                badge.innerHTML = '<i class="fas fa-check-circle"></i> Journey Complete';
                break;
            case 'in-progress':
            case 'incomplete':
                badge.innerHTML = '<i class="fas fa-spinner"></i> Journey In Progress';
                break;
            case 'active':
                badge.innerHTML = '<i class="fas fa-circle"></i> Journey Active';
                break;
            default:
                return; // Don't add badge for unknown status
        }

        // Find header or title element to append to
        const header = card.querySelector('.client-card-header') ||
                      card.querySelector('.client-name')?.parentElement ||
                      card.querySelector('h3')?.parentElement;
        
        if (header) {
            header.appendChild(badge);
        }
    },

    /**
     * Clean up URL by removing journey_success parameter
     */
    cleanupUrl() {
        const url = new URL(window.location.href);
        url.searchParams.delete('journey_success');
        window.history.replaceState({}, '', url.toString());
    },

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
};

/**
 * Extension to add to existing ClientManager class
 * 
 * Add this code to client-manager.js in the handleEvents or init method:
 * 
 * ```javascript
 * // After page load, initialize journey integration
 * if (typeof JourneyIntegration !== 'undefined') {
 *     JourneyIntegration.init();
 * }
 * ```
 */

/**
 * Client card render extension
 * 
 * Modify the renderClientCard method in client-manager.js to include:
 * 
 * ```javascript
 * // Add journey circle button to card actions
 * <button class="btn btn-sm btn-info journey-circle-btn" 
 *         title="Create Journey Circle">
 *     <i class="fas fa-circle-notch"></i> Journey Circle
 * </button>
 * ```
 * 
 * And handle the click:
 * 
 * ```javascript
 * // In event delegation handler
 * const journeyBtn = e.target.closest('.journey-circle-btn');
 * if (journeyBtn) {
 *     e.preventDefault();
 *     e.stopPropagation();
 *     const card = journeyBtn.closest('.client-card');
 *     if (card) {
 *         const clientId = parseInt(card.dataset.clientId, 10);
 *         this.handleJourneyCircleClick(clientId);
 *     }
 *     return;
 * }
 * ```
 * 
 * And the navigation method:
 * 
 * ```javascript
 * handleJourneyCircleClick(clientId) {
 *     window.location.href = `${window.location.origin}/wp-admin/admin.php?page=dr-journey-circle&client_id=${clientId}`;
 * }
 * ```
 */

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the Campaign Builder page
    const isCampaignBuilder = document.querySelector('.dr-campaign-builder-wrap') ||
                             window.location.href.includes('page=dr-campaign-builder');
    
    if (isCampaignBuilder) {
        JourneyIntegration.init();
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JourneyIntegration;
}

// Attach to window
window.JourneyIntegration = JourneyIntegration;
