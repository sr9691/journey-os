/**
 * Journey Circle Notification System
 *
 * Mirrors Campaign Builder's NotificationSystem (notifications.js + base.css)
 * so both apps share identical alert styling, positioning, and behavior.
 *
 * CB's base.css provides the styles for:
 *   .notification-container   – fixed top-right wrapper
 *   .notification             – white card with slideIn animation
 *   .notification-{type}      – colored left border (success/error/warning/info)
 *   .notification::before     – Font Awesome icon via pseudo-element
 *   .notification-close       – dismiss button
 *   .notification.fade-out    – slideOut animation
 *
 * Usage (from any JC module):
 *   window.JCNotifications.success('Saved!');
 *   window.JCNotifications.error('Something went wrong');
 *   window.JCNotifications.warning('Please select an item');
 *   window.JCNotifications.info('Generating content…');
 *   window.JCNotifications.show('custom', 'Message');   // custom type
 *
 * @package DirectReach_Campaign_Builder
 * @subpackage Journey_Circle
 * @since 2.0.0
 */
(function() {
    'use strict';

    const JCNotifications = {

        /** @type {HTMLElement|null} Cached container reference */
        _container: null,

        /**
         * Default auto-dismiss delay in milliseconds.
         * CB uses 3 000 ms which is too fast for longer messages.
         * 6 000 ms gives users time to read without being annoying.
         */
        defaultDuration: 6000,

        /* ------------------------------------------------------------------ */
        /*  Convenience helpers                                                */
        /* ------------------------------------------------------------------ */

        success(message, duration) {
            return this.show('success', message, duration);
        },

        error(message, duration) {
            return this.show('error', message, duration);
        },

        warning(message, duration) {
            return this.show('warning', message, duration);
        },

        info(message, duration) {
            return this.show('info', message, duration);
        },

        /* ------------------------------------------------------------------ */
        /*  Core show method                                                   */
        /* ------------------------------------------------------------------ */

        /**
         * Display a notification.
         *
         * @param {string}  type     One of 'success', 'error', 'warning', 'info'
         * @param {string}  message  Plain-text or safe HTML message
         * @param {number=} duration Auto-dismiss ms (0 = manual dismiss only)
         * @returns {HTMLElement}     The notification element (for programmatic control)
         */
        show(type, message, duration) {
            const container = this._getContainer();

            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;

            // Markup matches CB's NotificationSystem exactly:
            //   ::before pseudo-element provides the icon (from base.css)
            //   <span> holds the message
            //   <button> is the close control
            notification.innerHTML =
                '<span>' + this._escapeHtml(message) + '</span>' +
                '<button class="notification-close" title="Dismiss">' +
                    '<i class="fas fa-times"></i>' +
                '</button>';

            container.appendChild(notification);

            // Close button
            notification.querySelector('.notification-close')
                .addEventListener('click', () => this._dismiss(notification));

            // Auto-dismiss
            const ms = (duration !== undefined) ? duration : this.defaultDuration;
            if (ms > 0) {
                notification._autoTimer = setTimeout(() => {
                    this._dismiss(notification);
                }, ms);
            }

            return notification;
        },

        /* ------------------------------------------------------------------ */
        /*  Dismiss                                                            */
        /* ------------------------------------------------------------------ */

        /**
         * Dismiss a single notification with the slideOut animation.
         *
         * @param {HTMLElement} notification
         */
        _dismiss(notification) {
            if (!notification || !notification.parentNode) return;

            // Clear pending auto-dismiss so we don't double-fire
            if (notification._autoTimer) {
                clearTimeout(notification._autoTimer);
                notification._autoTimer = null;
            }

            notification.classList.add('fade-out');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300); // matches slideOut duration in base.css
        },

        /**
         * Dismiss all visible notifications immediately.
         */
        dismissAll() {
            const container = this._getContainer();
            container.querySelectorAll('.notification').forEach(n => this._dismiss(n));
        },

        /* ------------------------------------------------------------------ */
        /*  Container management                                               */
        /* ------------------------------------------------------------------ */

        /**
         * Get or create the .notification-container element.
         * Re-uses an existing one if CB already created it (unlikely on the
         * JC full-page, but defensive coding).
         *
         * @returns {HTMLElement}
         */
        _getContainer() {
            if (this._container && this._container.parentNode) {
                return this._container;
            }

            let container = document.querySelector('.notification-container');
            if (!container) {
                container = document.createElement('div');
                container.className = 'notification-container';
                document.body.appendChild(container);
            }

            this._container = container;
            return container;
        },

        /* ------------------------------------------------------------------ */
        /*  Utility                                                            */
        /* ------------------------------------------------------------------ */

        /**
         * Basic HTML-entity escaping.
         */
        _escapeHtml(str) {
            if (!str) return '';
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }
    };

    // Expose globally so every JC module can use it
    window.JCNotifications = JCNotifications;

})();
