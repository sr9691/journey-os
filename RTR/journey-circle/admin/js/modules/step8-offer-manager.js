/**
 * Step 8 Offer Mapping Manager - FIXED
 * 
 * Changes from original:
 * 1. Fixed selectedSolutions reading — it's { problemId: "title string" } not nested objects
 * 2. Added validation check for step 8 in workflow validateCurrentStep
 * 3. Added proper problem.id comparison (string vs number)
 * 4. Added step validation: requires at least 1 offer total to proceed
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

(function($) {
    'use strict';

    class Step8OfferManager {
        constructor(workflow) {
            this.workflow = workflow;
            this.nonce = workflow.config.restNonce;

            // State
            this.selectedProblems = [];
            this.selectedSolutions = {};
            this.offers = {}; // problemId -> [ { id, title, url } ]

            this._bound = false;

            this.init();
        }

        init() {
            // Load saved state
            const state = this.workflow.getState();
            if (state) {
                this.selectedProblems = state.selectedProblems || [];
                this.selectedSolutions = state.selectedSolutions || {};
                this.offers = state.offers || {};
            }

            // Listen for step changes
            $(document).on('jc:stepChanged', (e, step) => {
                if (step === 8) this.initStep8();
            });

            // If already on step 8, init immediately
            const currentStep = state ? state.currentStep : null;
            if (currentStep === 8) this.initStep8();

            console.log('Step8OfferManager initialized');
        }

        initStep8() {
            const container = document.getElementById('jc-offer-mapping-container');
            if (!container) return;

            // Reload state in case user went back and changed steps 5-7
            const state = this.workflow.getState();
            this.selectedProblems = state.selectedProblems || [];
            this.selectedSolutions = state.selectedSolutions || {};
            this.offers = state.offers || {};

            // Check prerequisites
            if (this.selectedProblems.length === 0) {
                container.innerHTML = `
                    <div style="padding:24px;text-align:center;color:#666">
                        <i class="fas fa-exclamation-circle" style="font-size:2em;margin-bottom:10px;display:block;color:#ffc107"></i>
                        <p>Please go back and complete Steps 5-7 first.</p>
                        <p style="font-size:13px;color:#999">You need to select problems and solutions before mapping offers.</p>
                    </div>`;
                return;
            }

            // Check that solutions were selected
            const hasSolutions = Object.keys(this.selectedSolutions).length > 0;
            if (!hasSolutions) {
                container.innerHTML = `
                    <div style="padding:24px;text-align:center;color:#666">
                        <i class="fas fa-exclamation-circle" style="font-size:2em;margin-bottom:10px;display:block;color:#ffc107"></i>
                        <p>Please go back to Step 7 and select solutions for each problem.</p>
                    </div>`;
                return;
            }

            this.render(container);
        }

        render(container) {
            const totalOffers = Object.values(this.offers).reduce((sum, arr) => {
                return sum + (Array.isArray(arr) ? arr.length : 0);
            }, 0);

            const sectionsHTML = this.selectedProblems.map((problem, index) => {
                // FIX: selectedSolutions is { problemId: "title string" }
                // problem.id might be string or number, handle both
                const pid = String(problem.id);
                const solutionTitle = this.selectedSolutions[pid] 
                    || this.selectedSolutions[problem.id] 
                    || 'No solution selected';
                
                // offers keyed by problem id (might be string or number)
                const problemOffers = this.offers[pid] || this.offers[problem.id] || [];

                return `
                    <div class="jc-offer-section" data-problem-id="${problem.id}" 
                         style="margin-bottom:20px;border:1px solid #ddd;border-radius:8px;overflow:hidden;background:#fff">
                        
                        <!-- Header -->
                        <div style="padding:14px 16px;background:#f8f9fa;border-bottom:1px solid #eee;display:flex;align-items:center;justify-content:space-between">
                            <div style="display:flex;align-items:center;gap:12px">
                                <span style="background:#e74c3c;color:#fff;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0">${index + 1}</span>
                                <div>
                                    <div style="font-weight:600;font-size:14px;color:#333">${this.esc(problem.title)}</div>
                                    <div style="font-size:12px;color:#42a5f5;margin-top:2px">
                                        <i class="fas fa-arrow-right" style="font-size:10px"></i> 
                                        ${this.esc(typeof solutionTitle === 'string' ? solutionTitle : String(solutionTitle))}
                                    </div>
                                </div>
                            </div>
                            <span style="background:${problemOffers.length > 0 ? '#e8f5e9' : '#fff3e0'};color:${problemOffers.length > 0 ? '#2e7d32' : '#e65100'};padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600">
                                ${problemOffers.length} offer${problemOffers.length !== 1 ? 's' : ''}
                            </span>
                        </div>

                        <!-- Offers List -->
                        <div style="padding:12px 16px">
                            ${problemOffers.length > 0 ? problemOffers.map(offer => `
                                <div class="jc-offer-item" data-offer-id="${offer.id}" 
                                     style="display:flex;align-items:center;gap:10px;padding:10px 12px;margin-bottom:8px;background:#f9f9f9;border:1px solid #eee;border-radius:6px">
                                    <i class="fas fa-tag" style="color:#66bb6a;flex-shrink:0"></i>
                                    <div style="flex:1;min-width:0">
                                        <div style="font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this.esc(offer.title)}</div>
                                        <a href="${this.esc(offer.url)}" target="_blank" rel="noopener" 
                                           style="font-size:12px;color:#1976d2;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block">
                                            ${this.esc(offer.url)}
                                        </a>
                                    </div>
                                    <button type="button" class="jc-remove-offer-btn" data-problem-id="${problem.id}" data-offer-id="${offer.id}"
                                            style="background:none;border:none;color:#e53935;cursor:pointer;padding:4px 8px;font-size:16px;flex-shrink:0"
                                            title="Remove offer">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                            `).join('') : `
                                <div style="padding:12px;text-align:center;color:#999;font-size:13px;font-style:italic">
                                    No offers added yet. Add at least one below.
                                </div>
                            `}

                            <!-- Add Offer Form -->
                            <div style="margin-top:10px;padding:12px;background:#f0f7ff;border:1px dashed #90caf9;border-radius:6px">
                                <div style="display:flex;gap:8px;flex-wrap:wrap">
                                    <input type="text" class="jc-offer-title-input" data-problem-id="${problem.id}"
                                           placeholder="Offer title (e.g., Free Cloud Audit)"
                                           style="flex:1;min-width:180px;padding:8px 12px;border:1px solid #ddd;border-radius:4px;font-size:13px">
                                    <input type="url" class="jc-offer-url-input" data-problem-id="${problem.id}"
                                           placeholder="https://example.com/offer"
                                           style="flex:1.5;min-width:220px;padding:8px 12px;border:1px solid #ddd;border-radius:4px;font-size:13px">
                                    <button type="button" class="button button-small jc-add-offer-btn" data-problem-id="${problem.id}"
                                            style="white-space:nowrap">
                                        <i class="fas fa-plus"></i> Add Offer
                                    </button>
                                </div>
                                <div class="jc-offer-error" data-problem-id="${problem.id}" style="display:none;color:#e53935;font-size:12px;margin-top:6px"></div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = `
                <!-- Summary Bar -->
                <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;margin-bottom:16px;background:#f8f9fa;border-radius:8px;border:1px solid #eee">
                    <div style="display:flex;gap:20px">
                        <span style="font-size:13px;color:#666">
                            <i class="fas fa-exclamation-circle" style="color:#e74c3c"></i> 
                            <strong>${this.selectedProblems.length}</strong> Problems
                        </span>
                        <span style="font-size:13px;color:#666">
                            <i class="fas fa-lightbulb" style="color:#42a5f5"></i> 
                            <strong>${Object.keys(this.selectedSolutions).length}</strong> Solutions
                        </span>
                        <span style="font-size:13px;color:#666">
                            <i class="fas fa-tag" style="color:#66bb6a"></i> 
                            <strong id="jc-total-offer-count">${totalOffers}</strong> Offers
                        </span>
                    </div>
                    <div style="font-size:13px;color:${totalOffers > 0 ? '#2e7d32' : '#e65100'};font-weight:600">
                        ${totalOffers > 0 
                            ? '<i class="fas fa-check-circle"></i> Ready to proceed' 
                            : '<i class="fas fa-info-circle"></i> Add at least one offer'}
                    </div>
                </div>

                <!-- Solution Sections -->
                ${sectionsHTML}
            `;

            this.bindEvents(container);
        }

        bindEvents(container) {
            // Add offer buttons
            container.querySelectorAll('.jc-add-offer-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const problemId = btn.dataset.problemId;
                    this.addOffer(problemId, container);
                });
            });

            // Enter key on URL input
            container.querySelectorAll('.jc-offer-url-input').forEach(input => {
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        const problemId = input.dataset.problemId;
                        this.addOffer(problemId, container);
                    }
                });
            });

            // Enter key on title input -> focus URL
            container.querySelectorAll('.jc-offer-title-input').forEach(input => {
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        const problemId = input.dataset.problemId;
                        const urlInput = container.querySelector(`.jc-offer-url-input[data-problem-id="${problemId}"]`);
                        if (urlInput) urlInput.focus();
                    }
                });
            });

            // Remove offer buttons
            container.querySelectorAll('.jc-remove-offer-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const problemId = btn.dataset.problemId;
                    const offerId = btn.dataset.offerId;
                    this.removeOffer(problemId, offerId, container);
                });
            });
        }

        addOffer(problemId, container) {
            const titleInput = container.querySelector(`.jc-offer-title-input[data-problem-id="${problemId}"]`);
            const urlInput = container.querySelector(`.jc-offer-url-input[data-problem-id="${problemId}"]`);
            const errorEl = container.querySelector(`.jc-offer-error[data-problem-id="${problemId}"]`);

            if (!titleInput || !urlInput) return;

            const title = titleInput.value.trim();
            const url = urlInput.value.trim();

            // Validation
            if (!title) {
                this.showError(errorEl, 'Please enter an offer title.');
                titleInput.focus();
                return;
            }

            if (!url) {
                this.showError(errorEl, 'Please enter an offer URL.');
                urlInput.focus();
                return;
            }

            if (!this.isValidUrl(url)) {
                this.showError(errorEl, 'Please enter a valid URL (e.g., https://example.com).');
                urlInput.focus();
                return;
            }

            // Hide error
            if (errorEl) errorEl.style.display = 'none';

            // Add to state — use consistent key type
            const pid = String(problemId);
            if (!this.offers[pid]) {
                this.offers[pid] = [];
            }

            this.offers[pid].push({
                id: 'offer_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5),
                title: title,
                url: url
            });

            // Save to workflow state
            this.workflow.updateState('offers', this.offers);

            // Clear inputs
            titleInput.value = '';
            urlInput.value = '';

            // Re-render
            this.render(container);

            // Focus back to title input for quick entry
            setTimeout(() => {
                const newTitleInput = container.querySelector(`.jc-offer-title-input[data-problem-id="${problemId}"]`);
                if (newTitleInput) newTitleInput.focus();
            }, 50);
        }

        removeOffer(problemId, offerId, container) {
            const pid = String(problemId);
            if (!this.offers[pid]) return;

            this.offers[pid] = this.offers[pid].filter(o => o.id !== offerId);

            // Clean up empty arrays
            if (this.offers[pid].length === 0) {
                delete this.offers[pid];
            }

            // Save to workflow state
            this.workflow.updateState('offers', this.offers);

            // Re-render
            this.render(container);
        }

        showError(errorEl, message) {
            if (errorEl) {
                errorEl.textContent = message;
                errorEl.style.display = 'block';
                setTimeout(() => { errorEl.style.display = 'none'; }, 4000);
            }
        }

        isValidUrl(string) {
            try {
                const url = new URL(string);
                return url.protocol === 'http:' || url.protocol === 'https:';
            } catch (_) {
                return false;
            }
        }

        esc(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = String(text);
            return div.innerHTML;
        }
    }

    // =========================================================================
    // INITIALIZATION
    // =========================================================================

    $(document).ready(function() {
        if (window.drJourneyCircle) {
            window.drStep8OfferManager = new Step8OfferManager(window.drJourneyCircle);
        }
    });

})(jQuery);
