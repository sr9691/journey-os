/**
 * Journey Circle Renderer Updates - Iteration 5
 * 
 * This file contains the additions to journey-circle-renderer.js
 * for displaying the problem ring on the canvas visualization.
 * 
 * Integration Instructions:
 * 1. Add these methods to the JourneyCircleRenderer class
 * 2. Call updateProblems() when problems are selected
 * 
 * @package DirectReach
 * @subpackage JourneyCircle
 * @since 2.0.0
 */

// ============================================================================
// ADD TO CONSTRUCTOR
// ============================================================================

/*
 * Add to constructor after existing properties:
 * 
 * // Problem data
 * this.problems = [];
 * 
 * // Canvas dimensions (from mockup specs)
 * this.dimensions = {
 *     canvas: { width: 700, height: 700 },
 *     center: { x: 350, y: 350 },
 *     outerRing: { radius: 280, width: 40 },  // Problems - red
 *     middleRing: { radius: 200, width: 40 }, // Solutions - blue
 *     centerCircle: { radius: 80 }             // Offers - green
 * };
 * 
 * // Colors from mockup
 * this.colors = {
 *     problems: '#ff6b6b',
 *     problemsHover: '#ff5252',
 *     solutions: '#42a5f5',
 *     solutionsHover: '#2196f3',
 *     offers: '#66bb6a',
 *     offersHover: '#4caf50',
 *     segments: '#ffffff',
 *     text: '#ffffff',
 *     textDark: '#1e293b',
 *     background: '#f8fafc',
 *     emptyRing: '#e2e8f0'
 * };
 */


// ============================================================================
// PROBLEM RING RENDERING METHODS
// ============================================================================

/**
 * Update problems data
 * @param {Array} problems - Array of selected problems
 */
updateProblems(problems) {
    this.problems = problems || [];
    this.draw();
}

/**
 * Draw the problem ring (outer ring)
 */
drawProblemRing() {
    const ctx = this.ctx;
    const center = this.dimensions.center;
    const ring = this.dimensions.outerRing;
    
    if (this.problems.length === 0) {
        // Draw empty ring
        this.drawEmptyRing(ring.radius, ring.width, 'Problems', 5);
        return;
    }

    const numSegments = 5;
    const segmentAngle = (2 * Math.PI) / numSegments;
    const startAngle = -Math.PI / 2; // Start from top

    // Draw each segment
    for (let i = 0; i < numSegments; i++) {
        const problem = this.problems[i];
        const angle1 = startAngle + (i * segmentAngle);
        const angle2 = startAngle + ((i + 1) * segmentAngle);

        // Draw segment
        ctx.beginPath();
        ctx.arc(center.x, center.y, ring.radius, angle1, angle2);
        ctx.arc(center.x, center.y, ring.radius - ring.width, angle2, angle1, true);
        ctx.closePath();

        // Fill with problem color or empty color
        if (problem) {
            ctx.fillStyle = this.colors.problems;
        } else {
            ctx.fillStyle = this.colors.emptyRing;
        }
        ctx.fill();

        // Draw segment border
        ctx.strokeStyle = this.colors.segments;
        ctx.lineWidth = 3;
        ctx.stroke();

        // Draw node with number
        if (problem) {
            this.drawProblemNode(i, angle1 + segmentAngle / 2, ring.radius - ring.width / 2, problem);
        }
    }
}

/**
 * Draw a problem node (circle with number)
 */
