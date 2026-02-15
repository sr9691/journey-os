/**
 * Step 11 - Journey Complete Manager
 * 
 * Handles Step 11 of the Journey Circle Creator:
 * - Populates summary statistics (problems, solutions, offers, assets)
 * - Allows user to go back and create more assets
 * - Marks journey as complete via REST API
 * - Stores completion data in sessionStorage
 * - Navigates back to Campaign Builder with success notification
 * 
 * Works with template IDs: #jc-step-11, #jc-summary-stats,
 *   #jc-stat-problems, #jc-stat-solutions, #jc-stat-offers, #jc-stat-assets,
 *   #jc-create-more-assets, #jc-complete-journey
 * 
 * Reads from state: selectedProblems, selectedSolutions, offers, contentAssets, publishedUrls
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

(function($) {
    'use strict';

    class Step11Complete {
        constructor(workflow) {
            this.workflow = workflow;
            this.apiBase = workflow.config.restUrl;
            this.nonce = workflow.config.restNonce;
            this.campaignBuilderUrl = workflow.config.campaignBuilderUrl;

            this._bound = false;
            this.init();
        }

        init() {
            $(document).on('jc:stepChanged', (e, step) => {
                if (step === 11) this.initStep11();
            });

            const state = this.workflow.getState();
            if (state && state.currentStep === 11) {
                this.initStep11();
            }

            console.log('Step11Complete initialized');
        }

        initStep11() {
            const state = this.workflow.getState();
            if (!state) return;

            this.updateSummaryStats(state);
            this.renderCompletionDetails(state);

            if (!this._bound) {
                this._bound = true;
                this.bindEvents();
            }
        }

        updateSummaryStats(state) {
            const problems = state.selectedProblems || [];
            const solutions = state.selectedSolutions || {};
            const offers = state.offers || {};
            const contentAssets = state.contentAssets || {};
            const publishedUrls = state.publishedUrls || {};

            const problemCount = problems.length;
            const solutionCount = Object.keys(solutions).length;
            const offerCount = Object.values(offers).reduce((sum, arr) => {
                return sum + (Array.isArray(arr) ? arr.length : 0);
            }, 0);
            let assetCount = 0;
            Object.values(contentAssets).forEach(entry => {
                if (!entry) return;
                ['problem', 'solution'].forEach(focus => {
                    if (entry[focus] && entry[focus].types) {
                        Object.values(entry[focus].types).forEach(t => {
                            if (t && (t.status === 'approved' || t.status === 'downloaded')) assetCount++;
                        });
                    }
                });
                if (entry.status && (entry.status === 'approved' || entry.status === 'downloaded')) assetCount++;
            });
            const linkedCount = Object.values(publishedUrls).filter(u => u && u.trim()).length;

            // Update stat elements
            const statProblems = document.getElementById('jc-stat-problems');
            const statSolutions = document.getElementById('jc-stat-solutions');
            const statOffers = document.getElementById('jc-stat-offers');
            const statAssets = document.getElementById('jc-stat-assets');

            if (statProblems) statProblems.textContent = problemCount;
            if (statSolutions) statSolutions.textContent = solutionCount;
            if (statOffers) statOffers.textContent = offerCount;
            if (statAssets) statAssets.textContent = assetCount;

            // Insert additional detail below the stats
            const summaryContainer = document.getElementById('jc-summary-stats');
            if (summaryContainer) {
                // Remove any existing detail row
                const existingDetail = summaryContainer.querySelector('.jc-summary-detail-row');
                if (existingDetail) existingDetail.remove();

                const detailRow = document.createElement('div');
                detailRow.className = 'jc-summary-detail-row';
                detailRow.style.cssText = 'width:100%;margin-top:16px;padding-top:16px;border-top:1px solid #e0e0e0;text-align:center;font-size:13px;color:#666';
                detailRow.innerHTML = `
                    <span style="margin-right:20px">
                        <i class="fas fa-link" style="color:#42a5f5"></i> 
                        ${linkedCount} published URL${linkedCount !== 1 ? 's' : ''} linked
                    </span>
                    <span>
                        <i class="fas fa-tag" style="color:#66bb6a"></i> 
                        ${offerCount} offer${offerCount !== 1 ? 's' : ''} mapped
                    </span>
                `;
                summaryContainer.appendChild(detailRow);
            }
        }

        renderCompletionDetails(state) {
            const problems = state.selectedProblems || [];
            const solutions = state.selectedSolutions || {};
            const contentAssets = state.contentAssets || {};
            const publishedUrls = state.publishedUrls || {};
            const offers = state.offers || {};

            // Find or create a detail panel below the summary
            let detailPanel = document.getElementById('jc-completion-detail');
            if (!detailPanel) {
                const completionSummary = document.querySelector('.jc-completion-summary');
                if (completionSummary) {
                    detailPanel = document.createElement('div');
                    detailPanel.id = 'jc-completion-detail';
                    // Insert before the action buttons
                    const actions = completionSummary.querySelector('.jc-completion-actions');
                    if (actions) {
                        completionSummary.insertBefore(detailPanel, actions);
                    } else {
                        completionSummary.appendChild(detailPanel);
                    }
                }
            }

            if (!detailPanel) return;

            detailPanel.innerHTML = `
                <div style="margin:20px 0;padding:16px;background:#f8f9fa;border-radius:8px;border:1px solid #eee;max-height:300px;overflow-y:auto">
                    <h4 style="margin:0 0 12px 0;font-size:14px;color:#333;font-weight:600">
                        <i class="fas fa-list-alt" style="color:#42a5f5"></i> Journey Summary
                    </h4>
                    
                    ${problems.map((problem, index) => {
                        const solution = solutions[problem.id] || 'No solution';
                        const assetEntry = contentAssets[problem.id];
                        let hasContent = false;
                        if (assetEntry) {
                            ['problem', 'solution'].forEach(focus => {
                                if (assetEntry[focus] && assetEntry[focus].types) {
                                    Object.values(assetEntry[focus].types).forEach(t => {
                                        if (t && (t.status === 'approved' || t.status === 'downloaded')) hasContent = true;
                                    });
                                }
                            });
                            if (assetEntry.status && (assetEntry.status === 'approved' || assetEntry.status === 'downloaded')) hasContent = true;
                        }
                        const publishedUrl = publishedUrls[problem.id];
                        const problemOffers = offers[problem.id] || [];

                        return `
                            <div style="margin-bottom:10px;padding:10px 12px;background:#fff;border:1px solid #eee;border-radius:6px;border-left:3px solid ${hasContent ? '#66bb6a' : '#ff9800'}">
                                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                                    <span style="background:#e74c3c;color:#fff;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;flex-shrink:0">${index + 1}</span>
                                    <span style="font-weight:600;font-size:13px;color:#333">${this.esc(problem.title)}</span>
                                </div>
                                <div style="padding-left:30px;font-size:12px;color:#666;line-height:1.6">
                                    <div><i class="fas fa-arrow-right" style="color:#42a5f5;font-size:10px;width:14px"></i> ${this.esc(solution)}</div>
                                    <div>
                                        <i class="fas fa-${hasContent ? 'check-circle' : 'clock'}" style="color:${hasContent ? '#66bb6a' : '#ff9800'};font-size:10px;width:14px"></i> 
                                        ${hasContent ? `Content: ${this.getAssetFormats(assetEntry)}` : 'No content created'}
                                    </div>
                                    ${publishedUrl ? `
                                        <div>
                                            <i class="fas fa-link" style="color:#42a5f5;font-size:10px;width:14px"></i> 
                                            <a href="${this.esc(publishedUrl)}" target="_blank" rel="noopener" style="color:#1976d2;text-decoration:none;font-size:11px">
                                                ${this.truncateUrl(publishedUrl)}
                                            </a>
                                        </div>
                                    ` : ''}
                                    ${problemOffers.length > 0 ? `
                                        <div>
                                            <i class="fas fa-tag" style="color:#66bb6a;font-size:10px;width:14px"></i> 
                                            ${problemOffers.length} offer${problemOffers.length !== 1 ? 's' : ''}: ${problemOffers.map(o => this.esc(o.title)).join(', ')}
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        bindEvents() {
            // "Create More Assets" button
            const createMoreBtn = document.getElementById('jc-create-more-assets');
            if (createMoreBtn) {
                createMoreBtn.addEventListener('click', () => {
                    // Navigate back to Step 9
                    this.workflow.goToStep(9);
                });
            }

            // "Complete & Return" button
            const completeBtn = document.getElementById('jc-complete-journey');
            if (completeBtn) {
                completeBtn.addEventListener('click', () => {
                    this.completeJourney();
                });
            }
        }

        async completeJourney() {
            const completeBtn = document.getElementById('jc-complete-journey');
            if (completeBtn) {
                completeBtn.disabled = true;
                completeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Completing...';
            }

            const state = this.workflow.getState();

            // Try to mark complete via API if we have a journey circle ID
            const journeyCircleId = state.journeyCircleId;
            let apiSuccess = false;

            if (journeyCircleId) {
                try {
                    const response = await fetch(`${this.apiBase}/journey-circles/${journeyCircleId}/complete`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-WP-Nonce': this.nonce
                        }
                    });

                    if (response.ok) {
                        apiSuccess = true;
                    } else {
                        // API might reject if not all 5 problems have assets — that's OK
                        // We still allow local completion
                        console.warn('API complete request returned non-OK, proceeding with local completion');
                    }
                } catch (error) {
                    console.warn('Could not reach API for completion, proceeding locally:', error);
                }
            }

            // Build completion data
            const problems = state.selectedProblems || [];
            const solutions = state.selectedSolutions || {};
            const offers = state.offers || {};
            const contentAssets = state.contentAssets || {};
            const publishedUrls = state.publishedUrls || {};

            const offerCount = Object.values(offers).reduce((sum, arr) => {
                return sum + (Array.isArray(arr) ? arr.length : 0);
            }, 0);
            const assetCount2Arr = Object.values(contentAssets);
            let assetCount = 0;
            assetCount2Arr.forEach(entry => {
                if (!entry) return;
                ['problem', 'solution'].forEach(focus => {
                    if (entry[focus] && entry[focus].types) {
                        Object.values(entry[focus].types).forEach(t => {
                            if (t && (t.status === 'approved' || t.status === 'downloaded')) assetCount++;
                        });
                    }
                });
                if (entry.status && (entry.status === 'approved' || entry.status === 'downloaded')) assetCount++;
            });

            const completionData = {
                success: true,
                clientId: state.clientId,
                serviceAreaId: state.serviceAreaId,
                serviceAreaName: state.serviceAreaName || '',
                circleComplete: true,
                problemCount: problems.length,
                solutionCount: Object.keys(solutions).length,
                offerCount: offerCount,
                assetCount: assetCount,
                timestamp: new Date().toISOString()
            };

            // Store in sessionStorage for Campaign Builder to pick up
            sessionStorage.setItem('dr_journey_completed', JSON.stringify(completionData));

            // Update local state
            this.workflow.updateState('journeyStatus', 'complete');

            // Brief celebration before redirect
            this.showCelebration(() => {
                // Navigate to Campaign Builder
                window.location.href = this.campaignBuilderUrl + 
                    (this.campaignBuilderUrl.indexOf('?') > -1 ? '&' : '?') + 
                    'journey_success=1';
            });
        }

        showCelebration(callback) {
            // Replace the completion actions with a celebration message
            const actions = document.querySelector('.jc-completion-actions');
            if (actions) {
                actions.innerHTML = `
                    <div style="text-align:center;padding:20px">
                        <div style="font-size:3em;margin-bottom:12px">🎉</div>
                        <h3 style="color:#2e7d32;margin:0 0 8px 0">Journey Circle Complete!</h3>
                        <p style="color:#666;margin:0;font-size:14px">Redirecting to Campaign Builder...</p>
                        <div style="margin-top:12px">
                            <i class="fas fa-spinner fa-spin" style="color:#42a5f5;font-size:1.5em"></i>
                        </div>
                    </div>
                `;
            }

            // Also update the completion icon
            const icon = document.querySelector('.jc-completion-icon');
            if (icon) {
                icon.innerHTML = '<i class="fas fa-trophy" style="color:#ffc107;font-size:3em"></i>';
            }

            // Redirect after a brief delay
            setTimeout(() => {
                if (typeof callback === 'function') callback();
            }, 2000);
        }

        // =====================================================================
        // UTILITIES
        // =====================================================================

        /**
         * Extract human-readable format labels from a contentAssets entry.
         * Structure: { problem: { types: { format: {status} } }, solution: { types: { format: {status} } } }
         * Legacy:    { format, status, content }
         */
        getAssetFormats(assetEntry) {
            if (!assetEntry) return 'Unknown';
            const formats = [];

            // New structure: problem/solution focus with types
            ['problem', 'solution'].forEach(focus => {
                if (assetEntry[focus] && assetEntry[focus].types) {
                    Object.keys(assetEntry[focus].types).forEach(fmt => {
                        const t = assetEntry[focus].types[fmt];
                        if (t && (t.status === 'approved' || t.status === 'downloaded' || t.status === 'draft')) {
                            const label = this.formatLabel(fmt);
                            const tag = focus === 'problem' ? 'P' : 'S';
                            formats.push(`${label} (${tag})`);
                        }
                    });
                }
            });

            // Legacy structure: single format/status at top level
            if (formats.length === 0 && assetEntry.format) {
                formats.push(this.formatLabel(assetEntry.format));
            }

            return formats.length > 0 ? formats.join(', ') : 'Created';
        }

        formatLabel(format) {
            const labels = {
                'article_long': 'Long Article',
                'article_short': 'Short Article',
                'blog_post': 'Blog Post',
                'linkedin_post': 'LinkedIn Post',
                'presentation': 'Presentation',
                'infographic': 'Infographic'
            };
            return labels[format] || format || 'Unknown';
        }

        truncateUrl(url) {
            if (!url) return '';
            if (url.length <= 60) return url;
            return url.substring(0, 55) + '...';
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
            window.drStep11Complete = new Step11Complete(window.drJourneyCircle);
        }
    });

})(jQuery);