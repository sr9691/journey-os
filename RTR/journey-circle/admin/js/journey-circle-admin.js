/**
 * Journey Circle Admin JavaScript
 *
 * @package Journey_Circle
 */

(function($) {
    'use strict';

    /**
     * Journey Circle Admin Manager
     */
    const JourneyCircleAdmin = {
        
        /**
         * Initialize
         */
        init: function() {
            this.bindEvents();
            this.checkRequirements();
        },
        
        /**
         * Bind event listeners
         */
        bindEvents: function() {
            // Quick action buttons
            $('.jc-actions-grid .button').on('click', function(e) {
                const $btn = $(this);
                $btn.addClass('jc-loading');
            });
        },
        
        /**
         * Check plugin requirements
         */
        checkRequirements: function() {
            // Check if REST API is available
            if (typeof journeyCircleData === 'undefined') {
                console.warn('Journey Circle: REST API data not available');
                return;
            }
            
            console.log('Journey Circle initialized with REST API:', journeyCircleData.restUrl);
        },
        
        /**
         * Make API request
         */
        apiRequest: function(endpoint, method, data, callback) {
            method = method || 'GET';
            data = data || {};
            
            const settings = {
                url: journeyCircleData.restUrl + '/' + endpoint,
                method: method,
                dataType: 'json',
                headers: {
                    'X-WP-Nonce': journeyCircleData.restNonce
                },
                success: function(response) {
                    if (typeof callback === 'function') {
                        callback(null, response);
                    }
                },
                error: function(xhr, status, error) {
                    if (typeof callback === 'function') {
                        callback(error, null);
                    }
                }
            };
            
            if (method !== 'GET') {
                settings.data = JSON.stringify(data);
                settings.contentType = 'application/json';
            }
            
            $.ajax(settings);
        },
        
        /**
         * Show notice
         */
        showNotice: function(message, type) {
            type = type || 'info';
            
            const $notice = $('<div>')
                .addClass('jc-notice jc-notice-' + type)
                .text(message);
            
            $('.wrap h1').after($notice);
            
            setTimeout(function() {
                $notice.fadeOut(function() {
                    $(this).remove();
                });
            }, 5000);
        },
        
        /**
         * Confirm action
         */
        confirm: function(message, callback) {
            if (window.confirm(message)) {
                if (typeof callback === 'function') {
                    callback();
                }
            }
        }
    };

    /**
     * Initialize on document ready
     */
    $(document).ready(function() {
        JourneyCircleAdmin.init();
    });

    // Make available globally
    window.JourneyCircleAdmin = JourneyCircleAdmin;

})(jQuery);