drawProblemNode(index, angle, radius, problem) {
    const ctx = this.ctx;
    const center = this.dimensions.center;

    // Calculate node position
    const nodeX = center.x + Math.cos(angle) * radius;
    const nodeY = center.y + Math.sin(angle) * radius;
    const nodeRadius = 18;

    // Draw node circle
    ctx.beginPath();
    ctx.arc(nodeX, nodeY, nodeRadius, 0, 2 * Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = this.colors.problems;
    ctx.lineWidth = 3;
    ctx.stroke();

    // Draw number
    ctx.fillStyle = this.colors.problems;
    ctx.font = 'bold 14px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText((index + 1).toString(), nodeX, nodeY);

    // Mark primary problem with a star
    if (problem.isPrimary) {
        this.drawPrimaryStar(nodeX, nodeY - nodeRadius - 8);
    }
}

/**
 * Draw a star indicator for primary problem
 */
drawPrimaryStar(x, y) {
    const ctx = this.ctx;
    const size = 10;

    ctx.beginPath();
    ctx.fillStyle = '#f59e0b';

    // 5-pointed star
    for (let i = 0; i < 5; i++) {
        const angle = (i * 4 * Math.PI / 5) - Math.PI / 2;
        const px = x + Math.cos(angle) * size;
        const py = y + Math.sin(angle) * size;
        if (i === 0) {
            ctx.moveTo(px, py);
        } else {
            ctx.lineTo(px, py);
        }
    }

    ctx.closePath();
    ctx.fill();
}

/**
 * Draw an empty ring placeholder
 */
drawEmptyRing(radius, width, label, segments) {
    const ctx = this.ctx;
    const center = this.dimensions.center;
    const segmentAngle = (2 * Math.PI) / segments;
    const startAngle = -Math.PI / 2;

    // Draw each segment
    for (let i = 0; i < segments; i++) {
        const angle1 = startAngle + (i * segmentAngle);
        const angle2 = startAngle + ((i + 1) * segmentAngle);

        ctx.beginPath();
        ctx.arc(center.x, center.y, radius, angle1, angle2);
        ctx.arc(center.x, center.y, radius - width, angle2, angle1, true);
        ctx.closePath();

        // Fill with empty color
        ctx.fillStyle = this.colors.emptyRing;
        ctx.fill();

        // Draw segment border
        ctx.strokeStyle = this.colors.segments;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw placeholder number
        const midAngle = angle1 + segmentAngle / 2;
        const nodeX = center.x + Math.cos(midAngle) * (radius - width / 2);
        const nodeY = center.y + Math.sin(midAngle) * (radius - width / 2);

        ctx.fillStyle = '#94a3b8';
        ctx.font = 'bold 14px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText((i + 1).toString(), nodeX, nodeY);
    }

    // Draw label in center of ring
    ctx.fillStyle = '#94a3b8';
    ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // Position label between rings
    ctx.fillText(label, center.x, center.y - radius + width / 2 + 50);
}

/**
 * Draw the solution ring (middle ring) - placeholder for Iteration 6
 */
drawSolutionRing() {
    const ring = this.dimensions.middleRing;
    this.drawEmptyRing(ring.radius, ring.width, 'Solutions', 5);
}

/**
 * Draw the offer center circle - placeholder for Iteration 6
 */
drawOfferCenter() {
    const ctx = this.ctx;
    const center = this.dimensions.center;
    const circleRadius = this.dimensions.centerCircle.radius;

    // Draw center circle
    ctx.beginPath();
    ctx.arc(center.x, center.y, circleRadius, 0, 2 * Math.PI);
    ctx.fillStyle = this.colors.emptyRing;
    ctx.fill();

    // Draw border
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw placeholder text
    ctx.fillStyle = '#94a3b8';
    ctx.font = '14px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('Offers', center.x, center.y - 10);
    ctx.fillText('(0)', center.x, center.y + 10);
}

/**
 * Draw connecting lines from problems to center
 */
drawConnectionLines() {
    if (this.problems.length === 0) return;

    const ctx = this.ctx;
    const center = this.dimensions.center;
    const outerRing = this.dimensions.outerRing;
    const middleRing = this.dimensions.middleRing;
    const centerCircle = this.dimensions.centerCircle;
    const numSegments = 5;
    const segmentAngle = (2 * Math.PI) / numSegments;
    const startAngle = -Math.PI / 2;

    for (let i = 0; i < this.problems.length && i < 5; i++) {
        const angle = startAngle + (i * segmentAngle) + segmentAngle / 2;

        // Calculate points
        const outerX = center.x + Math.cos(angle) * (outerRing.radius - outerRing.width);
        const outerY = center.y + Math.sin(angle) * (outerRing.radius - outerRing.width);
        const middleX = center.x + Math.cos(angle) * middleRing.radius;
        const middleY = center.y + Math.sin(angle) * middleRing.radius;
        const innerX = center.x + Math.cos(angle) * (middleRing.radius - middleRing.width);
        const innerY = center.y + Math.sin(angle) * (middleRing.radius - middleRing.width);
        const centerEdgeX = center.x + Math.cos(angle) * centerCircle.radius;
        const centerEdgeY = center.y + Math.sin(angle) * centerCircle.radius;

        // Draw line from outer to middle
        ctx.beginPath();
        ctx.moveTo(outerX, outerY);
        ctx.lineTo(middleX, middleY);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Draw line from middle to center
        ctx.beginPath();
        ctx.moveTo(innerX, innerY);
        ctx.lineTo(centerEdgeX, centerEdgeY);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
    }
}

/**
 * Main draw method - updated
 */
draw() {
    const ctx = this.ctx;
    const canvas = this.canvas;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw background
    ctx.fillStyle = this.colors.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw rings from outside in
    this.drawProblemRing();    // Outer ring - Problems (red)
    this.drawSolutionRing();   // Middle ring - Solutions (blue)
    this.drawOfferCenter();    // Center circle - Offers (green)

    // Draw connection lines
    this.drawConnectionLines();

    // Draw labels
    this.drawLabels();
}

/**
 * Draw ring labels
 */
drawLabels() {
    const ctx = this.ctx;
    const center = this.dimensions.center;

    // Only draw labels if rings are populated
    if (this.problems.length > 0) {
        // Problem count label
        ctx.fillStyle = this.colors.textDark;
        ctx.font = 'bold 12px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // Position at top of canvas
        ctx.fillText(`${this.problems.length}/5 Problems`, center.x, 30);
    }
}

/**
 * Handle canvas resize for responsiveness
 */
handleResize() {
    const container = this.canvas.parentElement;
    if (!container) return;

    const containerWidth = container.clientWidth;
    const maxSize = Math.min(containerWidth, 700);
    const scale = maxSize / 700;

    // Update canvas size
    this.canvas.style.width = maxSize + 'px';
    this.canvas.style.height = maxSize + 'px';

    // Redraw
    this.draw();
}

/**
 * Initialize resize handler
 */
initResizeHandler() {
    // Debounced resize handler
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => this.handleResize(), 150);
    });

    // Initial resize
    this.handleResize();
}


