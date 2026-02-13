/**
 * Journey Circle Renderer - Complete Canvas Visualization
 *
 * Renders the Journey Circle as concentric rings on an HTML5 canvas:
 *   - Outer ring (red):   5 Problem segments
 *   - Middle ring (blue): 5 Solution segments (1:1 mapped to problems)
 *   - Center circle (green): Offer count
 *
 * All data is fetched from the database via REST API.
 * No mock/hardcoded data is used.
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 *
 * Usage:
 *   const renderer = new JourneyCircleRenderer('journey-circle-canvas', {
 *       circleId: 123,
 *       restUrl: '/wp-json/directreach/v2/',
 *       nonce: '...'
 *   });
 *   renderer.init();
 *
 * To refresh after data changes:
 *   renderer.refresh();
 */

(function(window, document) {
    'use strict';

    /* ====================================================================
     * Constants
     * ==================================================================== */

    const DEFAULTS = {
        // Canvas dimensions (logical pixels; CSS handles display size)
        width:  700,
        height: 700,

        // Ring geometry
        outerRingRadius:  280,
        middleRingRadius: 200,
        centerRadius:     80,
        ringWidth:        40,

        // Node sizes
        nodeRadius:      20,   // Problem nodes
        nodeRadiusSmall: 16,   // Solution nodes

        // Segment count
        segmentCount: 5,

        // Colors — from design doc
        colors: {
            problemRing:      '#ff6b6b',
            problemRingLight: '#ff8a8a',
            solutionRing:      '#42a5f5',
            solutionRingLight: '#64b5f6',
            offerCenter:       '#66bb6a',
            offerCenterLight:  '#81c784',
            divider:           '#ffffff',
            nodeBackground:    '#ffffff',
            nodeText:          '#333333',
            primaryIndicator:  '#ffca28',
            connectionLine:    'rgba(255,255,255,0.35)',
            emptyState:        '#e0e0e0',
            emptyStateText:    '#9e9e9e',
            labelText:         '#ffffff',
            canvasBackground:  'transparent'
        },

        // Typography
        fonts: {
            nodeLabel:    'bold 14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            centerCount:  'bold 28px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            centerLabel:  '13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            ringLabel:    '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            emptyLabel:   '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            titleTrunc:   '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        },

        // Animation
        animationDuration: 600,  // ms for draw-in animation
        animationEasing:   'easeOutCubic',

        // REST / data
        restUrl:  '',
        nonce:    '',
        circleId: 0
    };

    /* ====================================================================
     * Easing helpers
     * ==================================================================== */

    const EASINGS = {
        linear:       t => t,
        easeOutCubic: t => 1 - Math.pow(1 - t, 3),
        easeOutQuad:  t => 1 - (1 - t) * (1 - t),
        easeInOutCubic: t => t < 0.5
            ? 4 * t * t * t
            : 1 - Math.pow(-2 * t + 2, 3) / 2
    };

    /* ====================================================================
     * JourneyCircleRenderer Class
     * ==================================================================== */

    class JourneyCircleRenderer {

        /**
         * @param {HTMLCanvasElement|string} canvas  Canvas element or its ID
         * @param {Object}                   options Overrides for DEFAULTS
         */
        constructor(canvas, options = {}) {
            // Resolve canvas element
            this.canvas = typeof canvas === 'string'
                ? document.getElementById(canvas)
                : canvas;

            if (!this.canvas || this.canvas.tagName !== 'CANVAS') {
                console.error('[JourneyCircleRenderer] Invalid canvas element.');
                return;
            }

            this.ctx = this.canvas.getContext('2d');

            // Merge config
            this.config = Object.assign({}, DEFAULTS, options);
            this.config.colors = Object.assign({}, DEFAULTS.colors, options.colors || {});
            this.config.fonts  = Object.assign({}, DEFAULTS.fonts,  options.fonts  || {});

            // Data containers — always start empty, populated from API
            this.data = {
                problems:  [],
                solutions: [],
                offers:    [],
                loaded:    false,
                loading:   false,
                error:     null
            };

            // Animation state
            this._anim = {
                progress:  0,
                startTime: null,
                rafId:     null,
                running:   false
            };

            // Pixel-ratio for Retina / HiDPI
            this.dpr = window.devicePixelRatio || 1;
        }

        /* ----------------------------------------------------------------
         * Public API
         * ---------------------------------------------------------------- */

        /**
         * Initialise: size canvas, fetch data, render.
         *
         * @returns {Promise<void>}
         */
        async init() {
            this._setupCanvas();
            this._drawLoading();

            try {
                await this.fetchData();
                this._animate();
            } catch (err) {
                console.error('[JourneyCircleRenderer] init error:', err);
                this._drawError(err.message || 'Failed to load circle data.');
            }
        }

        /**
         * Re-fetch data from the API and re-draw.
         *
         * @returns {Promise<void>}
         */
        async refresh() {
            this._cancelAnimation();
            this._drawLoading();

            try {
                await this.fetchData();
                this._animate();
            } catch (err) {
                console.error('[JourneyCircleRenderer] refresh error:', err);
                this._drawError(err.message || 'Failed to refresh circle data.');
            }
        }

        /**
         * Redraw at current progress (no data fetch).
         */
        redraw() {
            this._render(1);
        }

        /**
         * Programmatically supply data instead of fetching.
         * Useful when parent modules already have the data.
         *
         * @param {Object} payload  { problems:[], solutions:[], offers:[] }
         */
        setData(payload = {}) {
            this.data.problems  = Array.isArray(payload.problems)  ? payload.problems  : [];
            this.data.solutions = Array.isArray(payload.solutions) ? payload.solutions : [];
            this.data.offers    = Array.isArray(payload.offers)    ? payload.offers    : [];
            this.data.loaded    = true;
            this.data.error     = null;

            this._cancelAnimation();
            this._animate();
        }

        /**
         * Fetch problems, solutions, and offers from the REST API.
         *
         * @returns {Promise<void>}
         */
        async fetchData() {
            const { restUrl, nonce, circleId } = this.config;

            if (!circleId) {
                this.data.problems  = [];
                this.data.solutions = [];
                this.data.offers    = [];
                this.data.loaded    = true;
                return;
            }

            this.data.loading = true;
            this.data.error   = null;

            const headers = {
                'Content-Type': 'application/json'
            };
            if (nonce) {
                headers['X-WP-Nonce'] = nonce;
            }

            const fetchJSON = async (endpoint) => {
                const url = `${restUrl.replace(/\/+$/, '')}/${endpoint}`;
                const res = await fetch(url, { headers, credentials: 'same-origin' });
                if (!res.ok) {
                    // 404 is acceptable — means no data yet
                    if (res.status === 404) return [];
                    throw new Error(`API ${res.status}: ${res.statusText}`);
                }
                const json = await res.json();
                return Array.isArray(json) ? json : (json.data || json.items || []);
            };

            try {
                const [problems, solutions, offers] = await Promise.all([
                    fetchJSON(`journey-circles/${circleId}/problems`),
                    fetchJSON(`journey-circles/${circleId}/solutions`),
                    fetchJSON(`journey-circles/${circleId}/offers`)
                ]);

                this.data.problems  = problems;
                this.data.solutions = solutions;
                this.data.offers    = offers;
                this.data.loaded    = true;
            } catch (err) {
                this.data.error = err.message;
                throw err;
            } finally {
                this.data.loading = false;
            }
        }

        /**
         * Export canvas as PNG data-URL.
         *
         * @returns {string}
         */
        toDataURL() {
            return this.canvas.toDataURL('image/png');
        }

        /**
         * Trigger download of the canvas as a PNG file.
         *
         * @param {string} filename
         */
        downloadAsImage(filename = 'journey-circle.png') {
            const a  = document.createElement('a');
            a.download = filename;
            a.href     = this.toDataURL();
            a.click();
        }

        /**
         * Resize the canvas (logical pixels). Re-renders.
         *
         * @param {number} width
         * @param {number} height
         */
        resize(width, height) {
            this.config.width  = width;
            this.config.height = height;
            this._setupCanvas();

            if (this.data.loaded) {
                this._render(1);
            }
        }

        /**
         * Clean up animation frames and references.
         */
        destroy() {
            this._cancelAnimation();
            this.ctx    = null;
            this.canvas = null;
        }

        /* ----------------------------------------------------------------
         * Canvas setup helpers
         * ---------------------------------------------------------------- */

        /**
         * Configure canvas buffer size (accounts for device pixel ratio)
         * and CSS display size.
         * @private
         */
        _setupCanvas() {
            const { width, height } = this.config;
            const dpr = this.dpr;

            this.canvas.width  = width  * dpr;
            this.canvas.height = height * dpr;
            this.canvas.style.width  = width  + 'px';
            this.canvas.style.height = height + 'px';

            this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        /* ----------------------------------------------------------------
         * Animation
         * ---------------------------------------------------------------- */

        /** @private */
        _animate() {
            this._cancelAnimation();

            const duration = this.config.animationDuration;
            const easing   = EASINGS[this.config.animationEasing] || EASINGS.easeOutCubic;

            this._anim.progress  = 0;
            this._anim.startTime = null;
            this._anim.running   = true;

            const tick = (ts) => {
                if (!this._anim.running) return;

                if (!this._anim.startTime) this._anim.startTime = ts;
                const elapsed = ts - this._anim.startTime;
                const raw     = Math.min(elapsed / duration, 1);

                this._anim.progress = easing(raw);
                this._render(this._anim.progress);

                if (raw < 1) {
                    this._anim.rafId = requestAnimationFrame(tick);
                } else {
                    this._anim.running = false;
                }
            };

            this._anim.rafId = requestAnimationFrame(tick);
        }

        /** @private */
        _cancelAnimation() {
            if (this._anim.rafId) {
                cancelAnimationFrame(this._anim.rafId);
                this._anim.rafId = null;
            }
            this._anim.running = false;
        }

        /* ----------------------------------------------------------------
         * Core rendering pipeline
         * ---------------------------------------------------------------- */

        /**
         * Master render call.
         *
         * @param {number} progress  0→1 animation progress
         * @private
         */
        _render(progress) {
            const ctx = this.ctx;
            const { width, height, colors } = this.config;

            // Clear
            ctx.clearRect(0, 0, width, height);

            // Optional background
            if (colors.canvasBackground && colors.canvasBackground !== 'transparent') {
                ctx.fillStyle = colors.canvasBackground;
                ctx.fillRect(0, 0, width, height);
            }

            const cx = width  / 2;
            const cy = height / 2;

            const hasProblems  = this.data.problems.length  > 0;
            const hasSolutions = this.data.solutions.length > 0;
            const hasOffers    = this.data.offers.length    > 0;

            // Draw from inside out (painter's order: background first)
            // 1. Connection lines (behind everything)
            if (hasProblems && hasSolutions) {
                this._drawConnections(cx, cy, progress);
            }

            // 2. Outer ring — problems
            this._drawRing(cx, cy, progress, 'problem');

            // 3. Middle ring — solutions
            this._drawRing(cx, cy, progress, 'solution');

            // 4. Center circle — offers
            this._drawCenter(cx, cy, progress);

            // 5. Nodes on rings
            if (hasProblems) {
                this._drawNodes(cx, cy, progress, 'problem');
            }
            if (hasSolutions) {
                this._drawNodes(cx, cy, progress, 'solution');
            }

            // 6. Ring labels (outside the rings)
            this._drawRingLabels(cx, cy, progress);

            // 7. Empty-state overlay when nothing loaded yet
            if (!hasProblems && !hasSolutions && !hasOffers) {
                this._drawEmptyState(cx, cy);
            }
        }

        /* ----------------------------------------------------------------
         * Ring drawing
         * ---------------------------------------------------------------- */

        /**
         * Draw a segmented ring (outer for problems, middle for solutions).
         *
         * @param {number} cx        Center X
         * @param {number} cy        Center Y
         * @param {number} progress  Animation 0→1
         * @param {string} type      'problem' | 'solution'
         * @private
         */
        _drawRing(cx, cy, progress, type) {
            const ctx    = this.ctx;
            const cfg    = this.config;
            const colors = cfg.colors;
            const count  = cfg.segmentCount;

            const isProblem = type === 'problem';
            const radius    = isProblem ? cfg.outerRingRadius  : cfg.middleRingRadius;
            const baseColor = isProblem ? colors.problemRing   : colors.solutionRing;
            const lightColor= isProblem ? colors.problemRingLight : colors.solutionRingLight;
            const items     = isProblem ? this.data.problems   : this.data.solutions;
            const hasData   = items.length > 0;

            const segAngle   = (Math.PI * 2) / count;
            const startAngle = -Math.PI / 2;  // 12 o'clock

            // Animated radius
            const r     = radius * progress;
            const rw    = cfg.ringWidth * progress;
            const inner = r - rw;

            for (let i = 0; i < count; i++) {
                const a0 = startAngle + segAngle * i;
                const a1 = a0 + segAngle;

                // Determine fill
                let fill;
                if (hasData && i < items.length) {
                    // Filled segment
                    fill = baseColor;
                } else if (hasData) {
                    // Extra empty slot (shouldn't happen with exactly 5, but defensive)
                    fill = this._hexToRGBA(baseColor, 0.25);
                } else {
                    // No data at all — ghost ring
                    fill = this._hexToRGBA(colors.emptyState, 0.35);
                }

                // Draw arc segment
                ctx.beginPath();
                ctx.arc(cx, cy, r, a0, a1);
                ctx.arc(cx, cy, Math.max(inner, 0), a1, a0, true);
                ctx.closePath();
                ctx.fillStyle = fill;
                ctx.fill();

                // Divider line
                if (progress > 0.3) {
                    const divAlpha = Math.min((progress - 0.3) / 0.4, 1);
                    ctx.beginPath();
                    ctx.moveTo(
                        cx + Math.cos(a0) * Math.max(inner, 0),
                        cy + Math.sin(a0) * Math.max(inner, 0)
                    );
                    ctx.lineTo(
                        cx + Math.cos(a0) * r,
                        cy + Math.sin(a0) * r
                    );
                    ctx.strokeStyle = this._hexToRGBA(colors.divider, 0.8 * divAlpha);
                    ctx.lineWidth   = 2;
                    ctx.stroke();
                }
            }

            // Outer edge stroke for definition
            if (hasData && progress > 0.5) {
                const edgeAlpha = (progress - 0.5) / 0.5;
                ctx.beginPath();
                ctx.arc(cx, cy, r, 0, Math.PI * 2);
                ctx.strokeStyle = this._hexToRGBA(lightColor, 0.4 * edgeAlpha);
                ctx.lineWidth   = 1;
                ctx.stroke();

                ctx.beginPath();
                ctx.arc(cx, cy, Math.max(inner, 0), 0, Math.PI * 2);
                ctx.stroke();
            }
        }

        /* ----------------------------------------------------------------
         * Center circle
         * ---------------------------------------------------------------- */

        /**
         * Draw the green center circle with offer count.
         *
         * @param {number} cx
         * @param {number} cy
         * @param {number} progress
         * @private
         */
        _drawCenter(cx, cy, progress) {
            const ctx    = this.ctx;
            const cfg    = this.config;
            const colors = cfg.colors;
            const r      = cfg.centerRadius * progress;

            const offerCount = this.data.offers.length;
            const hasOffers  = offerCount > 0;

            // Circle fill
            const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
            if (hasOffers) {
                gradient.addColorStop(0, colors.offerCenterLight);
                gradient.addColorStop(1, colors.offerCenter);
            } else {
                gradient.addColorStop(0, this._hexToRGBA(colors.emptyState, 0.3));
                gradient.addColorStop(1, this._hexToRGBA(colors.emptyState, 0.5));
            }

            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.fillStyle = gradient;
            ctx.fill();

            // Subtle border
            ctx.strokeStyle = hasOffers
                ? this._hexToRGBA(colors.offerCenter, 0.6)
                : this._hexToRGBA(colors.emptyState, 0.3);
            ctx.lineWidth = 2;
            ctx.stroke();

            // Text — only show after animation mostly done
            if (progress > 0.6) {
                const textAlpha = Math.min((progress - 0.6) / 0.3, 1);

                // Count number
                ctx.font      = cfg.fonts.centerCount;
                ctx.textAlign  = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = hasOffers
                    ? this._hexToRGBA(colors.nodeBackground, textAlpha)
                    : this._hexToRGBA(colors.emptyStateText, textAlpha);
                ctx.fillText(String(offerCount), cx, cy - 8);

                // Label
                ctx.font      = cfg.fonts.centerLabel;
                ctx.fillStyle = hasOffers
                    ? this._hexToRGBA(colors.nodeBackground, 0.85 * textAlpha)
                    : this._hexToRGBA(colors.emptyStateText, 0.7 * textAlpha);
                ctx.fillText(offerCount === 1 ? 'Offer' : 'Offers', cx, cy + 16);
            }
        }

        /* ----------------------------------------------------------------
         * Nodes
         * ---------------------------------------------------------------- */

        /**
         * Draw numbered node circles on ring segments.
         *
         * @param {number} cx
         * @param {number} cy
         * @param {number} progress
         * @param {string} type  'problem' | 'solution'
         * @private
         */
        _drawNodes(cx, cy, progress, type) {
            const ctx    = this.ctx;
            const cfg    = this.config;
            const colors = cfg.colors;

            const isProblem = type === 'problem';
            const items     = isProblem ? this.data.problems : this.data.solutions;
            const radius    = isProblem ? cfg.outerRingRadius  : cfg.middleRingRadius;
            const nodeR     = isProblem ? cfg.nodeRadius        : cfg.nodeRadiusSmall;
            const ringW     = cfg.ringWidth;
            const count     = cfg.segmentCount;
            const segAngle  = (Math.PI * 2) / count;
            const startAngle = -Math.PI / 2;

            // Only show nodes once ring is mostly drawn
            if (progress < 0.4) return;
            const nodeAlpha = Math.min((progress - 0.4) / 0.4, 1);

            items.forEach((item, idx) => {
                const pos = (typeof item.position !== 'undefined') ? item.position : idx;
                if (pos >= count) return;

                const midAngle = startAngle + segAngle * pos + segAngle / 2;
                const nodeRad  = radius - ringW / 2;

                const nx = cx + Math.cos(midAngle) * nodeRad * progress;
                const ny = cy + Math.sin(midAngle) * nodeRad * progress;
                const nr = nodeR * nodeAlpha;

                // Primary problem indicator — golden ring
                if (isProblem && item.is_primary) {
                    ctx.beginPath();
                    ctx.arc(nx, ny, nr + 4, 0, Math.PI * 2);
                    ctx.strokeStyle = this._hexToRGBA(colors.primaryIndicator, nodeAlpha);
                    ctx.lineWidth   = 3;
                    ctx.stroke();
                }

                // Node circle
                ctx.beginPath();
                ctx.arc(nx, ny, nr, 0, Math.PI * 2);

                // Shadow
                ctx.shadowColor   = 'rgba(0,0,0,0.15)';
                ctx.shadowBlur    = 4 * nodeAlpha;
                ctx.shadowOffsetY = 2 * nodeAlpha;
                ctx.fillStyle     = this._hexToRGBA(colors.nodeBackground, nodeAlpha);
                ctx.fill();
                ctx.shadowColor   = 'transparent';
                ctx.shadowBlur    = 0;
                ctx.shadowOffsetY = 0;

                // Border matching ring color
                const borderColor = isProblem ? colors.problemRing : colors.solutionRing;
                ctx.strokeStyle = this._hexToRGBA(borderColor, 0.6 * nodeAlpha);
                ctx.lineWidth   = 2;
                ctx.stroke();

                // Number label
                ctx.font         = cfg.fonts.nodeLabel;
                ctx.textAlign    = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle    = this._hexToRGBA(colors.nodeText, nodeAlpha);
                ctx.fillText(String(pos + 1), nx, ny);
            });
        }

        /* ----------------------------------------------------------------
         * Connection lines
         * ---------------------------------------------------------------- */

        /**
         * Draw lines from each problem node → matched solution node → center.
         *
         * @param {number} cx
         * @param {number} cy
         * @param {number} progress
         * @private
         */
        _drawConnections(cx, cy, progress) {
            const ctx    = this.ctx;
            const cfg    = this.config;
            const colors = cfg.colors;
            const count  = cfg.segmentCount;
            const segAngle   = (Math.PI * 2) / count;
            const startAngle = -Math.PI / 2;

            if (progress < 0.5) return;
            const lineAlpha = Math.min((progress - 0.5) / 0.4, 1);

            // Build lookup: problem position → solution
            const solutionByProblemId = {};
            this.data.solutions.forEach(s => {
                solutionByProblemId[s.problem_id] = s;
            });

            this.data.problems.forEach((problem, idx) => {
                const pPos     = (typeof problem.position !== 'undefined') ? problem.position : idx;
                if (pPos >= count) return;

                const midAngle = startAngle + segAngle * pPos + segAngle / 2;

                // Problem node position
                const pRad = cfg.outerRingRadius - cfg.ringWidth / 2;
                const px   = cx + Math.cos(midAngle) * pRad;
                const py   = cy + Math.sin(midAngle) * pRad;

                // Solution node position (same angular position if matched)
                const sol = solutionByProblemId[problem.id];
                if (sol) {
                    const sPos     = (typeof sol.position !== 'undefined') ? sol.position : pPos;
                    const sMidAngle = startAngle + segAngle * sPos + segAngle / 2;
                    const sRad = cfg.middleRingRadius - cfg.ringWidth / 2;
                    const sx   = cx + Math.cos(sMidAngle) * sRad;
                    const sy   = cy + Math.sin(sMidAngle) * sRad;

                    // Problem → Solution
                    ctx.beginPath();
                    ctx.moveTo(px, py);
                    ctx.lineTo(sx, sy);
                    ctx.strokeStyle = this._hexToRGBA(colors.connectionLine.replace('rgba(','').replace(')','') 
                        ? colors.connectionLine 
                        : '#ffffff', 0.35 * lineAlpha);
                    // Safer: just use the configured color
                    ctx.strokeStyle = colors.connectionLine;
                    ctx.globalAlpha = lineAlpha;
                    ctx.lineWidth   = 1.5;
                    ctx.setLineDash([4, 4]);
                    ctx.stroke();
                    ctx.setLineDash([]);

                    // Solution → Center
                    ctx.beginPath();
                    ctx.moveTo(sx, sy);
                    ctx.lineTo(cx, cy);
                    ctx.stroke();

                    ctx.globalAlpha = 1;
                } else {
                    // No matched solution — draw faded line to center only
                    ctx.beginPath();
                    ctx.moveTo(px, py);
                    ctx.lineTo(cx, cy);
                    ctx.strokeStyle = colors.connectionLine;
                    ctx.globalAlpha = lineAlpha * 0.2;
                    ctx.lineWidth   = 1;
                    ctx.setLineDash([2, 6]);
                    ctx.stroke();
                    ctx.setLineDash([]);
                    ctx.globalAlpha = 1;
                }
            });
        }

        /* ----------------------------------------------------------------
         * Ring labels
         * ---------------------------------------------------------------- */

        /**
         * Draw text labels outside the rings identifying them.
         *
         * @param {number} cx
         * @param {number} cy
         * @param {number} progress
         * @private
         */
        _drawRingLabels(cx, cy, progress) {
            if (progress < 0.7) return;

            const ctx    = this.ctx;
            const cfg    = this.config;
            const colors = cfg.colors;
            const alpha  = Math.min((progress - 0.7) / 0.3, 1);

            ctx.font         = cfg.fonts.ringLabel;
            ctx.textAlign    = 'center';
            ctx.textBaseline = 'middle';

            const hasProblems  = this.data.problems.length > 0;
            const hasSolutions = this.data.solutions.length > 0;

            // Problem ring label — top outside
            const pLabelY = cy - cfg.outerRingRadius - 12;
            ctx.fillStyle = hasProblems
                ? this._hexToRGBA(colors.problemRing, alpha)
                : this._hexToRGBA(colors.emptyStateText, alpha * 0.6);
            ctx.fillText(
                hasProblems
                    ? `PROBLEMS (${this.data.problems.length})`
                    : 'PROBLEMS',
                cx, pLabelY
            );

            // Solution ring label — bottom inside gap
            const sLabelY = cy + cfg.outerRingRadius + 14;
            ctx.fillStyle = hasSolutions
                ? this._hexToRGBA(colors.solutionRing, alpha)
                : this._hexToRGBA(colors.emptyStateText, alpha * 0.6);
            ctx.fillText(
                hasSolutions
                    ? `SOLUTIONS (${this.data.solutions.length})`
                    : 'SOLUTIONS',
                cx, sLabelY
            );
        }

        /* ----------------------------------------------------------------
         * Empty & loading states
         * ---------------------------------------------------------------- */

        /**
         * Show empty-state overlay when there's no data at all.
         *
         * @param {number} cx
         * @param {number} cy
         * @private
         */
        _drawEmptyState(cx, cy) {
            const ctx    = this.ctx;
            const cfg    = this.config;
            const colors = cfg.colors;

            ctx.font         = cfg.fonts.emptyLabel;
            ctx.textAlign    = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle    = colors.emptyStateText;
            ctx.fillText('Complete Steps 5–8 to populate', cx, cy + cfg.centerRadius + 30);
            ctx.fillText('your Journey Circle.', cx, cy + cfg.centerRadius + 50);
        }

        /**
         * Draw a simple loading indicator.
         * @private
         */
        _drawLoading() {
            const ctx = this.ctx;
            const { width, height, colors } = this.config;
            const cx = width / 2;
            const cy = height / 2;

            ctx.clearRect(0, 0, width, height);

            // Pulsing circle
            ctx.beginPath();
            ctx.arc(cx, cy, 40, 0, Math.PI * 2);
            ctx.fillStyle = this._hexToRGBA(colors.emptyState, 0.3);
            ctx.fill();

            ctx.font         = this.config.fonts.emptyLabel;
            ctx.textAlign    = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle    = colors.emptyStateText;
            ctx.fillText('Loading…', cx, cy);
        }

        /**
         * Draw error state.
         *
         * @param {string} message
         * @private
         */
        _drawError(message) {
            const ctx = this.ctx;
            const { width, height, colors } = this.config;
            const cx = width / 2;
            const cy = height / 2;

            ctx.clearRect(0, 0, width, height);

            ctx.font         = this.config.fonts.emptyLabel;
            ctx.textAlign    = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle    = '#e53935';
            ctx.fillText('⚠ ' + message, cx, cy);

            ctx.font      = this.config.fonts.ringLabel;
            ctx.fillStyle = colors.emptyStateText;
            ctx.fillText('Click refresh to retry.', cx, cy + 24);
        }

        /* ----------------------------------------------------------------
         * Utility helpers
         * ---------------------------------------------------------------- */

        /**
         * Convert hex colour to rgba string.
         *
         * @param {string} hex   e.g. '#ff6b6b'
         * @param {number} alpha 0–1
         * @returns {string}
         * @private
         */
        _hexToRGBA(hex, alpha) {
            if (!hex || hex.startsWith('rgba')) {
                // Already rgba or falsy — return as-is with new alpha if possible
                if (hex && typeof alpha === 'number') {
                    return hex.replace(/[\d.]+\)$/, alpha + ')');
                }
                return hex || 'transparent';
            }
            hex = hex.replace('#', '');
            if (hex.length === 3) {
                hex = hex[0]+hex[0] + hex[1]+hex[1] + hex[2]+hex[2];
            }
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);
            return `rgba(${r},${g},${b},${alpha})`;
        }
    }

    /* ====================================================================
     * Export
     * ==================================================================== */

    // Expose globally for WordPress script dependency model
    window.JourneyCircleRenderer = JourneyCircleRenderer;

    // Also support ES-module-style if a bundler picks this up
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = JourneyCircleRenderer;
    }

})(window, document);
