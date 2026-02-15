/**
 * Steps 5-7 Manager
 * 
 * Handles the AI-powered steps of the Journey Circle Creator:
 * - Step 5: Designate Primary Problem (select 1 from AI suggestions)
 * - Step 6: Select 5 Problem Titles (select 5 from 8-10 suggestions)
 * - Step 7: Select Solution Titles (1 solution per problem)
 * 
 * Works with template IDs:
 *   Step 5: #jc-primary-problem-list, #jc-primary-problem-loading, #jc-regenerate-primary-problems
 *   Step 6: #jc-problem-titles-list, #jc-problem-titles-loading, #jc-regenerate-problem-titles, #jc-problem-selection-count
 *   Step 7: #jc-solution-mapping-container, #jc-solution-titles-loading, #jc-regenerate-solutions
 * 
 * Calls: POST /directreach/v2/ai/generate-problem-titles
 *        POST /directreach/v2/ai/generate-solution-titles
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

(function($) {
    'use strict';

    class Steps567Manager {
        constructor(workflow) {
            this.workflow = workflow;
            this.apiBase = workflow.config.restUrl;
            this.nonce = workflow.config.restNonce;

            // State
            this.problemSuggestions = [];      // AI-generated problem titles for Step 5/6
            this.primaryProblemId = null;       // Selected in Step 5
            this.selectedProblems = [];         // 5 selected in Step 6
            this.solutionSuggestions = {};      // problemId -> [solution titles]
            this.selectedSolutions = {};        // problemId -> solution title

            // Flags
            this._step5Bound = false;
            this._step6Bound = false;
            this._step7Bound = false;

            this.init();
        }

        init() {
            // Load saved state
            const state = this.workflow.getState();
            if (state) {
                this.primaryProblemId = state.primaryProblemId || null;
                this.selectedProblems = state.selectedProblems || [];
                this.selectedSolutions = state.selectedSolutions || {};
            }

            // Init guards to prevent double-initialization
            this._step5Running = false;
            this._step6Running = false;
            this._step7Running = false;

            // Listen for step changes
            $(document).on('jc:stepChanged', (e, step) => {
                if (step === 5) this.initStep5();
                if (step === 6) this.initStep6();
                if (step === 7) this.initStep7();
            });

            // If already on one of these steps, init immediately
            const currentStep = state ? state.currentStep : null;
            if (currentStep === 5) this.initStep5();
            if (currentStep === 6) this.initStep6();
            if (currentStep === 7) this.initStep7();

            console.log('Steps567Manager initialized');
        }

        // =====================================================================
        // STEP 5: DESIGNATE PRIMARY PROBLEM
        // =====================================================================

        async initStep5() {
            if (this._step5Running) return;
            this._step5Running = true;

            const list = document.getElementById('jc-primary-problem-list');
            const loading = document.getElementById('jc-primary-problem-loading');
            const regenBtn = document.getElementById('jc-regenerate-primary-problems');

            if (!list) {
                this._step5Running = false;
                return;
            }

            // Bind regenerate button once
            if (regenBtn && !this._step5Bound) {
                this._step5Bound = true;
                regenBtn.addEventListener('click', () => this.loadProblems(list, loading, regenBtn, true));
            }

            // Auto-load on first visit
            if (this.problemSuggestions.length === 0) {
                await this.loadProblems(list, loading, regenBtn, false);
            } else {
                this.renderStep5List(list);
            }

            this._step5Running = false;
        }

        async loadProblems(list, loading, regenBtn, forceRefresh) {
            if (loading) loading.style.display = 'flex';
            if (regenBtn) regenBtn.disabled = true;
            list.innerHTML = '';

            const state = this.workflow.getState();

            try {
                const response = await fetch(`${this.apiBase}/ai/generate-problem-titles`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': this.nonce
                    },
                    body: JSON.stringify({
                        service_area_id: state.serviceAreaId || 0,
                        service_area_name: '',
                        industries: state.industries || [],
                        brain_content: state.brainContent || [],
                        force_refresh: forceRefresh
                    })
                });

                const data = await response.json();

                if (data.success && data.titles && data.titles.length > 0) {
                    this.problemSuggestions = data.titles.map((t, i) => ({
                        id: `prob_${i}`,
                        title: typeof t === 'string' ? t : (t.title || t.text || String(t))
                    }));
                    this.renderStep5List(list);
                } else {
                    const errMsg = data.error || 'No suggestions generated';
                    throw new Error(errMsg);
                }
            } catch (error) {
                console.error('Problem generation error:', error);
                this.renderManualEntry(list, 'problem');
            } finally {
                if (loading) loading.style.display = 'none';
                if (regenBtn) regenBtn.disabled = false;
            }
        }

        renderStep5List(container) {
            container.innerHTML = this.problemSuggestions.map((p, i) => `
                <div class="jc-problem-card ${this.primaryProblemId === p.id ? 'jc-selected' : ''}"
                     data-id="${p.id}"
                     style="padding:12px;margin-bottom:8px;border:2px solid ${this.primaryProblemId === p.id ? '#4a90d9' : '#ddd'};border-radius:6px;cursor:pointer;background:${this.primaryProblemId === p.id ? '#f0f7ff' : '#fff'};transition:all .2s">
                    <label style="display:flex;align-items:center;gap:12px;cursor:pointer">
                        <input type="radio" name="primaryProblem" value="${p.id}"
                               ${this.primaryProblemId === p.id ? 'checked' : ''}
                               style="width:18px;height:18px">
                        <span style="background:#4a90d9;color:#fff;border-radius:50%;min-width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-weight:700">${i + 1}</span>
                        <span style="flex:1;font-size:14px">${this.esc(p.title)}</span>
                    </label>
                </div>
            `).join('');

            // Bind radio changes
            container.querySelectorAll('input[name="primaryProblem"]').forEach(radio => {
                radio.addEventListener('change', (e) => {
                    this.primaryProblemId = e.target.value;
                    this.workflow.updateState('primaryProblemId', this.primaryProblemId);
                    this.renderStep5List(container); // Re-render to update styles
                });
            });

            // Card click
            container.querySelectorAll('.jc-problem-card').forEach(card => {
                card.addEventListener('click', (e) => {
                    if (e.target.type !== 'radio') {
                        const radio = card.querySelector('input[type="radio"]');
                        if (radio) { radio.checked = true; radio.dispatchEvent(new Event('change')); }
                    }
                });
            });
        }

        // =====================================================================
        // STEP 6: SELECT 5 PROBLEM TITLES
        // =====================================================================

        async initStep6() {
            if (this._step6Running) return;
            this._step6Running = true;

            const list = document.getElementById('jc-problem-titles-list');
            const loading = document.getElementById('jc-problem-titles-loading');
            const regenBtn = document.getElementById('jc-regenerate-problem-titles');
            const countEl = document.getElementById('jc-problem-selection-count');

            if (!list) {
                this._step6Running = false;
                return;
            }

            // Bind regenerate
            if (regenBtn && !this._step6Bound) {
                this._step6Bound = true;
                regenBtn.addEventListener('click', () => this.loadProblems6(list, loading, regenBtn, countEl, true));
            }

            // Use suggestions from Step 5 if available, otherwise generate fresh
            if (this.problemSuggestions.length === 0) {
                await this.loadProblems6(list, loading, regenBtn, countEl, false);
            } else {
                this.renderStep6List(list, countEl);
            }

            this._step6Running = false;
        }

        async loadProblems6(list, loading, regenBtn, countEl, forceRefresh) {
            if (loading) loading.style.display = 'flex';
            if (regenBtn) regenBtn.disabled = true;
            list.innerHTML = '';

            const state = this.workflow.getState();

            try {
                const response = await fetch(`${this.apiBase}/ai/generate-problem-titles`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-WP-Nonce': this.nonce
                    },
                    body: JSON.stringify({
                        service_area_id: state.serviceAreaId || 0,
                        service_area_name: '',
                        industries: state.industries || [],
                        brain_content: state.brainContent || [],
                        force_refresh: forceRefresh
                    })
                });

                const data = await response.json();

                if (data.success && data.titles && data.titles.length > 0) {
                    this.problemSuggestions = data.titles.map((t, i) => ({
                        id: `prob_${i}`,
                        title: typeof t === 'string' ? t : (t.title || t.text || String(t))
                    }));
                    this.renderStep6List(list, countEl);
                } else {
                    throw new Error(data.error || 'No suggestions generated');
                }
            } catch (error) {
                console.error('Problem title generation error:', error);
                this.renderManualEntry(list, 'problem-title');
            } finally {
                if (loading) loading.style.display = 'none';
                if (regenBtn) regenBtn.disabled = false;
            }
        }

        renderStep6List(container, countEl) {
            container.innerHTML = this.problemSuggestions.map((p, i) => {
                const isSelected = this.selectedProblems.some(sp => sp.id === p.id);
                return `
                    <div class="jc-problem-checkbox-card"
                         data-id="${p.id}"
                         style="padding:12px;margin-bottom:8px;border:2px solid ${isSelected ? '#28a745' : '#ddd'};border-radius:6px;cursor:pointer;background:${isSelected ? '#f0fff4' : '#fff'};transition:all .2s">
                        <label style="display:flex;align-items:center;gap:12px;cursor:pointer">
                            <input type="checkbox" class="jc-problem-checkbox" value="${p.id}"
                                   data-title="${this.esc(p.title)}"
                                   ${isSelected ? 'checked' : ''}
                                   style="width:18px;height:18px">
                            <span style="background:#e74c3c;color:#fff;border-radius:50%;min-width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px">${i + 1}</span>
                            <span style="flex:1;font-size:14px">${this.esc(p.title)}</span>
                        </label>
                    </div>
                `;
            }).join('');

            this.updateStep6Count(countEl);

            // Bind checkbox changes
            container.querySelectorAll('.jc-problem-checkbox').forEach(cb => {
                cb.addEventListener('change', () => {
                    const checked = container.querySelectorAll('.jc-problem-checkbox:checked');
                    
                    // Enforce max 5
                    if (checked.length > 5) {
                        cb.checked = false;
                        this.workflow.showNotification('You can only select 5 problem titles', 'warning');
                        return;
                    }

                    // Update selected problems
                    this.selectedProblems = Array.from(checked).map(c => ({
                        id: c.value,
                        title: c.dataset.title
                    }));

                    this.workflow.updateState('selectedProblems', this.selectedProblems);
                    this.updateStep6Count(countEl);

                    // Update card styles
                    container.querySelectorAll('.jc-problem-checkbox-card').forEach(card => {
                        const input = card.querySelector('.jc-problem-checkbox');
                        const sel = input && input.checked;
                        card.style.borderColor = sel ? '#28a745' : '#ddd';
                        card.style.background = sel ? '#f0fff4' : '#fff';
                    });
                });
            });

            // Card click
            container.querySelectorAll('.jc-problem-checkbox-card').forEach(card => {
                card.addEventListener('click', (e) => {
                    if (e.target.type !== 'checkbox') {
                        const cb = card.querySelector('.jc-problem-checkbox');
                        if (cb) { cb.checked = !cb.checked; cb.dispatchEvent(new Event('change')); }
                    }
                });
            });
        }

        updateStep6Count(countEl) {
            if (countEl) {
                countEl.textContent = this.selectedProblems.length;
                countEl.style.color = this.selectedProblems.length === 5 ? '#28a745' : '#dc3545';
            }
        }

        // =====================================================================
        // STEP 7: SELECT SOLUTION TITLES
        // =====================================================================

        async initStep7() {
            if (this._step7Running) return;
            this._step7Running = true;

            const container = document.getElementById('jc-solution-mapping-container');
            const loading = document.getElementById('jc-solution-titles-loading');
            const regenBtn = document.getElementById('jc-regenerate-solutions');

            if (!container) {
                this._step7Running = false;
                return;
            }

            // Check we have problems selected
            if (this.selectedProblems.length === 0) {
                container.innerHTML = `
                    <div style="padding:20px;text-align:center;color:#666">
                        <i class="fas fa-exclamation-circle" style="font-size:2em;margin-bottom:10px;display:block"></i>
                        <p>Please go back to Step 6 and select 5 problem titles first.</p>
                    </div>`;
                this._step7Running = false;
                return;
            }

            // Bind regenerate
            if (regenBtn && !this._step7Bound) {
                this._step7Bound = true;
                regenBtn.addEventListener('click', () => this.loadAllSolutions(container, loading, regenBtn, true));
            }

            // Load solutions
            if (Object.keys(this.solutionSuggestions).length === 0) {
                await this.loadAllSolutions(container, loading, regenBtn, false);
            } else {
                this.renderStep7(container);
            }

            this._step7Running = false;
        }

        async loadAllSolutions(container, loading, regenBtn, forceRefresh) {
            if (loading) loading.style.display = 'flex';
            if (regenBtn) regenBtn.disabled = true;
            container.innerHTML = '';

            const state = this.workflow.getState();

            try {
                // Generate solutions for each selected problem
                for (const problem of this.selectedProblems) {
                    const response = await fetch(`${this.apiBase}/ai/generate-solution-titles`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-WP-Nonce': this.nonce
                        },
                        body: JSON.stringify({
                            problem_id: problem.id,
                            problem_title: problem.title,
                            service_area_id: state.serviceAreaId || 0,
                            service_area_name: '',
                            industries: state.industries || [],
                            brain_content: state.brainContent || [],
                            force_refresh: forceRefresh
                        })
                    });

                    const data = await response.json();

                    if (data.success && data.titles && data.titles.length > 0) {
                        this.solutionSuggestions[problem.id] = data.titles.map(t =>
                            typeof t === 'string' ? t : (t.title || t.text || String(t))
                        );
                    } else {
                        // Provide manual entry option for this problem
                        this.solutionSuggestions[problem.id] = [];
                    }
                }

                this.renderStep7(container);
            } catch (error) {
                console.error('Solution generation error:', error);
                container.innerHTML = `
                    <div style="padding:20px;text-align:center;color:#856404;background:#fff3cd;border:1px solid #ffc107;border-radius:6px">
                        <p><strong>AI generation failed:</strong> ${this.esc(error.message)}</p>
                        <p>You can manually enter solution titles for each problem.</p>
                    </div>`;
                // Render manual entry for all problems
                this.selectedProblems.forEach(p => { this.solutionSuggestions[p.id] = []; });
                this.renderStep7(container);
            } finally {
                if (loading) loading.style.display = 'none';
                if (regenBtn) regenBtn.disabled = false;
            }
        }

        renderStep7(container) {
            container.innerHTML = this.selectedProblems.map((problem, pi) => {
                const solutions = this.solutionSuggestions[problem.id] || [];
                const selectedSol = this.selectedSolutions[problem.id] || '';
                const hasSolutions = solutions.length > 0;

                return `
                    <div class="jc-solution-group" style="margin-bottom:24px;padding:16px;border:1px solid #ddd;border-radius:8px;background:#fafafa">
                        <h4 style="margin:0 0 4px 0;color:#e74c3c;font-size:13px;text-transform:uppercase;letter-spacing:.5px">
                            Problem ${pi + 1}
                        </h4>
                        <p style="margin:0 0 12px 0;font-weight:600;font-size:15px">${this.esc(problem.title)}</p>
                        
                        <div style="margin-left:12px">
                            <p style="margin:0 0 8px 0;color:#42a5f5;font-weight:600;font-size:13px">
                                <i class="fas fa-arrow-right"></i> Select a Solution:
                            </p>
                            ${hasSolutions ? solutions.map((sol, si) => `
                                <div style="padding:8px 12px;margin-bottom:6px;border:2px solid ${selectedSol === sol ? '#42a5f5' : '#e0e0e0'};border-radius:4px;cursor:pointer;background:${selectedSol === sol ? '#e3f2fd' : '#fff'};transition:all .2s">
                                    <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
                                        <input type="radio" name="solution_${problem.id}" value="${this.esc(sol)}"
                                               class="jc-solution-radio" data-problem-id="${problem.id}"
                                               ${selectedSol === sol ? 'checked' : ''}
                                               style="width:16px;height:16px">
                                        <span style="flex:1;font-size:14px">${this.esc(sol)}</span>
                                    </label>
                                </div>
                            `).join('') : ''}
                            <div style="margin-top:8px;display:flex;gap:8px">
                                <input type="text" class="jc-manual-solution-input" data-problem-id="${problem.id}"
                                       placeholder="Or type a custom solution..." 
                                       style="flex:1;padding:8px 12px;border:1px solid #ddd;border-radius:4px;font-size:14px">
                                <button type="button" class="button button-small jc-add-solution-btn" data-problem-id="${problem.id}">
                                    Add
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            // Bind solution radio changes
            container.querySelectorAll('.jc-solution-radio').forEach(radio => {
                radio.addEventListener('change', (e) => {
                    this.selectedSolutions[e.target.dataset.problemId] = e.target.value;
                    this.workflow.updateState('selectedSolutions', this.selectedSolutions);
                    this.renderStep7(container); // Re-render for styles
                });
            });

            // Bind manual solution add
            container.querySelectorAll('.jc-add-solution-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const problemId = btn.dataset.problemId;
                    const input = container.querySelector(`.jc-manual-solution-input[data-problem-id="${problemId}"]`);
                    if (!input || !input.value.trim()) return;

                    if (!this.solutionSuggestions[problemId]) {
                        this.solutionSuggestions[problemId] = [];
                    }
                    this.solutionSuggestions[problemId].push(input.value.trim());
                    input.value = '';
                    this.renderStep7(container);
                });
            });
        }

        // =====================================================================
        // MANUAL ENTRY FALLBACK (when AI is unavailable)
        // =====================================================================

        renderManualEntry(container, type) {
            container.innerHTML = `
                <div style="padding:16px;margin-bottom:16px;background:#fff3cd;border:1px solid #ffc107;border-radius:6px">
                    <p style="margin:0 0 8px 0"><i class="fas fa-exclamation-triangle"></i> <strong>AI suggestions unavailable.</strong></p>
                    <p style="margin:0">You can manually enter ${type === 'problem' ? 'problem statements' : 'problem titles'} below. The AI may not be configured or may be temporarily unavailable.</p>
                </div>
                <div id="jc-manual-entries"></div>
                <div style="display:flex;gap:8px;margin-top:12px">
                    <input type="text" id="jc-manual-entry-input" class="jc-input"
                           placeholder="Enter a ${type === 'problem' ? 'problem statement' : 'problem title'}..."
                           style="flex:1;padding:10px;border:1px solid #ddd;border-radius:4px">
                    <button type="button" class="button button-primary" id="jc-add-manual-entry">
                        <i class="fas fa-plus"></i> Add
                    </button>
                </div>
            `;

            const addBtn = container.querySelector('#jc-add-manual-entry');
            const input = container.querySelector('#jc-manual-entry-input');
            const entriesEl = container.querySelector('#jc-manual-entries');

            if (addBtn && input) {
                const addEntry = () => {
                    const title = input.value.trim();
                    if (!title) return;

                    this.problemSuggestions.push({
                        id: `manual_${Date.now()}`,
                        title: title
                    });
                    input.value = '';

                    // Determine which step we're on and re-render appropriately
                    const step5List = document.getElementById('jc-primary-problem-list');
                    const step6List = document.getElementById('jc-problem-titles-list');

                    if (container === step5List || container.closest('#jc-step-5')) {
                        this.renderStep5List(container);
                    } else {
                        const countEl = document.getElementById('jc-problem-selection-count');
                        this.renderStep6List(container, countEl);
                    }
                };

                addBtn.addEventListener('click', addEntry);
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') { e.preventDefault(); addEntry(); }
                });
            }
        }

        // =====================================================================
        // UTILITIES
        // =====================================================================

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
            window.drSteps567Manager = new Steps567Manager(window.drJourneyCircle);
        }
    });

})(jQuery);