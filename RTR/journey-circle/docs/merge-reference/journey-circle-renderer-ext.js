/**
 * Journey Circle Canvas Renderer Extensions
 *
 * Extends the base JourneyCircleRenderer with solution ring and offer center
 * visualization capabilities for Steps 7-8.
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */

(function(window, document) {
    'use strict';

    /**
     * Extend the existing JourneyCircleRenderer if it exists,
     * or create a new one with solution/offer capabilities
     */

    // Check if base renderer exists
    const BaseRenderer = window.JourneyCircleRenderer || null;

    /**
     * JourneyCircleRendererExtended Class
     *
     * Enhanced renderer with solution and offer visualization
     */
    class JourneyCircleRendererExtended {
        /**
         * Constructor
         *
         * @param {HTMLCanvasElement|string} canvas Canvas element or ID
         * @param {Object} options Configuration options
         */
        constructor(canvas, options = {}) {
            // Get canvas element
            this.canvas = typeof canvas === 'string' 
                ? document.getElementById(canvas) 
                : canvas;

            if (!this.canvas || !this.canvas.getContext) {
                console.error('Invalid canvas element');
                return;
            }

            this.ctx = this.canvas.getContext('2d');

            // Configuration
            this.config = {
                // Canvas dimensions
                width: options.width || 700,
                height: options.height || 700,
                
                // Ring dimensions (from design specs)
                outerRingRadius: options.outerRingRadius || 280, // Problems
                middleRingRadius: options.middleRingRadius || 200, // Solutions
                centerCircleRadius: options.centerCircleRadius || 80, // Offers
                ringWidth: options.ringWidth || 40,
                
                // Colors
                problemColor: options.problemColor || '#ff6b6b',
                problemColorLight: options.problemColorLight || '#ffebee',
                solutionColor: options.solutionColor || '#42a5f5',
                solutionColorLight: options.solutionColorLight || '#e3f2fd',
                offerColor: options.offerColor || '#66bb6a',
                offerColorLight: options.offerColorLight || '#e8f5e9',
                lineColor: options.lineColor || '#ffffff',
                nodeColor: options.nodeColor || '#ffffff',
                textColor: options.textColor || '#333333',
                textColorLight: options.textColorLight || '#ffffff',
                
                // Node sizes
                nodeRadius: options.nodeRadius || 18,
                nodeRadiusSmall: options.nodeRadiusSmall || 14,
                
                // Animation
                animationEnabled: options.animationEnabled !== false,
                animationDuration: options.animationDuration || 500,
                
                ...options
            };

            // Data
            this.data = {
                problems: [],
                solutions: [],
                offers: [],
                primaryProblemId: null
            };

            // Animation state
            this.animationState = {
                progress: 1,
                animating: false,
                requestId: null
            };

            // Initialize
            this.init();
        }

        /**
         * Initialize the renderer
         */
        init() {
            // Set canvas size
            this.canvas.width = this.config.width;
            this.canvas.height = this.config.height;

            // Enable high DPI support
            this.setupHiDPI();

            // Initial render
            this.render();
        }

        /**
         * Setup High DPI (Retina) support
         */
        setupHiDPI() {
            const dpr = window.devicePixelRatio || 1;
            const rect = this.canvas.getBoundingClientRect();

            // Set actual size in memory
            this.canvas.width = rect.width * dpr;
            this.canvas.height = rect.height * dpr;

            // Scale canvas back down using CSS
            this.canvas.style.width = rect.width + 'px';
            this.canvas.style.height = rect.height + 'px';

            // Scale context
            this.ctx.scale(dpr, dpr);

            // Store logical dimensions
            this.logicalWidth = rect.width;
            this.logicalHeight = rect.height;
        }

        /**
         * Update data
         *
         * @param {Object} data New data
         * @param {boolean} animate Animate transition
         */
        setData(data, animate = true) {
            this.data = {
                problems: data.problems || [],
                solutions: data.solutions || [],
                offers: data.offers || [],
                primaryProblemId: data.primaryProblemId || null
            };

            if (animate && this.config.animationEnabled) {
                this.animateRender();
            } else {
                this.render();
            }
        }

        /**
         * Animate render
         */
        animateRender() {
            if (this.animationState.animating) {
                cancelAnimationFrame(this.animationState.requestId);
            }

            this.animationState.animating = true;
            this.animationState.progress = 0;

            const startTime = performance.now();
            const duration = this.config.animationDuration;

            const animate = (currentTime) => {
                const elapsed = currentTime - startTime;
                this.animationState.progress = Math.min(elapsed / duration, 1);

                // Use easeOutCubic
                const eased = 1 - Math.pow(1 - this.animationState.progress, 3);
                
                this.render(eased);

                if (this.animationState.progress < 1) {
                    this.animationState.requestId = requestAnimationFrame(animate);
                } else {
                    this.animationState.animating = false;
                }
            };

            this.animationState.requestId = requestAnimationFrame(animate);
        }

        /**
         * Main render function
         *
         * @param {number} progress Animation progress (0-1)
         */
        render(progress = 1) {
            const ctx = this.ctx;
            const centerX = this.logicalWidth / 2;
            const centerY = this.logicalHeight / 2;

            // Clear canvas
            ctx.clearRect(0, 0, this.logicalWidth, this.logicalHeight);

            // Draw layers from outer to inner
            this.drawProblemRing(ctx, centerX, centerY, progress);
            this.drawSolutionRing(ctx, centerX, centerY, progress);
            this.drawOfferCenter(ctx, centerX, centerY, progress);
            this.drawConnections(ctx, centerX, centerY, progress);
            this.drawNodes(ctx, centerX, centerY, progress);
        }

        /**
         * Draw problem ring (outer, red)
         */
        drawProblemRing(ctx, centerX, centerY, progress) {
            const config = this.config;
            const outerRadius = config.outerRingRadius * progress;
            const innerRadius = (config.outerRingRadius - config.ringWidth) * progress;
            const problems = this.data.problems;
            const segmentCount = Math.max(problems.length, 5);

            // Draw ring background
            ctx.beginPath();
            ctx.arc(centerX, centerY, outerRadius, 0, Math.PI * 2);
            ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2, true);
            ctx.fillStyle = config.problemColor;
            ctx.fill();

            // Draw segment dividers
            if (problems.length > 0) {
                const segmentAngle = (Math.PI * 2) / segmentCount;
                
                ctx.strokeStyle = config.lineColor;
                ctx.lineWidth = 2;
                
                for (let i = 0; i < segmentCount; i++) {
                    const angle = segmentAngle * i - Math.PI / 2;
                    const x1 = centerX + Math.cos(angle) * innerRadius;
                    const y1 = centerY + Math.sin(angle) * innerRadius;
                    const x2 = centerX + Math.cos(angle) * outerRadius;
                    const y2 = centerY + Math.sin(angle) * outerRadius;
                    
                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                    ctx.stroke();
                }
            }
        }

        /**
         * Draw solution ring (middle, blue)
         */
        drawSolutionRing(ctx, centerX, centerY, progress) {
            const config = this.config;
            const outerRadius = config.middleRingRadius * progress;
            const innerRadius = (config.middleRingRadius - config.ringWidth) * progress;
            const solutions = this.data.solutions;
            const segmentCount = Math.max(solutions.length, this.data.problems.length, 5);

            // Draw ring background
            ctx.beginPath();
            ctx.arc(centerX, centerY, outerRadius, 0, Math.PI * 2);
            ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2, true);
            ctx.fillStyle = config.solutionColor;
            ctx.fill();

            // Draw segment dividers
            if (solutions.length > 0 || this.data.problems.length > 0) {
                const segmentAngle = (Math.PI * 2) / segmentCount;
                
                ctx.strokeStyle = config.lineColor;
                ctx.lineWidth = 2;
                
                for (let i = 0; i < segmentCount; i++) {
                    const angle = segmentAngle * i - Math.PI / 2;
                    const x1 = centerX + Math.cos(angle) * innerRadius;
                    const y1 = centerY + Math.sin(angle) * innerRadius;
                    const x2 = centerX + Math.cos(angle) * outerRadius;
                    const y2 = centerY + Math.sin(angle) * outerRadius;
                    
                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                    ctx.stroke();
                }
            }
        }

        /**
         * Draw offer center (green circle)
         */
        drawOfferCenter(ctx, centerX, centerY, progress) {
            const config = this.config;
            const radius = config.centerCircleRadius * progress;
            const offerCount = this.data.offers.length;

            // Draw center circle
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
            ctx.fillStyle = config.offerColor;
            ctx.fill();

            // Draw offer count in center
            if (progress > 0.5) {
                const textOpacity = (progress - 0.5) * 2;
                ctx.globalAlpha = textOpacity;
                
                // Draw count
                ctx.font = 'bold 36px -apple-system, BlinkMacSystemFont, sans-serif';
                ctx.fillStyle = config.textColorLight;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(offerCount.toString(), centerX, centerY - 8);

                // Draw label
                ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
                ctx.fillText('OFFERS', centerX, centerY + 20);

                ctx.globalAlpha = 1;
            }
        }

        /**
         * Draw connections between rings
         */
        drawConnections(ctx, centerX, centerY, progress) {
            const config = this.config;
            const problems = this.data.problems;
            const solutions = this.data.solutions;

            if (problems.length === 0 || solutions.length === 0) return;

            const segmentCount = Math.max(problems.length, 5);
            const segmentAngle = (Math.PI * 2) / segmentCount;

            // Draw connection lines from problems to solutions to center
            solutions.forEach(solution => {
                const problem = problems.find(p => p.id === solution.problem_id);
                if (!problem) return;

                const position = problem.position;
                const angle = segmentAngle * position + segmentAngle / 2 - Math.PI / 2;

                // Problem node position (middle of outer ring)
                const problemRadius = config.outerRingRadius - config.ringWidth / 2;
                const problemX = centerX + Math.cos(angle) * problemRadius * progress;
                const problemY = centerY + Math.sin(angle) * problemRadius * progress;

                // Solution node position (middle of middle ring)
                const solutionRadius = config.middleRingRadius - config.ringWidth / 2;
                const solutionX = centerX + Math.cos(angle) * solutionRadius * progress;
                const solutionY = centerY + Math.sin(angle) * solutionRadius * progress;

                // Draw line from problem to solution
                ctx.beginPath();
                ctx.moveTo(problemX, problemY);
                ctx.lineTo(solutionX, solutionY);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
                ctx.lineWidth = 2;
                ctx.stroke();

                // Draw line from solution to center
                ctx.beginPath();
                ctx.moveTo(solutionX, solutionY);
                ctx.lineTo(centerX, centerY);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
                ctx.lineWidth = 1.5;
                ctx.stroke();
            });
        }

        /**
         * Draw nodes on rings
         */
        drawNodes(ctx, centerX, centerY, progress) {
            const config = this.config;
            const problems = this.data.problems;
            const solutions = this.data.solutions;
            const segmentCount = Math.max(problems.length, 5);
            const segmentAngle = (Math.PI * 2) / segmentCount;

            // Draw problem nodes
            problems.forEach((problem, index) => {
                const position = problem.position !== undefined ? problem.position : index;
                const angle = segmentAngle * position + segmentAngle / 2 - Math.PI / 2;
                const radius = config.outerRingRadius - config.ringWidth / 2;
                
                const x = centerX + Math.cos(angle) * radius * progress;
                const y = centerY + Math.sin(angle) * radius * progress;

                // Node circle
                ctx.beginPath();
                ctx.arc(x, y, config.nodeRadius * progress, 0, Math.PI * 2);
                ctx.fillStyle = config.nodeColor;
                ctx.fill();

                // Primary indicator
                if (problem.is_primary) {
                    ctx.beginPath();
                    ctx.arc(x, y, (config.nodeRadius + 4) * progress, 0, Math.PI * 2);
                    ctx.strokeStyle = '#ffd700';
                    ctx.lineWidth = 3;
                    ctx.stroke();
                }

                // Node number
                if (progress > 0.7) {
                    ctx.font = `bold ${14 * progress}px -apple-system, BlinkMacSystemFont, sans-serif`;
                    ctx.fillStyle = config.problemColor;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText((position + 1).toString(), x, y);
                }
            });

            // Draw solution nodes
            solutions.forEach(solution => {
                const problem = problems.find(p => p.id === solution.problem_id);
                if (!problem) return;

                const position = problem.position;
                const angle = segmentAngle * position + segmentAngle / 2 - Math.PI / 2;
                const radius = config.middleRingRadius - config.ringWidth / 2;
                
                const x = centerX + Math.cos(angle) * radius * progress;
                const y = centerY + Math.sin(angle) * radius * progress;

                // Node circle
                ctx.beginPath();
                ctx.arc(x, y, config.nodeRadiusSmall * progress, 0, Math.PI * 2);
                ctx.fillStyle = config.nodeColor;
                ctx.fill();

                // Checkmark for solutions
                if (progress > 0.7) {
                    ctx.font = `${12 * progress}px -apple-system, BlinkMacSystemFont, sans-serif`;
                    ctx.fillStyle = config.solutionColor;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText('✓', x, y);
                }
            });

            // Draw empty placeholders for missing solutions
            const solutionProblemIds = solutions.map(s => s.problem_id);
            problems.forEach((problem, index) => {
                if (solutionProblemIds.includes(problem.id)) return;

                const position = problem.position !== undefined ? problem.position : index;
                const angle = segmentAngle * position + segmentAngle / 2 - Math.PI / 2;
                const radius = config.middleRingRadius - config.ringWidth / 2;
                
                const x = centerX + Math.cos(angle) * radius * progress;
                const y = centerY + Math.sin(angle) * radius * progress;

                // Empty node circle (dashed)
                ctx.beginPath();
                ctx.arc(x, y, config.nodeRadiusSmall * progress, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
                ctx.lineWidth = 2;
                ctx.setLineDash([4, 4]);
                ctx.stroke();
                ctx.setLineDash([]);
            });
        }

        /**
         * Get canvas data URL
         *
         * @returns {string} Data URL
         */
        toDataURL() {
            return this.canvas.toDataURL('image/png');
        }

        /**
         * Download canvas as image
         *
         * @param {string} filename Filename
         */
        downloadAsImage(filename = 'journey-circle.png') {
            const link = document.createElement('a');
            link.download = filename;
            link.href = this.toDataURL();
            link.click();
        }

        /**
         * Resize canvas
         *
         * @param {number} width New width
         * @param {number} height New height
         */
        resize(width, height) {
            this.config.width = width;
            this.config.height = height;
            this.init();
        }

        /**
         * Destroy renderer
         */
        destroy() {
            if (this.animationState.requestId) {
                cancelAnimationFrame(this.animationState.requestId);
            }
            this.ctx = null;
            this.canvas = null;
        }
    }

    /**
     * Helper function to update existing renderer with new solution/offer data
     *
     * @param {Object} renderer Existing renderer instance
     * @param {Object} data Solution and offer data
     */
    function updateRendererWithSolutionsAndOffers(renderer, data) {
        if (!renderer || !renderer.setData) {
            console.error('Invalid renderer instance');
            return;
        }

        renderer.setData({
            ...renderer.data,
            solutions: data.solutions || [],
            offers: data.offers || []
        });
    }

    // Export to global scope
    window.JourneyCircleRendererExtended = JourneyCircleRendererExtended;
    window.updateRendererWithSolutionsAndOffers = updateRendererWithSolutionsAndOffers;

    // If base renderer exists, extend it
    if (BaseRenderer) {
        // Add methods to prototype
        Object.assign(BaseRenderer.prototype, {
            drawSolutionRing: JourneyCircleRendererExtended.prototype.drawSolutionRing,
            drawOfferCenter: JourneyCircleRendererExtended.prototype.drawOfferCenter,
            drawConnections: JourneyCircleRendererExtended.prototype.drawConnections
        });
    }

})(window, document);
