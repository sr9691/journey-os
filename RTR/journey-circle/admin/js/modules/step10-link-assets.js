/**
 * Step 10 - Link Published Assets Manager
 * 
 * Handles Step 10 of the Journey Circle Creator:
 * - Displays each problem/solution pair with their created content
 * - Allows user to paste published URLs for each asset
 * - Saves URLs to workflow state (localStorage)
 * - Optionally persists to database via REST API
 * - Validates URL format
 * - Allows skipping (URLs can be added later)
 * 
 * Works with template ID: #jc-step-10, #jc-asset-url-list
 * Reads from state: selectedProblems, selectedSolutions, contentAssets
 * Writes to state: publishedUrls (object keyed by problem ID)
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

(function($) {
    'use strict';

    class Step10LinkAssets {
        constructor(workflow) {
            this.workflow = workflow;
            this.apiBase = workflow.config.restUrl;
            this.nonce = workflow.config.restNonce;

            // State
            this.selectedProblems = [];
            this.selectedSolutions = {};
            this.contentAssets = {};
            this.publishedUrls = {};  // problemId -> url string

            this.init();
        }

        init() {
            const state = this.workflow.getState();
            if (state) {
                this.selectedProblems = state.selectedProblems || [];
                this.selectedSolutions = state.selectedSolutions || {};
                this.contentAssets = state.contentAssets || {};
                this.publishedUrls = state.publishedUrls || {};
            }

            $(document).on('jc:stepChanged', (e, step) => {
                if (step === 10) this.initStep10();
            });

            const currentStep = state ? state.currentStep : null;
            if (currentStep === 10) this.initStep10();

            console.log('Step10LinkAssets initialized');
        }

        initStep10() {
            const container = document.getElementById('jc-asset-url-list');
            if (!container) return;

            // Reload state
            const state = this.workflow.getState();
            this.selectedProblems = state.selectedProblems || [];
            this.selectedSolutions = state.selectedSolutions || {};
            this.contentAssets = state.contentAssets || {};
            this.publishedUrls = state.publishedUrls || {};

            if (this.selectedProblems.length === 0) {
                container.innerHTML = `
                    <div style="padding:24px;text-align:center;color:#666">
                        <i class="fas fa-exclamation-circle" style="font-size:2em;margin-bottom:10px;display:block;color:#ffc107"></i>
                        <p>No problems/solutions found. Please complete earlier steps first.</p>
                    </div>`;
                return;
            }

            this.render(container);
        }

        render(container) {
            const linkedCount = Object.values(this.publishedUrls).filter(u => u && u.trim()).length;
            // Count total approved/downloaded assets across new problem/solution split structure
            let totalAssets = 0;
            Object.values(this.contentAssets).forEach(entry => {
                if (!entry) return;
                // New structure: entry = { problem: { types: {} }, solution: { types: {} } }
                ['problem', 'solution'].forEach(focus => {
                    if (entry[focus] && entry[focus].types) {
                        Object.values(entry[focus].types).forEach(t => {
                            if (t && (t.status === 'approved' || t.status === 'downloaded')) totalAssets++;
                        });
                    }
                });
                // Legacy flat structure fallback: entry = { status: 'approved', ... }
                if (entry.status && (entry.status === 'approved' || entry.status === 'downloaded')) totalAssets++;
            });

            container.innerHTML = `
                <!-- Summary -->
                <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;margin-bottom:16px;background:#f8f9fa;border-radius:8px;border:1px solid #eee">
                    <span style="font-size:14px;font-weight:600">Link Published Content</span>
                    <span style="font-size:13px;color:${linkedCount > 0 ? '#2e7d32' : '#666'}">
                        <i class="fas fa-link" style="color:${linkedCount > 0 ? '#4caf50' : '#90a4ae'}"></i>
                        ${linkedCount} / ${this.selectedProblems.length} linked
                    </span>
                </div>

                <p style="font-size:13px;color:#666;margin-bottom:16px;padding:0 4px;line-height:1.5">
                    After publishing your content assets on the client's website (or any platform), 
                    paste the live URLs below to complete the journey circle. This step is optional — 
                    you can skip it and add URLs later from the dashboard.
                </p>

                <!-- URL Form for Each Problem -->
                ${this.selectedProblems.map((problem, index) => {
                    const solution = this.selectedSolutions[problem.id] || '';
                    const assetEntry = this.contentAssets[problem.id];
                    let hasContent = false;
                    if (assetEntry) {
                        ['problem', 'solution'].forEach(focus => {
                            if (assetEntry[focus] && assetEntry[focus].types) {
                                Object.values(assetEntry[focus].types).forEach(t => {
                                    if (t && (t.status === 'approved' || t.status === 'downloaded')) hasContent = true;
                                });
                            }
                        });
                        // Legacy fallback
                        if (assetEntry.status && (assetEntry.status === 'approved' || assetEntry.status === 'downloaded')) hasContent = true;
                    }
                    const currentUrl = this.publishedUrls[problem.id] || '';
                    const isLinked = currentUrl && currentUrl.trim().length > 0;

                    return `
                        <div class="jc-url-section" data-problem-id="${problem.id}"
                             style="margin-bottom:14px;border:1px solid ${isLinked ? '#c8e6c9' : '#ddd'};border-radius:8px;overflow:hidden;background:${isLinked ? '#f1f8e9' : '#fff'}">
                            
                            <!-- Header -->
                            <div style="padding:12px 16px;background:${isLinked ? '#e8f5e9' : '#f8f9fa'};border-bottom:1px solid #eee;display:flex;align-items:center;gap:12px">
                                <span style="background:${isLinked ? '#66bb6a' : '#e74c3c'};color:#fff;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;flex-shrink:0">
                                    ${isLinked ? '<i class="fas fa-check" style="font-size:11px"></i>' : (index + 1)}
                                </span>
                                <div style="flex:1;min-width:0">
                                    <div style="font-weight:600;font-size:13px;color:#333;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${this.esc(problem.title)}</div>
                                    <div style="font-size:11px;color:#42a5f5;margin-top:1px">
                                        <i class="fas fa-arrow-right" style="font-size:9px"></i> ${this.esc(solution)}
                                    </div>
                                </div>
                                <div style="flex-shrink:0">
                                    ${hasContent 
                                        ? '<span style="font-size:11px;color:#2e7d32;background:#e8f5e9;padding:2px 8px;border-radius:10px"><i class="fas fa-file-alt"></i> Content Ready</span>'
                                        : '<span style="font-size:11px;color:#999;background:#f5f5f5;padding:2px 8px;border-radius:10px"><i class="fas fa-clock"></i> No Content Yet</span>'
                                    }
                                </div>
                            </div>

                            <!-- URL Input -->
                            <div style="padding:12px 16px">
                                <div style="display:flex;gap:8px;align-items:center">
                                    <i class="fas fa-globe" style="color:#90a4ae;flex-shrink:0"></i>
                                    <input type="url" 
                                           class="jc-published-url-input" 
                                           data-problem-id="${problem.id}"
                                           value="${this.esc(currentUrl)}"
                                           placeholder="https://client-site.com/published-article-url"
                                           style="flex:1;padding:8px 12px;border:1px solid ${isLinked ? '#a5d6a7' : '#ddd'};border-radius:4px;font-size:13px">
                                    <button type="button" 
                                            class="button button-small jc-save-url-btn ${isLinked ? 'button-primary' : ''}" 
                                            data-problem-id="${problem.id}"
                                            style="white-space:nowrap">
                                        ${isLinked ? '<i class="fas fa-check"></i> Saved' : '<i class="fas fa-save"></i> Save'}
                                    </button>
                                    ${isLinked ? `
                                        <a href="${this.esc(currentUrl)}" target="_blank" rel="noopener" 
                                           style="color:#1976d2;flex-shrink:0;padding:4px" title="Open URL">
                                            <i class="fas fa-external-link-alt"></i>
                                        </a>
                                    ` : ''}
                                </div>
                                <div class="jc-url-error" data-problem-id="${problem.id}" 
                                     style="display:none;color:#e53935;font-size:12px;margin-top:6px;padding-left:26px"></div>
                            </div>
                        </div>
                    `;
                }).join('')}

                <!-- Bulk actions -->
                ${linkedCount > 0 ? `
                    <div style="padding:12px 16px;margin-top:12px;text-align:center;background:#e8f5e9;border-radius:8px;border:1px solid #c8e6c9">
                        <i class="fas fa-check-circle" style="color:#66bb6a;margin-right:6px"></i>
                        <span style="color:#2e7d32;font-size:13px;font-weight:600">${linkedCount} URL${linkedCount !== 1 ? 's' : ''} linked. You can proceed to the final step.</span>
                    </div>
                ` : ''}
            `;

            this.bindEvents(container);
        }

        bindEvents(container) {
            // Save URL buttons
            container.querySelectorAll('.jc-save-url-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const problemId = btn.dataset.problemId;
                    this.saveUrl(problemId, container);
                });
            });

            // Enter key on URL input
            container.querySelectorAll('.jc-published-url-input').forEach(input => {
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        const problemId = input.dataset.problemId;
                        this.saveUrl(problemId, container);
                    }
                });

                // Auto-save on blur
                input.addEventListener('blur', () => {
                    const problemId = input.dataset.problemId;
                    const url = input.value.trim();
                    if (url && this.isValidUrl(url)) {
                        this.saveUrl(problemId, container);
                    }
                });
            });
        }

        saveUrl(problemId, container) {
            const input = container.querySelector(`.jc-published-url-input[data-problem-id="${problemId}"]`);
            const errorEl = container.querySelector(`.jc-url-error[data-problem-id="${problemId}"]`);
            if (!input) return;

            const url = input.value.trim();

            // Allow empty (clear the URL)
            if (!url) {
                delete this.publishedUrls[problemId];
                this.workflow.updateState('publishedUrls', this.publishedUrls);
                this.render(container);
                return;
            }

            // Validate
            if (!this.isValidUrl(url)) {
                if (errorEl) {
                    errorEl.textContent = 'Please enter a valid URL (e.g., https://example.com/article).';
                    errorEl.style.display = 'block';
                    setTimeout(() => { errorEl.style.display = 'none'; }, 4000);
                }
                input.style.borderColor = '#e53935';
                input.focus();
                return;
            }

            // Save
            this.publishedUrls[problemId] = url;
            this.workflow.updateState('publishedUrls', this.publishedUrls);

            // Show success feedback briefly
            const btn = container.querySelector(`.jc-save-url-btn[data-problem-id="${problemId}"]`);
            if (btn) {
                btn.innerHTML = '<i class="fas fa-check"></i> Saved!';
                btn.classList.add('button-primary');
            }

            // Re-render to reflect updated state
            setTimeout(() => this.render(container), 600);

            // Also try to persist to API if we have a journey circle ID
            this.persistUrlToApi(problemId, url);
        }

        async persistUrlToApi(problemId, url) {
            const state = this.workflow.getState();
            const journeyCircleId = state.journeyCircleId;
            
            // Only persist if we have a real database journey circle ID
            // and a numeric problem ID (not localStorage-style prob_1, prob_2, etc.)
            if (!journeyCircleId || !problemId || /^prob_/.test(problemId)) {
                // URL is already saved in localStorage via workflow state — that's sufficient
                return;
            }

            // Build the correct directreach/v2 endpoint
            let apiBase = this.apiBase;
            // If apiBase points to journey-circle/v1, switch to directreach/v2
            if (apiBase.indexOf('journey-circle/v1') !== -1) {
                apiBase = apiBase.replace('journey-circle/v1', 'directreach/v2');
            }

            try {
                const response = await fetch(`${apiBase}/journey-circles/${journeyCircleId}/problems/${problemId}/asset-urls`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': this.nonce
                    },
                    body: JSON.stringify({
                        asset_urls: [url]
                    })
                });
                if (!response.ok) {
                    console.debug('[Step10] API persist returned', response.status, '(URL saved locally)');
                }
            } catch (error) {
                // Silently fail - URL is already saved in localStorage
                console.debug('[Step10] API persist failed (URL saved locally):', error.message);
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
            window.drStep10LinkAssets = new Step10LinkAssets(window.drJourneyCircle);
        }
    });

})(jQuery);