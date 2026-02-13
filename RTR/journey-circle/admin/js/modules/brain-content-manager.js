/**
 * Brain Content Manager - JavaScript Module
 * 
 * Handles resource intake for the Journey Circle:
 * - URL input
 * - Text paste
 * - File upload
 * - Resource list management
 * 
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0
 */

(function($) {
    'use strict';

    class BrainContentManager {
        constructor(workflow) {
            this.workflow = workflow;
            this.resources = [];
            
            this.init();
        }

        /**
         * Initialize brain content manager
         */
        init() {
            this.bindEvents();
            this.restoreResources();
            this.updateResourceCount();
            
            console.log('Brain Content Manager initialized');
        }

        /**
         * Bind event handlers
         */
        bindEvents() {
            // URL input
            $('.jc-add-url-btn').on('click', () => this.addURL());
            $('#jc-url-input').on('keypress', (e) => {
                if (e.which === 13) { // Enter key
                    e.preventDefault();
                    this.addURL();
                }
            });

            // Text paste
            $('.jc-paste-text-btn').on('click', () => this.openTextPasteModal());
            $('.jc-paste-submit-btn').on('click', () => this.addPastedText());
            $('.jc-modal-cancel, .jc-modal-close').on('click', () => this.closeTextPasteModal());

            // File upload
            $('#jc-file-input').on('change', (e) => this.handleFileSelect(e));
            
            // Drag and drop
            this.initDragDrop('#jc-file-upload-area', '#jc-file-input');

            // Delete resource
            $(document).on('click', '.jc-resource-delete', (e) => {
                const index = $(e.currentTarget).data('index');
                this.deleteResource(index);
            });

            // Restore state
            $(document).on('jc:restoreState', (e, state) => {
                if (state.brainContent) {
                    this.resources = state.brainContent;
                    this.renderResourceList();
                }
            });
        }

        /**
         * Add URL resource
         */
        addURL() {
            const url = $('#jc-url-input').val().trim();
            
            if (!url) {
                this.workflow.showNotification('Please enter a URL', 'error');
                return;
            }

            if (!this.isValidURL(url)) {
                this.workflow.showNotification('Please enter a valid URL', 'error');
                return;
            }

            // Check for duplicates
            if (this.resources.some(r => r.type === 'url' && r.value === url)) {
                this.workflow.showNotification('This URL has already been added', 'error');
                return;
            }

            // Add resource
            this.resources.push({
                type: 'url',
                value: url,
                name: this.extractDomain(url),
                addedAt: new Date().toISOString()
            });

            // Update UI
            $('#jc-url-input').val('');
            this.renderResourceList();
            this.updateResourceCount();
            this.saveToWorkflow();
            
            this.workflow.showNotification('URL added successfully', 'success');
        }

        /**
         * Open text paste modal
         */
        openTextPasteModal() {
            $('#jc-text-paste-modal').fadeIn(200);
            $('#jc-paste-textarea').focus();
        }

        /**
         * Close text paste modal
         */
        closeTextPasteModal() {
            $('#jc-text-paste-modal').fadeOut(200);
            $('#jc-paste-textarea').val('');
        }

        /**
         * Add pasted text
         */
        addPastedText() {
            const text = $('#jc-paste-textarea').val().trim();
            
            if (!text) {
                this.workflow.showNotification('Please paste some content', 'error');
                return;
            }

            if (text.length < 50) {
                this.workflow.showNotification('Please paste at least 50 characters of content', 'error');
                return;
            }

            // Add resource
            const preview = text.substring(0, 100) + (text.length > 100 ? '...' : '');
            this.resources.push({
                type: 'text',
                value: text,
                name: preview,
                addedAt: new Date().toISOString()
            });

            // Update UI
            this.closeTextPasteModal();
            this.renderResourceList();
            this.updateResourceCount();
            this.saveToWorkflow();
            
            this.workflow.showNotification('Text content added successfully', 'success');
        }

        /**
         * Handle file selection
         */
        handleFileSelect(event) {
            const files = event.target.files;
            
            if (files.length === 0) {
                return;
            }

            Array.from(files).forEach(file => {
                this.uploadFile(file);
            });
        }

        /**
         * Upload file
         */
        async uploadFile(file) {
            // Validate file
            const validation = this.validateFile(file);
            if (!validation.valid) {
                this.workflow.showNotification(validation.message, 'error');
                return;
            }

            // Show loading state
            const loadingId = this.addLoadingResource(file.name);

            try {
                // Create FormData
                const formData = new FormData();
                formData.append('file', file);
                formData.append('action', 'dr_upload_brain_content');
                formData.append('nonce', this.workflow.config.nonce);
                formData.append('client_id', this.workflow.config.clientId);

                // Upload via AJAX
                const response = await $.ajax({
                    url: this.workflow.config.ajaxUrl,
                    type: 'POST',
                    data: formData,
                    processData: false,
                    contentType: false
                });

                if (response.success) {
                    // Remove loading state
                    this.removeLoadingResource(loadingId);
                    
                    // Add uploaded file to resources
                    this.resources.push({
                        type: 'file',
                        value: response.data.url,
                        name: file.name,
                        fileId: response.data.id,
                        size: file.size,
                        addedAt: new Date().toISOString()
                    });

                    this.renderResourceList();
                    this.updateResourceCount();
                    this.saveToWorkflow();
                    
                    this.workflow.showNotification(`File "${file.name}" uploaded successfully`, 'success');
                } else {
                    throw new Error(response.data || 'Upload failed');
                }

            } catch (error) {
                this.removeLoadingResource(loadingId);
                this.workflow.showNotification(`Error uploading "${file.name}": ${error.message}`, 'error');
                console.error('File upload error:', error);
            }
        }

        /**
         * Delete resource
         */
        deleteResource(index) {
            if (!confirm('Are you sure you want to remove this resource?')) {
                return;
            }

            this.resources.splice(index, 1);
            this.renderResourceList();
            this.updateResourceCount();
            this.saveToWorkflow();
            
            this.workflow.showNotification('Resource removed', 'info');
        }

        /**
         * Render resource list
         */
        renderResourceList() {
            const $list = $('#jc-resource-list');
            
            if (this.resources.length === 0) {
                $list.html(`
                    <div class="jc-empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>No resources added yet</p>
                    </div>
                `);
                return;
            }

            $list.empty();
            
            this.resources.forEach((resource, index) => {
                const $item = this.createResourceItem(resource, index);
                $list.append($item);
            });
        }

        /**
         * Create resource item HTML
         */
        createResourceItem(resource, index) {
            let icon, subtitle;
            
            switch (resource.type) {
                case 'url':
                    icon = 'link';
                    subtitle = resource.value;
                    break;
                case 'text':
                    icon = 'file-alt';
                    subtitle = `${resource.value.length} characters`;
                    break;
                case 'file':
                    icon = 'file';
                    subtitle = this.formatFileSize(resource.size);
                    break;
            }

            return $(`
                <div class="jc-resource-item" data-index="${index}">
                    <div class="jc-resource-icon">
                        <i class="fas fa-${icon}"></i>
                    </div>
                    <div class="jc-resource-info">
                        <div class="jc-resource-name">${this.escapeHtml(resource.name)}</div>
                        <div class="jc-resource-subtitle">${subtitle}</div>
                    </div>
                    <button type="button" class="jc-resource-delete" data-index="${index}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `);
        }

        /**
         * Add loading resource
         */
        addLoadingResource(name) {
            const id = 'loading-' + Date.now();
            const $item = $(`
                <div class="jc-resource-item jc-resource-loading" id="${id}">
                    <div class="jc-resource-icon">
                        <i class="fas fa-spinner fa-spin"></i>
                    </div>
                    <div class="jc-resource-info">
                        <div class="jc-resource-name">${this.escapeHtml(name)}</div>
                        <div class="jc-resource-subtitle">Uploading...</div>
                    </div>
                </div>
            `);
            
            $('#jc-resource-list .jc-empty-state').remove();
            $('#jc-resource-list').append($item);
            
            return id;
        }

        /**
         * Remove loading resource
         */
        removeLoadingResource(id) {
            $(`#${id}`).fadeOut(200, function() {
                $(this).remove();
            });
        }

        /**
         * Update resource count
         */
        updateResourceCount() {
            $('.jc-resource-count').text(this.resources.length);
        }

        /**
         * Save resources to workflow state
         */
        saveToWorkflow() {
            this.workflow.updateState('brainContent', this.resources);
        }

        /**
         * Restore resources from state
         */
        restoreResources() {
            const savedResources = this.workflow.getState('brainContent');
            if (savedResources && savedResources.length > 0) {
                this.resources = savedResources;
                this.renderResourceList();
                this.updateResourceCount();
            }
        }

        /**
         * Initialize drag and drop
         */
        initDragDrop(dropZoneSelector, inputSelector) {
            const $dropZone = $(dropZoneSelector);
            
            $dropZone.on('dragover dragenter', function(e) {
                e.preventDefault();
                e.stopPropagation();
                $(this).addClass('jc-drag-over');
            });

            $dropZone.on('dragleave', function(e) {
                e.preventDefault();
                e.stopPropagation();
                $(this).removeClass('jc-drag-over');
            });

            $dropZone.on('drop', (e) => {
                e.preventDefault();
                e.stopPropagation();
                $dropZone.removeClass('jc-drag-over');
                
                const files = e.originalEvent.dataTransfer.files;
                if (files.length > 0) {
                    Array.from(files).forEach(file => {
                        this.uploadFile(file);
                    });
                }
            });
        }

        /**
         * Validate URL
         */
        isValidURL(string) {
            try {
                new URL(string);
                return true;
            } catch (_) {
                return false;
            }
        }

        /**
         * Extract domain from URL
         */
        extractDomain(url) {
            try {
                const urlObj = new URL(url);
                return urlObj.hostname;
            } catch (_) {
                return url;
            }
        }

        /**
         * Validate file
         */
        validateFile(file) {
            // Check file size
            if (file.size > this.workflow.config.maxFileSize) {
                return {
                    valid: false,
                    message: `File "${file.name}" is too large. Maximum size is ${this.formatFileSize(this.workflow.config.maxFileSize)}`
                };
            }

            // Check file type
            const extension = file.name.split('.').pop().toLowerCase();
            if (!this.workflow.config.allowedFileTypes.includes(extension)) {
                return {
                    valid: false,
                    message: `File type ".${extension}" is not allowed. Allowed types: ${this.workflow.config.allowedFileTypes.join(', ')}`
                };
            }

            return { valid: true };
        }

        /**
         * Format file size
         */
        formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }

        /**
         * Escape HTML
         */
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Initialize when workflow is ready
    $(document).ready(function() {
        if (window.drJourneyCircle) {
            window.drBrainContentManager = new BrainContentManager(window.drJourneyCircle);
        }
    });

})(jQuery);
