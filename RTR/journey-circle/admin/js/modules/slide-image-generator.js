/**
 * Slide Image Generator Module
 *
 * Enhances presentation downloads by generating AI images for visual-heavy slides
 * using Nano Banana Pro (Gemini Image API). Works alongside the existing
 * PptxGenJS pipeline in content-renderer.js.
 *
 * Flow:
 *   1. Gemini generates slide content JSON (existing)
 *   2. This module identifies slides with visual_element data
 *   3. Calls REST endpoint to generate images for those slides
 *   4. PptxGenJS assembles the deck:
 *      - Text-only slides → native PptxGenJS text/shapes (editable)
 *      - Visual slides → AI-generated image placed as slide image
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.1.0
 */
(function($) {
    'use strict';

    // =========================================================================
    // CONFIGURATION
    // =========================================================================

    var CONFIG = {
        // REST endpoint for slide image generation
        // Try multiple localized variable names, then fall back to wpApiSettings
        endpoint: (function() {
            // Campaign Builder style
            if (window.drJourneyCircle && window.drJourneyCircle.restUrl) {
                return window.drJourneyCircle.restUrl.replace(/journey-circle\/v1\/?$/, 'directreach/v2/') + 'ai/generate-slide-image';
            }
            // Journey Circle admin localized data
            if (window.journeyCircleData && window.journeyCircleData.restUrl) {
                var base = window.journeyCircleData.restUrl.replace(/journey-circle\/v1\/?$/, '');
                return base + 'directreach/v2/ai/generate-slide-image';
            }
            // WordPress REST API settings (most reliable)
            if (window.wpApiSettings && window.wpApiSettings.root) {
                return window.wpApiSettings.root + 'directreach/v2/ai/generate-slide-image';
            }
            // Absolute fallback using wp-json discovery
            return '/wp-json/directreach/v2/ai/generate-slide-image';
        })(),

        // Nonce for authentication
        nonce: (function() {
            if (window.drJourneyCircle && window.drJourneyCircle.nonce) return window.drJourneyCircle.nonce;
            if (window.journeyCircleData && window.journeyCircleData.restNonce) return window.journeyCircleData.restNonce;
            if (window.wpApiSettings && window.wpApiSettings.nonce) return window.wpApiSettings.nonce;
            return '';
        })(),

        // Quality: 'standard' (gemini-2.5-flash-image) or 'pro' (gemini-3-pro-image-preview)
        quality: 'standard',

        // Max concurrent image generation requests
        maxConcurrent: 2,

        // Request timeout (ms)
        timeout: 90000,

        // Retry settings
        maxRetries: 1,
        retryDelay: 2000
    };

    // =========================================================================
    // SLIDE IMAGE GENERATOR
    // =========================================================================

    var SlideImageGenerator = {

        /**
         * Check if a slide needs AI-generated imagery.
         *
         * @param {Object} slide - Slide data from Gemini JSON
         * @returns {boolean}
         */
        slideNeedsImage: function(slide) {
            return slide.visual_element
                && slide.visual_element.type
                && slide.visual_element.data
                && typeof slide.visual_element.data === 'object';
        },

        /**
         * Identify all visual slides in a deck that need images.
         *
         * @param {Array} slides - Array of slide objects
         * @returns {Array} Indices of slides needing images
         */
        getVisualSlideIndices: function(slides) {
            var indices = [];
            for (var i = 0; i < slides.length; i++) {
                if (this.slideNeedsImage(slides[i])) {
                    indices.push(i);
                }
            }
            return indices;
        },

        /**
         * Generate an image for a single slide via the REST API.
         *
         * @param {Object} slide     - Slide data object
         * @param {string} quality   - 'standard' or 'pro'
         * @returns {Promise<Object>} Resolves with { image_base64, mime_type } or rejects
         */
        generateSlideImage: function(slide, quality) {
            var self = this;
            quality = quality || CONFIG.quality;

            return new Promise(function(resolve, reject) {
                var payload = {
                    slide_title:    slide.slide_title || '',
                    section:        slide.section || '',
                    key_points:     slide.key_points || [],
                    data_points:    slide.data_points || [],
                    visual_element: slide.visual_element,
                    quality:        quality
                };

                self._apiCall(payload, 0, resolve, reject);
            });
        },

        /**
         * Internal API call with retry logic.
         */
        _apiCall: function(payload, attempt, resolve, reject) {
            var self = this;

            $.ajax({
                url: CONFIG.endpoint,
                method: 'POST',
                headers: CONFIG.nonce ? { 'X-WP-Nonce': CONFIG.nonce } : {},
                contentType: 'application/json',
                data: JSON.stringify(payload),
                timeout: CONFIG.timeout,
                success: function(response) {
                    if (response.success && response.image_base64) {
                        resolve({
                            image_base64: response.image_base64,
                            mime_type:    response.mime_type || 'image/png',
                            model_used:   response.model_used || 'unknown'
                        });
                    } else {
                        var msg = (response && response.message) || 'No image returned';
                        if (attempt < CONFIG.maxRetries) {
                            setTimeout(function() {
                                self._apiCall(payload, attempt + 1, resolve, reject);
                            }, CONFIG.retryDelay);
                        } else {
                            reject(new Error(msg));
                        }
                    }
                },
                error: function(xhr, status, error) {
                    var msg = 'Image generation failed';
                    if (status === 'timeout') {
                        msg = 'Image generation timed out';
                    } else if (xhr.responseJSON && xhr.responseJSON.message) {
                        msg = xhr.responseJSON.message;
                    }
                    if (attempt < CONFIG.maxRetries) {
                        setTimeout(function() {
                            self._apiCall(payload, attempt + 1, resolve, reject);
                        }, CONFIG.retryDelay);
                    } else {
                        reject(new Error(msg));
                    }
                }
            });
        },

        /**
         * Generate images for all visual slides with controlled concurrency.
         *
         * @param {Array}  slides   - Full slide array
         * @param {string} quality  - 'standard' or 'pro'
         * @param {Function} onProgress - Callback(completed, total, slideIndex)
         * @returns {Promise<Object>} Map of slideIndex => { image_base64, mime_type } | { error }
         */
        generateDeckImages: function(slides, quality, onProgress) {
            var self = this;
            var indices = this.getVisualSlideIndices(slides);
            var total = indices.length;
            var completed = 0;
            var imageMap = {};

            if (total === 0) {
                return Promise.resolve(imageMap);
            }

            // Process in batches to limit concurrency.
            return new Promise(function(resolveAll) {
                var queue = indices.slice();

                function processNext() {
                    if (queue.length === 0) {
                        if (completed >= total) resolveAll(imageMap);
                        return;
                    }

                    // Take up to maxConcurrent items.
                    var batch = queue.splice(0, CONFIG.maxConcurrent);
                    var batchPromises = batch.map(function(idx) {
                        return self.generateSlideImage(slides[idx], quality)
                            .then(function(result) {
                                imageMap[idx] = result;
                            })
                            .catch(function(err) {
                                console.warn('SlideImageGenerator: Failed for slide ' + (idx + 1) + ':', err.message);
                                imageMap[idx] = { error: err.message };
                            })
                            .finally(function() {
                                completed++;
                                if (typeof onProgress === 'function') {
                                    onProgress(completed, total, batch[0]);
                                }
                            });
                    });

                    Promise.all(batchPromises).then(function() {
                        processNext();
                    });
                }

                processNext();
            });
        },

        /**
         * Set quality level.
         * @param {string} q - 'standard' or 'pro'
         */
        setQuality: function(q) {
            CONFIG.quality = (q === 'pro') ? 'pro' : 'standard';
        }
    };


    // =========================================================================
    // ENHANCED PPTX DOWNLOAD — Monkey-patch onto JCContentRenderer
    // =========================================================================

    /**
     * Wait for the base ContentRenderer to be available, then augment it
     * with AI-powered image slide support.
     */
    function patchContentRenderer() {
        var CR = window.JCContentRenderer;
        if (!CR) {
            // Retry in 200ms if base module hasn't loaded yet.
            setTimeout(patchContentRenderer, 200);
            return;
        }

        // Store original download method.
        var _originalDownloadPptx = CR._downloadPptx;

        /**
         * Enhanced PPTX download with Nano Banana slide images.
         *
         * When the user clicks "Download PPTX", this:
         *   1) Checks if AI images are enabled
         *   2) If yes: shows progress UI, generates images, then builds PPTX
         *   3) If no: falls back to original PptxGenJS-only download
         */
        CR._downloadPptxWithImages = function(content, filename, meta, options) {
            var self = this;
            options = options || {};
            var useAiImages = options.useAiImages !== false; // default true
            var quality = options.quality || CONFIG.quality;

            var slides = this._parseSlides(content);
            if (!slides) {
                // Can't parse slides — fall back to HTML download.
                this._downloadHtml(content, 'presentation', filename, meta);
                return;
            }

            var visualIndices = SlideImageGenerator.getVisualSlideIndices(slides);

            if (!useAiImages || visualIndices.length === 0) {
                // No visual slides or AI disabled — use original method.
                _originalDownloadPptx.call(self, content, filename, meta);
                return;
            }

            // Show progress indicator.
            var progressEl = this._showImageProgress(visualIndices.length);

            SlideImageGenerator.generateDeckImages(slides, quality, function(done, total) {
                self._updateImageProgress(progressEl, done, total);
            }).then(function(imageMap) {
                self._hideImageProgress(progressEl);
                self._buildPptxWithImages(slides, imageMap, filename, meta);
            }).catch(function(err) {
                self._hideImageProgress(progressEl);
                console.error('Image generation failed, falling back to shapes:', err);
                _originalDownloadPptx.call(self, content, filename, meta);
            });
        };

        /**
         * Build the PPTX with AI images for visual slides and native
         * PptxGenJS elements for text-only slides.
         */
        CR._buildPptxWithImages = function(slides, imageMap, filename, meta) {
            if (!this.isPptxReady()) {
                alert('PowerPoint library is still loading. Please try again.');
                return;
            }

            var THEME = window.JC_SLIDE_THEME || {
                bg: '0F2B46', accentColor: '42A5F5', subtextColor: 'B0BEC5',
                sectionColors: {}
            };
            // Normalize: remove # if present.
            var bgColor = (THEME.bg || '0F2B46').replace('#', '');
            var accentColor = (THEME.accentColor || '42A5F5').replace('#', '');

            var pptx = new PptxGenJS();
            pptx.author = 'DirectReach Campaign Builder';
            pptx.subject = meta && meta.problemTitle ? meta.problemTitle : 'Journey Circle Presentation';
            pptx.title = slides[0] ? (slides[0].slide_title || 'Presentation') : 'Presentation';
            pptx.layout = 'LAYOUT_WIDE'; // 13.33" x 7.5" = 16:9

            // Define master slide.
            pptx.defineSlideMaster({
                title: 'JC_MASTER',
                background: { color: bgColor },
                objects: [
                    { rect: { x: 0, y: 0, w: '100%', h: 0.04, fill: { color: accentColor } } }
                ]
            });

            for (var s = 0; s < slides.length; s++) {
                var sd = slides[s];
                var hasImage = imageMap[s] && imageMap[s].image_base64 && !imageMap[s].error;
                var slide = pptx.addSlide({ masterName: 'JC_MASTER' });

                if (hasImage) {
                    // ─── AI IMAGE SLIDE ─────────────────────────────────
                    // Place the AI-generated image as a full-slide background.
                    var imgData = 'data:' + (imageMap[s].mime_type || 'image/png')
                        + ';base64,' + imageMap[s].image_base64;

                    slide.addImage({
                        data: imgData,
                        x: 0, y: 0,
                        w: '100%', h: '100%',
                        sizing: { type: 'contain', w: '100%', h: '100%' }
                    });

                    // Slide number overlay (semi-transparent).
                    slide.addText((sd.slide_number || (s + 1)) + ' / ' + slides.length, {
                        x: 8.5, y: 0.08, w: 1.3, h: 0.3,
                        fontSize: 8, color: 'FFFFFF', align: 'right',
                        transparency: 50
                    });

                } else {
                    // ─── NATIVE PPTXGENJS SLIDE ─────────────────────────
                    // Fall back to the original shape-based rendering.
                    this._buildNativeSlide(pptx, slide, sd, s, slides.length);
                }

                // Speaker notes (always editable text).
                if (sd.speaker_notes) {
                    slide.addNotes(sd.speaker_notes);
                }
            }

            pptx.writeFile({ fileName: (filename || 'presentation') + '.pptx' });
        };

        /**
         * Build a native PptxGenJS slide (no AI image).
         * Extracted from the original _downloadPptx for reuse.
         */
        CR._buildNativeSlide = function(pptx, slide, sd, slideIndex, totalSlides) {
            var THEME = {
                bg: '0F2B46', accentColor: '42A5F5', subtextColor: 'B0BEC5',
                chartColors: ['42A5F5', '66BB6A', 'EF5350', 'FF7043', 'AB47BC', 'FFA726', '26C6DA', 'EC407A'],
                sectionColors: {
                    'Title Slide':          { accent: '42A5F5' },
                    'Problem Definition':   { accent: 'EF5350' },
                    'Problem Amplification':{ accent: 'EF5350' },
                    'Solution Overview':    { accent: '66BB6A' },
                    'Solution Details':     { accent: '66BB6A' },
                    'Benefits Summary':     { accent: '42A5F5' },
                    'Credibility':          { accent: 'AB47BC' },
                    'Call to Action':       { accent: 'FF7043' }
                }
            };

            var section = sd.section || '';
            var sectionTheme = THEME.sectionColors[section] || { accent: THEME.accentColor };
            var accent = sectionTheme.accent;
            var isTitle = (slideIndex === 0 || section.toLowerCase().indexOf('title') !== -1);
            var hasVisual = sd.visual_element && sd.visual_element.type && sd.visual_element.data;

            // Slide number.
            slide.addText((sd.slide_number || (slideIndex + 1)) + ' / ' + totalSlides, {
                x: 8.5, y: 0.15, w: 1.3, h: 0.3,
                fontSize: 8, color: 'B0BEC5', align: 'right'
            });

            if (isTitle) {
                // Title slide layout.
                slide.addText(sd.slide_title || 'Untitled', {
                    x: 0.8, y: 1.5, w: 8.4, h: 1.5,
                    fontSize: 28, bold: true, color: 'FFFFFF', align: 'left', valign: 'middle'
                });
                if (sd.key_points && sd.key_points.length > 0) {
                    slide.addText(sd.key_points.join('\n'), {
                        x: 0.8, y: 3.0, w: 7.0, h: 1.5,
                        fontSize: 14, color: 'B0BEC5', lineSpacing: 22
                    });
                }
            } else if (hasVisual) {
                // Split layout: text left + visual right (PptxGenJS shapes).
                var textW = 4.8, vizX = 5.3, vizW = 4.5;

                if (section) {
                    slide.addText(section.toUpperCase(), {
                        x: 0.8, y: 0.4, w: textW, h: 0.3,
                        fontSize: 9, bold: true, color: accent, letterSpacing: 2
                    });
                }
                slide.addText(sd.slide_title || '', {
                    x: 0.8, y: 0.8, w: textW, h: 0.7,
                    fontSize: 20, bold: true, color: 'FFFFFF'
                });
                if (sd.key_points && sd.key_points.length > 0) {
                    var bullets = sd.key_points.map(function(kp) {
                        return {
                            text: kp,
                            options: {
                                fontSize: 12, color: 'B0BEC5',
                                bullet: { type: 'bullet', color: accent },
                                lineSpacing: 18, paraSpaceAfter: 4
                            }
                        };
                    });
                    slide.addText(bullets, { x: 0.8, y: 1.6, w: textW, h: 3.0, valign: 'top' });
                }
                // Use original visual renderer.
                if (typeof this._addPptxVisual === 'function') {
                    this._addPptxVisual(pptx, slide, sd.visual_element, vizX, 0.8, vizW, 4.0, sectionTheme);
                }
                if (sd.data_points && sd.data_points.length > 0) {
                    slide.addText(sd.data_points.map(function(dp) { return '• ' + dp; }).join('   '), {
                        x: 0.8, y: 4.8, w: 8.4, h: 0.4, fontSize: 9, color: '78909C', italic: true
                    });
                }
            } else {
                // Standard text-only layout.
                if (section) {
                    slide.addText(section.toUpperCase(), {
                        x: 0.8, y: 0.4, w: 5, h: 0.3,
                        fontSize: 9, bold: true, color: accent, letterSpacing: 2
                    });
                }
                slide.addText(sd.slide_title || '', {
                    x: 0.8, y: 0.8, w: 8.4, h: 0.8,
                    fontSize: 22, bold: true, color: 'FFFFFF'
                });
                if (sd.key_points && sd.key_points.length > 0) {
                    var stdBullets = sd.key_points.map(function(kp) {
                        return {
                            text: kp,
                            options: {
                                fontSize: 13, color: 'B0BEC5',
                                bullet: { type: 'bullet', color: accent },
                                lineSpacing: 20, paraSpaceAfter: 6
                            }
                        };
                    });
                    slide.addText(stdBullets, { x: 0.8, y: 1.8, w: 8.4, h: 2.8, valign: 'top' });
                }
                if (sd.data_points && sd.data_points.length > 0) {
                    slide.addText(sd.data_points.map(function(dp) { return '• ' + dp; }).join('   '), {
                        x: 0.8, y: 4.8, w: 8.4, h: 0.4, fontSize: 9, color: '78909C', italic: true
                    });
                }
            }
        };

        // =====================================================================
        // PROGRESS UI
        // =====================================================================

        CR._showImageProgress = function(totalImages) {
            var el = document.createElement('div');
            el.id = 'jc-slide-image-progress';
            el.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;'
                + 'background:rgba(15,43,70,0.92);z-index:99999;display:flex;'
                + 'align-items:center;justify-content:center;flex-direction:column;gap:16px';
            el.innerHTML = ''
                + '<div style="text-align:center;color:#fff;font-family:-apple-system,BlinkMacSystemFont,sans-serif">'
                + '<div style="font-size:14px;color:#42A5F5;font-weight:600;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">'
                + 'Generating AI Slide Images</div>'
                + '<div id="jc-img-progress-text" style="font-size:32px;font-weight:700;margin-bottom:12px">0 / ' + totalImages + '</div>'
                + '<div style="width:300px;height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden">'
                + '<div id="jc-img-progress-bar" style="width:0%;height:100%;background:linear-gradient(90deg,#42A5F5,#66BB6A);border-radius:3px;transition:width 0.4s ease"></div>'
                + '</div>'
                + '<div style="margin-top:12px;font-size:12px;color:#78909C">Using Nano Banana Pro for professional visuals</div>'
                + '</div>';
            document.body.appendChild(el);
            return el;
        };

        CR._updateImageProgress = function(el, done, total) {
            if (!el) return;
            var textEl = el.querySelector('#jc-img-progress-text');
            var barEl = el.querySelector('#jc-img-progress-bar');
            if (textEl) textEl.textContent = done + ' / ' + total;
            if (barEl) barEl.style.width = Math.round((done / total) * 100) + '%';
        };

        CR._hideImageProgress = function(el) {
            if (el && el.parentNode) {
                el.style.opacity = '0';
                el.style.transition = 'opacity 0.3s';
                setTimeout(function() {
                    if (el.parentNode) el.parentNode.removeChild(el);
                }, 300);
            }
        };

        // =====================================================================
        // OVERRIDE THE download() METHOD
        // =====================================================================

        // Store original download method.
        var _originalDownload = CR.download;

        /**
         * Enhanced download that adds:
         *   - Infographic → PNG via Nano Banana (AI-generated image)
         *   - Presentation → shapes-only PPTX by default (editable)
         *     Set window.JC_AI_IMAGES_ENABLED = true to use AI images instead
         */
        CR.download = function(content, format, filename, meta) {
            if (format === 'infographic') {
                this._downloadInfographicPng(content, filename, meta);
            } else if (format === 'presentation' && window.JC_AI_IMAGES_ENABLED === true) {
                // Only use AI images for presentations when explicitly enabled
                this._downloadPptxWithImages(content, filename, meta, {
                    useAiImages: true,
                    quality: CONFIG.quality
                });
            } else if (_originalDownload) {
                _originalDownload.call(this, content, format, filename, meta);
            }
        };

        /**
         * Download infographic as PNG via Nano Banana.
         *
         * Builds a single-image prompt from the infographic JSON, calls the
         * slide image endpoint, and downloads the result as a PNG file.
         */
        CR._downloadInfographicPng = function(content, filename, meta) {
            var self = this;
            var parsed = this._parseJson ? this._parseJson(content) : null;

            if (!parsed || !parsed.sections) {
                // Can't parse — fallback to HTML download
                if (_originalDownload) _originalDownload.call(this, content, 'infographic', filename, meta);
                return;
            }

            // Show progress overlay
            var progressEl = this._showImageProgress(1);
            this._updateImageProgress(progressEl, 0, 1);

            // Build the infographic as a single slide image request
            var keyPoints = [];
            var dataPoints = [];
            var sections = parsed.sections || [];
            for (var i = 0; i < sections.length; i++) {
                var sec = sections[i];
                if (sec.heading) keyPoints.push(sec.heading);
                if (sec.data_points) {
                    for (var d = 0; d < sec.data_points.length; d++) {
                        var dp = sec.data_points[d];
                        dataPoints.push((dp.label || '') + ': ' + (dp.value || ''));
                    }
                }
            }

            // Build visual element as a composite description for the whole infographic
            var visualElement = {
                type: 'infographic_full',
                data: {
                    title: parsed.title || '',
                    subtitle: parsed.subtitle || '',
                    sections: sections.map(function(sec) {
                        return {
                            heading: sec.heading || '',
                            description: sec.description || '',
                            data_points: sec.data_points || [],
                            visual_element: sec.visual_element || null
                        };
                    }),
                    footer: parsed.footer || '',
                    call_to_action: parsed.call_to_action || ''
                }
            };

            var payload = {
                slide_title:    parsed.title || 'Infographic',
                section:        'Infographic',
                key_points:     keyPoints,
                data_points:    dataPoints,
                visual_element: visualElement,
                quality:        CONFIG.quality
            };

            $.ajax({
                url: CONFIG.endpoint,
                method: 'POST',
                headers: CONFIG.nonce ? { 'X-WP-Nonce': CONFIG.nonce } : {},
                contentType: 'application/json',
                data: JSON.stringify(payload),
                timeout: CONFIG.timeout,
                success: function(response) {
                    self._updateImageProgress(progressEl, 1, 1);
                    setTimeout(function() { self._hideImageProgress(progressEl); }, 300);

                    if (response.success && response.image_base64) {
                        // Convert base64 to blob and download as PNG
                        var byteChars = atob(response.image_base64);
                        var byteNums = new Array(byteChars.length);
                        for (var i = 0; i < byteChars.length; i++) {
                            byteNums[i] = byteChars.charCodeAt(i);
                        }
                        var byteArray = new Uint8Array(byteNums);
                        var blob = new Blob([byteArray], { type: response.mime_type || 'image/png' });

                        var ext = (response.mime_type || '').indexOf('jpeg') !== -1 ? '.jpg' : '.png';
                        var url = URL.createObjectURL(blob);
                        var a = document.createElement('a');
                        a.href = url;
                        a.download = (filename || 'infographic') + ext;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        setTimeout(function() { URL.revokeObjectURL(url); }, 5000);
                    } else {
                        console.warn('[JC] No image returned for infographic, falling back to HTML');
                        if (_originalDownload) _originalDownload.call(self, content, 'infographic', filename, meta);
                    }
                },
                error: function(xhr, status, error) {
                    self._hideImageProgress(progressEl);
                    console.error('[JC] Infographic image generation failed:', status, error);
                    // Fallback to HTML download
                    if (_originalDownload) _originalDownload.call(self, content, 'infographic', filename, meta);
                }
            });
        };

        console.log('[JC] Slide image generator patched onto ContentRenderer');
    }

    // Initialize when DOM is ready.
    $(document).ready(function() {
        patchContentRenderer();
    });

    // =========================================================================
    // EXPOSE API
    // =========================================================================

    window.JCSlideImageGenerator = SlideImageGenerator;

    // Global toggle: set to true to enable AI images for PRESENTATION slides.
    // Default is false — presentations use editable PptxGenJS shapes.
    // Infographic PNG download always uses Nano Banana (not affected by this toggle).
    if (typeof window.JC_AI_IMAGES_ENABLED === 'undefined') {
        window.JC_AI_IMAGES_ENABLED = false;
    }

})(jQuery);