// ============================================================================
// COMPLETE RENDERER CLASS (for reference)
// ============================================================================

/**
 * Complete JourneyCircleRenderer class with Iteration 5 updates
 */
class JourneyCircleRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error(`Canvas element not found: ${canvasId}`);
            return;
        }

        this.ctx = this.canvas.getContext('2d');

        // Problem data
        this.problems = [];
        this.solutions = [];
        this.offers = [];

        // Canvas dimensions (from mockup specs)
        this.dimensions = {
            canvas: { width: 700, height: 700 },
            center: { x: 350, y: 350 },
            outerRing: { radius: 280, width: 40 },
            middleRing: { radius: 200, width: 40 },
            centerCircle: { radius: 80 }
        };

        // Colors from mockup
        this.colors = {
            problems: '#ff6b6b',
            problemsHover: '#ff5252',
            solutions: '#42a5f5',
            solutionsHover: '#2196f3',
            offers: '#66bb6a',
            offersHover: '#4caf50',
            segments: '#ffffff',
            text: '#ffffff',
            textDark: '#1e293b',
            background: '#f8fafc',
            emptyRing: '#e2e8f0'
        };

        // Set canvas dimensions
        this.canvas.width = this.dimensions.canvas.width;
        this.canvas.height = this.dimensions.canvas.height;

        // Initialize resize handler
        this.initResizeHandler();

        // Initial draw
        this.draw();
    }

    // Include all methods from above
    updateProblems(problems) {
        this.problems = problems || [];
        this.draw();
    }

    drawProblemRing() {
        const ctx = this.ctx;
        const center = this.dimensions.center;
        const ring = this.dimensions.outerRing;

        if (this.problems.length === 0) {
            this.drawEmptyRing(ring.radius, ring.width, 'Problems', 5);
            return;
        }

        const numSegments = 5;
        const segmentAngle = (2 * Math.PI) / numSegments;
        const startAngle = -Math.PI / 2;

        for (let i = 0; i < numSegments; i++) {
            const problem = this.problems[i];
            const angle1 = startAngle + (i * segmentAngle);
            const angle2 = startAngle + ((i + 1) * segmentAngle);

            ctx.beginPath();
            ctx.arc(center.x, center.y, ring.radius, angle1, angle2);
            ctx.arc(center.x, center.y, ring.radius - ring.width, angle2, angle1, true);
            ctx.closePath();

            if (problem) {
                ctx.fillStyle = this.colors.problems;
            } else {
                ctx.fillStyle = this.colors.emptyRing;
            }
            ctx.fill();

            ctx.strokeStyle = this.colors.segments;
            ctx.lineWidth = 3;
            ctx.stroke();

            if (problem) {
                this.drawProblemNode(i, angle1 + segmentAngle / 2, ring.radius - ring.width / 2, problem);
            }
        }
    }

    drawProblemNode(index, angle, radius, problem) {
        const ctx = this.ctx;
        const center = this.dimensions.center;

        const nodeX = center.x + Math.cos(angle) * radius;
        const nodeY = center.y + Math.sin(angle) * radius;
        const nodeRadius = 18;

        ctx.beginPath();
        ctx.arc(nodeX, nodeY, nodeRadius, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        ctx.strokeStyle = this.colors.problems;
        ctx.lineWidth = 3;
        ctx.stroke();

        ctx.fillStyle = this.colors.problems;
        ctx.font = 'bold 14px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText((index + 1).toString(), nodeX, nodeY);

        if (problem.isPrimary) {
            this.drawPrimaryStar(nodeX, nodeY - nodeRadius - 8);
        }
    }

    drawPrimaryStar(x, y) {
        const ctx = this.ctx;
        const size = 10;

        ctx.beginPath();
        ctx.fillStyle = '#f59e0b';

        for (let i = 0; i < 5; i++) {
            const angle = (i * 4 * Math.PI / 5) - Math.PI / 2;
            const px = x + Math.cos(angle) * size;
            const py = y + Math.sin(angle) * size;
            if (i === 0) {
                ctx.moveTo(px, py);
            } else {
                ctx.lineTo(px, py);
            }
        }

        ctx.closePath();
        ctx.fill();
    }

    drawEmptyRing(radius, width, label, segments) {
        const ctx = this.ctx;
        const center = this.dimensions.center;
        const segmentAngle = (2 * Math.PI) / segments;
        const startAngle = -Math.PI / 2;

        for (let i = 0; i < segments; i++) {
            const angle1 = startAngle + (i * segmentAngle);
            const angle2 = startAngle + ((i + 1) * segmentAngle);

            ctx.beginPath();
            ctx.arc(center.x, center.y, radius, angle1, angle2);
            ctx.arc(center.x, center.y, radius - width, angle2, angle1, true);
            ctx.closePath();

            ctx.fillStyle = this.colors.emptyRing;
            ctx.fill();

            ctx.strokeStyle = this.colors.segments;
            ctx.lineWidth = 2;
            ctx.stroke();

            const midAngle = angle1 + segmentAngle / 2;
            const nodeX = center.x + Math.cos(midAngle) * (radius - width / 2);
            const nodeY = center.y + Math.sin(midAngle) * (radius - width / 2);

            ctx.fillStyle = '#94a3b8';
            ctx.font = 'bold 14px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText((i + 1).toString(), nodeX, nodeY);
        }
    }

    drawSolutionRing() {
        const ring = this.dimensions.middleRing;
        this.drawEmptyRing(ring.radius, ring.width, 'Solutions', 5);
    }

    drawOfferCenter() {
        const ctx = this.ctx;
        const center = this.dimensions.center;
        const circleRadius = this.dimensions.centerCircle.radius;

        ctx.beginPath();
        ctx.arc(center.x, center.y, circleRadius, 0, 2 * Math.PI);
        ctx.fillStyle = this.colors.emptyRing;
        ctx.fill();

        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = '#94a3b8';
        ctx.font = '14px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Offers', center.x, center.y - 10);
        ctx.fillText('(0)', center.x, center.y + 10);
    }

    drawConnectionLines() {
        if (this.problems.length === 0) return;

        const ctx = this.ctx;
        const center = this.dimensions.center;
        const outerRing = this.dimensions.outerRing;
        const middleRing = this.dimensions.middleRing;
        const centerCircle = this.dimensions.centerCircle;
        const numSegments = 5;
        const segmentAngle = (2 * Math.PI) / numSegments;
        const startAngle = -Math.PI / 2;

        for (let i = 0; i < this.problems.length && i < 5; i++) {
            const angle = startAngle + (i * segmentAngle) + segmentAngle / 2;

            const outerX = center.x + Math.cos(angle) * (outerRing.radius - outerRing.width);
            const outerY = center.y + Math.sin(angle) * (outerRing.radius - outerRing.width);
            const middleX = center.x + Math.cos(angle) * middleRing.radius;
            const middleY = center.y + Math.sin(angle) * middleRing.radius;
            const innerX = center.x + Math.cos(angle) * (middleRing.radius - middleRing.width);
            const innerY = center.y + Math.sin(angle) * (middleRing.radius - middleRing.width);
            const centerEdgeX = center.x + Math.cos(angle) * centerCircle.radius;
            const centerEdgeY = center.y + Math.sin(angle) * centerCircle.radius;

            ctx.beginPath();
            ctx.moveTo(outerX, outerY);
            ctx.lineTo(middleX, middleY);
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 4]);
            ctx.stroke();
            ctx.setLineDash([]);

            ctx.beginPath();
            ctx.moveTo(innerX, innerY);
            ctx.lineTo(centerEdgeX, centerEdgeY);
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 4]);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }

    draw() {
        const ctx = this.ctx;
        const canvas = this.canvas;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        this.drawProblemRing();
        this.drawSolutionRing();
        this.drawOfferCenter();
        this.drawConnectionLines();
        this.drawLabels();
    }

    drawLabels() {
        const ctx = this.ctx;
        const center = this.dimensions.center;

        if (this.problems.length > 0) {
            ctx.fillStyle = this.colors.textDark;
            ctx.font = 'bold 12px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(`${this.problems.length}/5 Problems`, center.x, 30);
        }
    }

    handleResize() {
        const container = this.canvas.parentElement;
        if (!container) return;

        const containerWidth = container.clientWidth;
        const maxSize = Math.min(containerWidth, 700);

        this.canvas.style.width = maxSize + 'px';
        this.canvas.style.height = maxSize + 'px';

        this.draw();
    }

    initResizeHandler() {
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => this.handleResize(), 150);
        });

        this.handleResize();
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JourneyCircleRenderer;
}
