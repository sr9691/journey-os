/**
 * Asset Creator - Step 10 Extension
 * 
 * Iteration 10: Step 10 - Link Published Assets
 * 
 * This module extends the existing asset-creator.js to add the URL linking
 * phase after content is downloaded. Users paste the published URL of their
 * content asset back into the system.
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

class AssetUrlLinker {
    /**
     * Constructor
     * 
     * @param {Object} config Configuration object
     * @param {number} config.journeyCircleId Journey circle ID
     * @param {string} config.apiBase REST API base URL
     * @param {string} config.nonce WordPress nonce
     */
    constructor(config) {
        this.journeyCircleId = config.journeyCircleId;
        this.apiBase = config.apiBase || '/wp-json/directreach/v2';
        this.nonce = config.nonce;
        
        // Current asset being linked
        this.currentAsset = null;
        
        // DOM references
        this.container = null;
        
        // Bind methods
        this.init = this.init.bind(this);
        this.render = this.render.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
        this.handleSkip = this.handleSkip.bind(this);
        this.validateUrl = this.validateUrl.bind(this);
    }

    /**
     * Initialize the URL linker with an asset
     * 
     * @param {HTMLElement} container Container element
     * @param {Object} asset Asset object from Step 9
     */
    init(container, asset) {
        this.container = container;
        this.currentAsset = asset;
        this.render();
        this.attachEventListeners();
    }

    /**
     * Render the URL linking UI
     */
    render() {
        if (!this.currentAsset) {
            this.container.innerHTML = '<div class="jc-error">No asset to link</div>';
            return;
        }

        const { title, asset_type, linked_to_type, linked_to_id } = this.currentAsset;
        const assetTypeLabel = this.getAssetTypeLabel(asset_type);
        const linkedTypeLabel = linked_to_type === 'problem' ? 'Problem' : 'Solution';

        this.container.innerHTML = `
            <div class="jc-url-linker-wrapper">
                <div class="jc-step-header">
                    <div class="jc-step-badge">Step 10</div>
                    <h2>Link Your Published Content</h2>
                </div>

                <div class="jc-url-linker-intro">
                    <div class="jc-success-indicator">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <div class="jc-success-message">
                        <h3>Content Created Successfully!</h3>
                        <p>Your <strong>${assetTypeLabel}</strong> for the ${linkedTypeLabel.toLowerCase()} 
                           "<strong>${this.escapeHtml(title)}</strong>" has been downloaded.</p>
                    </div>
                </div>

                <div class="jc-url-form-section">
                    <div class="jc-form-intro">
                        <p><i class="fas fa-info-circle"></i> 
                           Once you've published this content on your website, paste the URL below 
                           to complete the asset linking.</p>
                    </div>

                    <form class="jc-url-form" id="urlLinkForm">
                        <div class="jc-form-group">
                            <label for="publishedUrl">Published URL</label>
                            <div class="jc-input-wrapper">
                                <i class="fas fa-link"></i>
                                <input type="url" 
                                       id="publishedUrl" 
                                       name="publishedUrl"
                                       placeholder="https://example.com/your-published-content"
                                       class="jc-url-input"
                                       required>
                            </div>
                            <div class="jc-validation-message" id="urlValidation"></div>
                        </div>

                        <div class="jc-form-actions">
                            <button type="button" class="btn btn-secondary jc-skip-btn">
                                <i class="fas fa-forward"></i> Skip for Now
                            </button>
                            <button type="submit" class="btn btn-primary jc-submit-btn">
                                <i class="fas fa-link"></i> Link URL & Continue
                            </button>
                        </div>
                    </form>
                </div>

                <div class="jc-url-tips">
                    <h4><i class="fas fa-lightbulb"></i> Tips</h4>
                    <ul>
                        <li>Copy the full URL from your browser's address bar after publishing</li>
                        <li>Make sure the URL is publicly accessible</li>
                        <li>You can add the URL later from the completion grid</li>
                    </ul>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        const form = this.container.querySelector('#urlLinkForm');
        const urlInput = this.container.querySelector('#publishedUrl');
        const skipBtn = this.container.querySelector('.jc-skip-btn');

        if (form) {
            form.addEventListener('submit', this.handleSubmit);
        }

        if (urlInput) {
            urlInput.addEventListener('input', () => this.validateUrl(urlInput.value));
            urlInput.addEventListener('blur', () => this.validateUrl(urlInput.value));
        }

        if (skipBtn) {
            skipBtn.addEventListener('click', this.handleSkip);
        }
    }

    /**
     * Handle form submission
     * 
     * @param {Event} e Submit event
     */
    async handleSubmit(e) {
        e.preventDefault();

        const urlInput = this.container.querySelector('#publishedUrl');
        const url = urlInput.value.trim();

        // Validate URL
        if (!this.validateUrl(url)) {
            return;
        }

        const submitBtn = this.container.querySelector('.jc-submit-btn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Linking...';
        }

        try {
            // Update asset with URL
            const assetResponse = await fetch(
                `${this.apiBase}/journey-circles/${this.journeyCircleId}/assets/${this.currentAsset.id}`,
                {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': this.nonce,
                    },
                    body: JSON.stringify({ url }),
                }
            );

            if (!assetResponse.ok) {
                const error = await assetResponse.json();
                throw new Error(error.message || 'Failed to update asset URL');
            }

            const result = await assetResponse.json();

            // Show success and dispatch event
            this.showSuccess();
            this.dispatchEvent('urlLinked', {
                assetId: this.currentAsset.id,
                url,
                asset: result.asset,
            });

        } catch (error) {
            console.error('Failed to link URL:', error);
            this.showError(error.message);
            
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-link"></i> Link URL & Continue';
            }
        }
    }

    /**
     * Handle skip button click
     */
    handleSkip() {
        this.dispatchEvent('urlSkipped', {
            assetId: this.currentAsset.id,
        });
    }

    /**
     * Validate URL format
     * 
     * @param {string} url URL to validate
     * @returns {boolean} Whether URL is valid
     */
    validateUrl(url) {
        const validationEl = this.container.querySelector('#urlValidation');
        const urlInput = this.container.querySelector('#publishedUrl');

        if (!url) {
            validationEl.textContent = '';
            urlInput.classList.remove('valid', 'invalid');
            return false;
        }

        try {
            const urlObj = new URL(url);
            
            // Check for valid protocol
            if (!['http:', 'https:'].includes(urlObj.protocol)) {
                throw new Error('URL must start with http:// or https://');
            }

            // Check for valid hostname
            if (!urlObj.hostname || urlObj.hostname.indexOf('.') === -1) {
                throw new Error('Please enter a valid domain');
            }

            validationEl.textContent = '✓ Valid URL';
            validationEl.className = 'jc-validation-message valid';
            urlInput.classList.add('valid');
            urlInput.classList.remove('invalid');
            return true;

        } catch (error) {
            validationEl.textContent = error.message || 'Please enter a valid URL';
            validationEl.className = 'jc-validation-message invalid';
            urlInput.classList.add('invalid');
            urlInput.classList.remove('valid');
            return false;
        }
    }

    /**
     * Show success message
     */
    showSuccess() {
        const formSection = this.container.querySelector('.jc-url-form-section');
        if (formSection) {
            formSection.innerHTML = `
                <div class="jc-link-success">
                    <div class="jc-success-icon">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <h3>URL Linked Successfully!</h3>
                    <p>Your content has been linked to the journey circle.</p>
                    <div class="jc-success-actions">
                        <button class="btn btn-primary jc-continue-btn">
                            <i class="fas fa-arrow-right"></i> Continue to Next Asset
                        </button>
                    </div>
                </div>
            `;

            const continueBtn = formSection.querySelector('.jc-continue-btn');
            if (continueBtn) {
                continueBtn.addEventListener('click', () => {
                    this.dispatchEvent('continueToNext', {
                        assetId: this.currentAsset.id,
                    });
                });
            }
        }
    }

    /**
     * Show error message
     * 
     * @param {string} message Error message
     */
    showError(message) {
        const validationEl = this.container.querySelector('#urlValidation');
        if (validationEl) {
            validationEl.textContent = message;
            validationEl.className = 'jc-validation-message error';
        }
    }

    /**
     * Get human-readable asset type label
     * 
     * @param {string} assetType Asset type code
     * @returns {string} Human-readable label
     */
    getAssetTypeLabel(assetType) {
        const labels = {
            'article_long': 'Long Article',
            'article_short': 'Short Article',
            'infographic': 'Infographic',
            'other': 'Content Asset',
        };
        return labels[assetType] || 'Content Asset';
    }

    /**
     * Dispatch custom event
     * 
     * @param {string} eventName Event name
     * @param {Object} detail Event detail
     */
    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(`assetUrlLinker:${eventName}`, {
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

/**
 * Integration with existing AssetCreator class
 * 
 * This function extends the existing asset-creator.js module to include
 * the Step 10 URL linking phase after download.
 */
function extendAssetCreatorWithUrlLinking(AssetCreator) {
    const originalDownloadComplete = AssetCreator.prototype.handleDownloadComplete;

    /**
     * Extended download complete handler
     * Transitions to Step 10 URL linking after download
     */
    AssetCreator.prototype.handleDownloadComplete = function(asset) {
        // Call original handler if exists
        if (typeof originalDownloadComplete === 'function') {
            originalDownloadComplete.call(this, asset);
        }

        // Transition to Step 10
        this.showUrlLinkingPhase(asset);
    };

    /**
     * Show URL linking phase (Step 10)
     * 
     * @param {Object} asset The downloaded asset
     */
    AssetCreator.prototype.showUrlLinkingPhase = function(asset) {
        // Initialize URL linker
        const urlLinker = new AssetUrlLinker({
            journeyCircleId: this.journeyCircleId,
            apiBase: this.apiBase,
            nonce: this.nonce,
        });

        // Create container for URL linking UI
        const linkContainer = document.createElement('div');
        linkContainer.className = 'jc-step-10-container';
        this.container.appendChild(linkContainer);

        // Hide Step 9 content
        const step9Content = this.container.querySelector('.jc-step-9-content');
        if (step9Content) {
            step9Content.style.display = 'none';
        }

        // Initialize URL linker
        urlLinker.init(linkContainer, asset);

        // Handle URL linking events
        linkContainer.addEventListener('assetUrlLinker:urlLinked', (e) => {
            this.handleUrlLinked(e.detail);
        });

        linkContainer.addEventListener('assetUrlLinker:urlSkipped', (e) => {
            this.handleUrlSkipped(e.detail);
        });

        linkContainer.addEventListener('assetUrlLinker:continueToNext', (e) => {
            this.transitionToStep11();
        });
    };

    /**
     * Handle successful URL linking
     * 
     * @param {Object} detail Event detail
     */
    AssetCreator.prototype.handleUrlLinked = function(detail) {
        console.log('URL linked:', detail);
        // Emit event for workflow manager
        this.dispatchEvent('assetPublished', detail);
    };

    /**
     * Handle URL skip
     * 
     * @param {Object} detail Event detail
     */
    AssetCreator.prototype.handleUrlSkipped = function(detail) {
        console.log('URL skipped:', detail);
        this.transitionToStep11();
    };

    /**
     * Transition to Step 11 (completion grid)
     */
    AssetCreator.prototype.transitionToStep11 = function() {
        this.dispatchEvent('proceedToStep11');
    };

    return AssetCreator;
}

// Export modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AssetUrlLinker, extendAssetCreatorWithUrlLinking };
}

// Attach to window for direct script usage
window.AssetUrlLinker = AssetUrlLinker;
window.extendAssetCreatorWithUrlLinking = extendAssetCreatorWithUrlLinking;
