// ============================================================================
// PROFESSIONAL SCREENSHOT & RECORDING PROTECTION
// ============================================================================
// Version: 8.0 - Production Ready
// ============================================================================

(function() {
    'use strict';

    // ============================================================================
    // CONFIGURATION
    // ============================================================================
    const CONFIG = {
        enableWatermark: true,
        watermarkOpacity: 0.12,
        showWarnings: true,
        friendlyMessages: true,
        logToServer: true,
        
        // Exempted elements - these will work normally
        exemptedSelectors: [
            '.customer-sidebar',
            '.sidebar-nav',
            '.nav-link',
            '.customer-header',
            '.dropdown-menu',
            'a',
            'button',
            'form',
            'input',
            'textarea',
            'select',
            '.btn',
            '#tawk-bubble',
            '.tawk-chat-panel',
            'iframe[title*="chat" i]',
            'iframe[src*="tawk" i]',
        ]
    };

    let violationCount = 0;
    let isBlurActive = false;
    let userEmail = '';

    // ============================================================================
    // GET USER EMAIL
    // ============================================================================
    function getUserEmail() {
        const emailElement = document.querySelector('[data-user-email]');
        if (emailElement) {
            userEmail = emailElement.dataset.userEmail;
        }
        return userEmail || 'User';
    }

    // ============================================================================
    // GET CSRF TOKEN
    // ============================================================================
    function getCSRFToken() {
        let token = document.querySelector('[name=csrf-token]')?.content;
        if (!token) {
            token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        }
        if (!token) {
            const cookieValue = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='));
            if (cookieValue) {
                token = cookieValue.split('=')[1];
            }
        }
        return token;
    }

    // ============================================================================
    // CHECK IF ELEMENT IS EXEMPTED
    // ============================================================================
    function isExempted(element) {
        if (!element) return false;
        
        for (const selector of CONFIG.exemptedSelectors) {
            try {
                if (element.matches && element.matches(selector)) return true;
                if (element.closest && element.closest(selector)) return true;
            } catch (e) {
                continue;
            }
        }
        return false;
    }

    // ============================================================================
    // CHECK IF TAWK.TO IS ACTIVE
    // ============================================================================
    function isTawkActive() {
        const tawkElements = document.querySelectorAll(
            '#tawkchat-container, .tawk-chat-panel, #tawk-bubble, iframe[src*="tawk"]'
        );
        
        for (let el of tawkElements) {
            if (el && (el.offsetWidth > 0 || el.offsetHeight > 0)) {
                return true;
            }
        }
        return false;
    }

    // ============================================================================
    // CREATE WATERMARK
    // ============================================================================
    function createWatermark() {
        if (!CONFIG.enableWatermark) return;
        
        const email = getUserEmail();
        const timestamp = new Date().toLocaleString('en-IN', { 
            timeZone: 'Asia/Kolkata',
            dateStyle: 'short',
            timeStyle: 'short'
        });
        
        // Create watermark container
        const watermarkContainer = document.createElement('div');
        watermarkContainer.id = 'security-watermarks';
        watermarkContainer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 999999;
            user-select: none;
        `;
        
        // Positions for watermarks
        const positions = [
            { top: '5%', left: '5%' },
            { top: '5%', right: '5%' },
            { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' },
            { bottom: '5%', left: '5%' },
            { bottom: '5%', right: '5%' },
        ];
        
        positions.forEach(pos => {
            const mark = document.createElement('div');
            mark.className = 'watermark-text';
            mark.style.cssText = `
                position: absolute;
                ${pos.top ? `top: ${pos.top};` : ''}
                ${pos.bottom ? `bottom: ${pos.bottom};` : ''}
                ${pos.left ? `left: ${pos.left};` : ''}
                ${pos.right ? `right: ${pos.right};` : ''}
                ${pos.transform ? `transform: ${pos.transform};` : ''}
                color: rgba(255, 0, 0, ${CONFIG.watermarkOpacity});
                font-size: 12px;
                font-weight: 600;
                font-family: Arial, sans-serif;
                white-space: nowrap;
                pointer-events: none;
                user-select: none;
            `;
            mark.textContent = `${email} | ${timestamp}`;
            watermarkContainer.appendChild(mark);
        });
        
        document.body.appendChild(watermarkContainer);
        console.log('✅ Watermark applied');
    }

    // ============================================================================
    // SHOW FRIENDLY WARNING
    // ============================================================================
    function showFriendlyWarning(title, message) {
        if (!CONFIG.showWarnings) return;
        
        // Remove existing warning
        const existing = document.getElementById('friendly-warning');
        if (existing) existing.remove();
        
        const warning = document.createElement('div');
        warning.id = 'friendly-warning';
        warning.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 50px rgba(0,0,0,0.3);
            z-index: 2147483647;
            max-width: 400px;
            text-align: center;
            animation: slideIn 0.3s ease;
        `;
        
        warning.innerHTML = `
            <style>
                @keyframes slideIn {
                    from { opacity: 0; transform: translate(-50%, -60%); }
                    to { opacity: 1; transform: translate(-50%, -50%); }
                }
            </style>
            <div style="color: #f59e0b; font-size: 50px; margin-bottom: 15px;">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <h3 style="color: #1f2937; margin: 0 0 10px 0; font-size: 20px;">${title}</h3>
            <p style="color: #6b7280; margin: 0 0 20px 0; font-size: 14px; line-height: 1.6;">
                ${message}
            </p>
            <button onclick="this.parentElement.remove()" 
                    style="background: #087fc2; color: white; border: none; padding: 12px 30px; 
                           border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: 600;">
                Understood
            </button>
        `;
        
        document.body.appendChild(warning);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (warning.parentElement) {
                warning.style.opacity = '0';
                warning.style.transition = 'opacity 0.3s';
                setTimeout(() => warning.remove(), 300);
            }
        }, 5000);
    }

    // ============================================================================
    // SHOW BLUR OVERLAY
    // ============================================================================
    function showBlurOverlay() {
        if (isBlurActive || isTawkActive()) return;
        
        const overlay = document.createElement('div');
        overlay.id = 'blur-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            z-index: 2147483645;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
            animation: fadeIn 0.2s ease;
        `;
        
        overlay.innerHTML = `
            <style>
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
            </style>
            <div style="text-align: center; color: #087fc2;">
                <i class="fas fa-shield-alt" style="font-size: 70px; margin-bottom: 20px; display: block;"></i>
                <div style="font-size: 24px; font-weight: 700;">Content Protected</div>
                <div style="font-size: 14px; margin-top: 10px; opacity: 0.7;">
                    This content is protected
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        isBlurActive = true;
    }

    function hideBlurOverlay() {
        const overlay = document.getElementById('blur-overlay');
        if (overlay) {
            overlay.remove();
            isBlurActive = false;
        }
    }

    // ============================================================================
    // LOG VIOLATION TO SERVER
    // ============================================================================
    function logViolation(type, description) {
        if (!CONFIG.logToServer) return;
        
        violationCount++;
        
        const csrfToken = getCSRFToken();
        if (!csrfToken) {
            console.warn('⚠️ CSRF token not found');
            return;
        }
        
        const payload = {
            violation_type: type,
            description: description,
            timestamp: new Date().toISOString(),
            page_url: window.location.href,
            user_agent: navigator.userAgent,
            user_email: getUserEmail()
        };
        
        fetch('/customer/ajax/log-security-violation/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(payload),
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            console.log('✅ Violation logged');
        })
        .catch(error => {
            console.warn('⚠️ Logging failed:', error);
        });
    }

    // ============================================================================
    // SCREENSHOT DETECTION
    // ============================================================================
    function setupScreenshotDetection() {
        
        // Window Blur Detection
        window.addEventListener('blur', function() {
            if (isTawkActive()) return;
            
            showBlurOverlay();
            
            setTimeout(() => {
                if (document.hidden || !document.hasFocus()) {
                    showFriendlyWarning(
                        'Screenshot Detected?',
                        'Screenshot attempt detected. This action has been recorded.'
                    );
                    logViolation('window_blur', 'Window focus lost - Potential screenshot');
                }
            }, 200);
        });

        window.addEventListener('focus', function() {
            hideBlurOverlay();
        });

        // Visibility Change
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                showBlurOverlay();
                logViolation('visibility_change', 'Page hidden - Potential screenshot');
            } else {
                hideBlurOverlay();
            }
        });

        // PrintScreen Key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'PrintScreen' || e.keyCode === 44) {
                e.preventDefault();
                
                showFriendlyWarning(
                    'PrintScreen Blocked',
                    'PrintScreen button is disabled. This action has been recorded.'
                );
                
                navigator.clipboard.writeText('').catch(() => {});
                logViolation('printscreen_key', 'PrintScreen key pressed');
                
                return false;
            }
        });

        document.addEventListener('keyup', function(e) {
            if (e.key === 'PrintScreen' || e.keyCode === 44) {
                navigator.clipboard.writeText('').catch(() => {});
            }
        });

        // Clipboard Monitoring
        setInterval(async function() {
            if (document.hidden || !document.hasFocus()) return;
            
            try {
                const items = await navigator.clipboard.read();
                
                for (const item of items) {
                    if (item.types.some(type => type.startsWith('image/'))) {
                        await navigator.clipboard.writeText('');
                        
                        showFriendlyWarning(
                            'Screenshot Detected',
                            'Screenshot found in clipboard and removed.'
                        );
                        
                        logViolation('clipboard_image', 'Screenshot detected in clipboard');
                        break;
                    }
                }
            } catch (err) {
                // Permission denied or not supported
            }
        }, 1000);

        // Screen Capture API Blocking
        if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
            const originalGetDisplayMedia = navigator.mediaDevices.getDisplayMedia;
            
            navigator.mediaDevices.getDisplayMedia = function() {
                showFriendlyWarning(
                    'Screen Capture Blocked',
                    'Screen recording is not allowed.'
                );
                
                logViolation('screen_capture', 'Screen capture API blocked');
                return Promise.reject(new Error('Screen capture not allowed'));
            };
        }
    }

    // ============================================================================
    // KEYBOARD PROTECTION
    // ============================================================================
    function setupKeyboardProtection() {
        
        document.addEventListener('keydown', function(e) {
            // Skip if exempted element
            if (isExempted(document.activeElement)) return true;
            
            let shouldBlock = false;
            let message = '';

            // DevTools
            if (e.key === 'F12' || 
                (e.ctrlKey && e.shiftKey && ['I', 'J', 'C'].includes(e.key.toUpperCase()))) {
                shouldBlock = true;
                message = 'Developer tools are disabled for security reasons.';
            }
            // View Source
            else if (e.ctrlKey && e.key.toUpperCase() === 'U') {
                shouldBlock = true;
                message = 'View source is disabled for security reasons.';
            }
            // Save Page
            else if (e.ctrlKey && e.key.toUpperCase() === 'S') {
                shouldBlock = true;
                message = 'Saving page is disabled for security reasons.';
            }
            // Print
            else if (e.ctrlKey && e.key.toUpperCase() === 'P') {
                shouldBlock = true;
                message = 'Printing is disabled for security reasons.';
            }

            if (shouldBlock) {
                e.preventDefault();
                e.stopPropagation();
                
                if (CONFIG.friendlyMessages) {
                    showFriendlyWarning('Action Blocked', message);
                }
                
                logViolation('keyboard_shortcut', message);
                return false;
            }
        }, true);

        // Right-click
        document.addEventListener('contextmenu', function(e) {
            // Allow on exempted elements
            if (isExempted(e.target)) return true;
            
            // Allow on form elements
            const allowedElements = ['INPUT', 'TEXTAREA', 'SELECT'];
            if (allowedElements.includes(e.target.tagName)) return true;
            
            e.preventDefault();
            e.stopPropagation();
            
            if (CONFIG.friendlyMessages) {
                showFriendlyWarning(
                    'Right-Click Disabled',
                    'Right-click is disabled for security.'
                );
            }
            
            logViolation('right_click', 'Right-click blocked');
            return false;
        }, true);
    }

    // ============================================================================
    // SELECTION & COPY PROTECTION
    // ============================================================================
    function setupSelectionProtection() {
        
        // Prevent text selection
        document.addEventListener('selectstart', function(e) {
            if (isExempted(e.target)) return true;
            
            const allowedElements = ['INPUT', 'TEXTAREA', 'SELECT'];
            if (allowedElements.includes(e.target.tagName)) return true;
            
            e.preventDefault();
            return false;
        }, true);

        // Prevent copy
        document.addEventListener('copy', function(e) {
            if (isExempted(document.activeElement)) return true;
            
            const allowedElements = ['INPUT', 'TEXTAREA', 'SELECT'];
            if (allowedElements.includes(document.activeElement.tagName)) return true;
            
            e.preventDefault();
            e.stopPropagation();
            
            navigator.clipboard.writeText('').catch(() => {});
            
            if (CONFIG.friendlyMessages) {
                showFriendlyWarning(
                    'Copy Disabled',
                    'Copying is disabled for security.'
                );
            }
            
            logViolation('copy_blocked', 'Copy attempt blocked');
            return false;
        }, true);

        // Prevent drag
        document.addEventListener('dragstart', function(e) {
            if (e.target.tagName === 'IMG' || e.target.tagName === 'VIDEO') {
                e.preventDefault();
                logViolation('drag_blocked', 'Drag attempt on media');
                return false;
            }
        }, true);
    }

    // ============================================================================
    // INJECT STYLES
    // ============================================================================
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Disable text selection globally */
            body, * {
                -webkit-user-select: none !important;
                -moz-user-select: none !important;
                user-select: none !important;
            }

            /* Enable selection for form elements and navigation */
            input, textarea, select, button, a,
            .customer-sidebar, .nav-link, .btn,
            [contenteditable="true"] {
                -webkit-user-select: text !important;
                -moz-user-select: text !important;
                user-select: text !important;
            }

            /* Disable drag for media */
            img, video, canvas {
                -webkit-user-drag: none !important;
                user-drag: none !important;
                pointer-events: none !important;
            }

            /* Enable pointer events for interactive elements */
            button, a, input, textarea, select, .btn {
                pointer-events: auto !important;
            }

            /* Hide video controls */
            video::-webkit-media-controls {
                display: none !important;
            }

            /* Disable selection highlight */
            ::selection {
                background: transparent !important;
            }

            ::-moz-selection {
                background: transparent !important;
            }
        `;
        document.head.appendChild(style);
    }

    // ============================================================================
    // INITIALIZE ALL PROTECTIONS
    // ============================================================================
    function initialize() {
        console.log('%c🔒 Security Protection Active', 
            'color: #087fc2; font-size: 16px; font-weight: bold;');
        
        getUserEmail();
        injectStyles();
        createWatermark();
        setupScreenshotDetection();
        setupKeyboardProtection();
        setupSelectionProtection();
        
        console.log('✅ All security systems initialized');
        console.log('📧 User:', getUserEmail());
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    // Re-initialize on page show
    window.addEventListener('pageshow', function(event) {
        if (event.persisted) {
            initialize();
        }
    });

})();