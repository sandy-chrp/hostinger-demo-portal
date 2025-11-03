// ============================================================================
// MAXIMUM PROTECTION - WITH WATERMARK & AGGRESSIVE DETECTION
// ============================================================================
// Version: 6.0 | Ultimate Protection
// ============================================================================

(function() {
    'use strict';

    const CONFIG = {
        enableWatermark: true,              // ✅ WATERMARK ENABLE
        watermarkOpacity: 0.15,             // Watermark visibility
        enableBlurOnFocusLoss: true,
        enableScreenshotDetection: true,
        enableRecordingDetection: true,
        enableAggressiveBlocking: true,
        logViolations: true,
        blockDevTools: true,
        blackScreenOnSuspicious: true,
        
        exemptedSelectors: [
            '.customer-sidebar',
            '.sidebar-nav',
            '.nav-link',
            '.customer-header',
            '.dropdown-menu',
            'a[href^="/customer/"]',
            'a[href^="/accounts/"]',
            'button[data-bs-toggle]',
            '.btn',
            'form',
            'input',
            'textarea',
            'select',
            '#tawk-bubble',
            '.tawk-min-container',
            '.tawk-chat-panel',
            'iframe[title*="chat" i]',
            'iframe[src*="tawk" i]',
        ]
    };

    let violationCount = 0;
    let suspiciousActivityLevel = 0;
    let lastViolationTime = 0;
    let blurOverlayActive = false;

    // ============================================================================
    // WATERMARK SYSTEM
    // ============================================================================
    
    function createWatermark() {
        if (!CONFIG.enableWatermark) return;
        
        const userEmail = document.querySelector('[data-user-email]')?.dataset.userEmail || 'PROTECTED';
        const timestamp = new Date().toLocaleString();
        
        // Create multiple watermarks for better coverage
        const positions = [
            { top: '10%', left: '10%' },
            { top: '10%', right: '10%' },
            { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' },
            { bottom: '10%', left: '10%' },
            { bottom: '10%', right: '10%' },
            { top: '30%', left: '30%' },
            { top: '30%', right: '30%' },
            { bottom: '30%', left: '30%' },
            { bottom: '30%', right: '30%' },
        ];
        
        positions.forEach((pos, index) => {
            const watermark = document.createElement('div');
            watermark.className = 'security-watermark';
            watermark.style.cssText = `
                position: fixed;
                ${pos.top ? `top: ${pos.top};` : ''}
                ${pos.bottom ? `bottom: ${pos.bottom};` : ''}
                ${pos.left ? `left: ${pos.left};` : ''}
                ${pos.right ? `right: ${pos.right};` : ''}
                ${pos.transform ? `transform: ${pos.transform};` : ''}
                color: rgba(255, 0, 0, ${CONFIG.watermarkOpacity});
                font-size: 14px;
                font-weight: bold;
                pointer-events: none;
                z-index: 99999;
                user-select: none;
                font-family: Arial, sans-serif;
                white-space: nowrap;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            `;
            watermark.textContent = `${userEmail} | ${timestamp}`;
            document.body.appendChild(watermark);
        });
        
        // Diagonal watermarks
        for (let i = 0; i < 5; i++) {
            const diagonalWatermark = document.createElement('div');
            diagonalWatermark.className = 'security-watermark';
            diagonalWatermark.style.cssText = `
                position: fixed;
                top: ${20 + (i * 15)}%;
                left: 0;
                width: 100%;
                text-align: center;
                color: rgba(255, 0, 0, ${CONFIG.watermarkOpacity});
                font-size: 16px;
                font-weight: bold;
                pointer-events: none;
                z-index: 99999;
                user-select: none;
                font-family: Arial, sans-serif;
                transform: rotate(-45deg);
                opacity: 0.5;
            `;
            diagonalWatermark.textContent = `${userEmail} - CONFIDENTIAL - ${timestamp}`;
            document.body.appendChild(diagonalWatermark);
        }
        
        console.log('🔐 Watermarks applied');
    }

    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================
    
    function isExemptedElement(element) {
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

    function isTawkActive() {
        const tawkElements = document.querySelectorAll(
            '#tawkchat-container, .tawk-chat-panel, #tawk-bubble, ' +
            'iframe[title*="chat" i], iframe[src*="tawk" i]'
        );
        
        for (let el of tawkElements) {
            if (el && (el.offsetWidth > 0 || el.offsetHeight > 0)) {
                return true;
            }
        }
        return false;
    }

    // ============================================================================
    // BLUR OVERLAY SYSTEM
    // ============================================================================
    
    function showBlurOverlay() {
        if (blurOverlayActive || isTawkActive()) return;
        
        const overlay = document.createElement('div');
        overlay.id = 'security-blur-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            z-index: 2147483646;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
        `;
        
        overlay.innerHTML = `
            <div style="text-align: center; color: #087fc2; font-size: 28px; font-weight: bold;">
                <i class="fas fa-shield-alt" style="font-size: 80px; margin-bottom: 30px; display: block;"></i>
                <div>CONTENT PROTECTED</div>
                <div style="font-size: 16px; margin-top: 15px; opacity: 0.7;">
                    Click to continue viewing
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        blurOverlayActive = true;
        
        logViolation('content_blurred', 'Content hidden due to focus loss');
    }

    function hideBlurOverlay() {
        const overlay = document.getElementById('security-blur-overlay');
        if (overlay) {
            overlay.remove();
            blurOverlayActive = false;
        }
    }

    // ============================================================================
    // BLACK SCREEN SYSTEM
    // ============================================================================
    
    function showBlackScreen(reason = 'Suspicious activity detected') {
        const existing = document.getElementById('security-black-screen');
        if (existing) return;
        
        const blackScreen = document.createElement('div');
        blackScreen.id = 'security-black-screen';
        blackScreen.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: #000000;
            z-index: 2147483647;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: all;
        `;
        
        const userEmail = document.querySelector('[data-user-email]')?.dataset.userEmail || 'User';
        const timestamp = new Date().toLocaleString();
        
        blackScreen.innerHTML = `
            <div style="text-align: center; color: #ffffff; font-size: 24px; font-weight: bold; padding: 40px;">
                <i class="fas fa-ban" style="font-size: 80px; margin-bottom: 30px; display: block; color: #ef4444;"></i>
                <div>⛔ SCREENSHOT/RECORDING BLOCKED</div>
                <div style="font-size: 16px; margin-top: 15px; opacity: 0.8;">
                    ${reason}
                </div>
                <div style="font-size: 14px; margin-top: 20px; opacity: 0.6; color: #ef4444;">
                    User: ${userEmail}<br>
                    Time: ${timestamp}<br>
                    This violation has been logged and reported
                </div>
                <button onclick="this.parentElement.parentElement.remove()" 
                        style="margin-top: 30px; background: #ef4444; color: white; border: none; 
                               padding: 15px 40px; border-radius: 10px; cursor: pointer; font-size: 17px;">
                    I Understand - Close Warning
                </button>
            </div>
        `;
        
        document.body.appendChild(blackScreen);
        
        setTimeout(() => {
            if (blackScreen.parentElement) {
                blackScreen.style.opacity = '0';
                blackScreen.style.transition = 'opacity 0.3s';
                setTimeout(() => blackScreen.remove(), 300);
            }
        }, 5000);
        
        logViolation('black_screen_triggered', reason);
    }

    // ============================================================================
    // SCREENSHOT DETECTION
    // ============================================================================
    
    function detectScreenshot() {
        if (!CONFIG.enableScreenshotDetection) return;
        
        // Window Blur - INSTANT RESPONSE
        window.addEventListener('blur', function() {
            if (isTawkActive()) return;
            
            const now = Date.now();
            lastViolationTime = now;
            
            showBlurOverlay();
            
            if (CONFIG.enableAggressiveBlocking) {
                setTimeout(() => {
                    if (document.hidden || !document.hasFocus()) {
                        showBlackScreen('Window focus lost - Screenshot/Recording attempt detected');
                    }
                }, 200);
            }
            
            logViolation('window_blur', 'Focus lost - Potential screenshot/recording');
        });

        window.addEventListener('focus', function() {
            hideBlurOverlay();
        });

        // Visibility Change
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                showBlurOverlay();
                
                if (!isTawkActive() && CONFIG.enableAggressiveBlocking) {
                    setTimeout(() => {
                        if (document.hidden) {
                            showBlackScreen('Tab hidden - Screenshot/Recording blocked');
                        }
                    }, 300);
                }
                
                logViolation('visibility_hidden', 'Page hidden - Potential capture');
            } else {
                hideBlurOverlay();
            }
        });

        // PrintScreen Key
        let printScreenPressed = false;
        
        document.addEventListener('keydown', function(e) {
            if (e.key === 'PrintScreen' || e.keyCode === 44) {
                e.preventDefault();
                e.stopPropagation();
                printScreenPressed = true;
                
                showBlackScreen('PrintScreen key blocked');
                navigator.clipboard.writeText('SCREENSHOT BLOCKED - VIOLATION LOGGED').catch(() => {});
                logViolation('printscreen_key', 'PrintScreen key pressed');
                
                return false;
            }
            
            // Windows Snipping Tool (Win+Shift+S)
            if (e.key === 'Meta' && e.shiftKey && e.code === 'KeyS') {
                e.preventDefault();
                e.stopPropagation();
                showBlackScreen('Windows Snipping Tool blocked');
                logViolation('snipping_tool', 'Snipping Tool shortcut detected');
                return false;
            }
        });

        document.addEventListener('keyup', function(e) {
            if (e.key === 'PrintScreen' || e.keyCode === 44) {
                if (printScreenPressed) {
                    navigator.clipboard.writeText('SCREENSHOT BLOCKED').catch(() => {});
                    printScreenPressed = false;
                }
            }
        });

        // Aggressive Clipboard Monitoring
        setInterval(async function() {
            if (document.hidden || !document.hasFocus()) return;
            
            try {
                const items = await navigator.clipboard.read();
                
                for (const item of items) {
                    if (item.types.some(type => type.startsWith('image/'))) {
                        await navigator.clipboard.writeText('SCREENSHOT BLOCKED - VIOLATION LOGGED');
                        showBlackScreen('Screenshot detected in clipboard and cleared');
                        logViolation('clipboard_image', 'Screenshot found in clipboard');
                        suspiciousActivityLevel += 3;
                        break;
                    }
                }
            } catch (err) {
                // Permission denied
            }
        }, 300); // Check every 300ms

        // Mouse Leave Detection
        let mouseLeaveCount = 0;
        let lastMouseLeave = 0;
        
        document.addEventListener('mouseleave', function(e) {
            if (e.clientY < 0) {
                const now = Date.now();
                if (now - lastMouseLeave < 2000) {
                    mouseLeaveCount++;
                } else {
                    mouseLeaveCount = 1;
                }
                lastMouseLeave = now;
                
                if (mouseLeaveCount > 1) {
                    showBlackScreen('Suspicious mouse activity detected');
                    logViolation('suspicious_mouse', `Mouse left top ${mouseLeaveCount} times`);
                    mouseLeaveCount = 0;
                }
            }
        });

        // Screen Capture API
        if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
            const originalGetDisplayMedia = navigator.mediaDevices.getDisplayMedia;
            
            navigator.mediaDevices.getDisplayMedia = function() {
                showBlackScreen('Screen capture API blocked');
                logViolation('getDisplayMedia', 'Screen capture API intercepted');
                return Promise.reject(new Error('Screen capture not allowed'));
            };
        }
    }

    // ============================================================================
    // SCREEN RECORDING DETECTION
    // ============================================================================
    
    function detectScreenRecording() {
        if (!CONFIG.enableRecordingDetection) return;
        
        // Block getUserMedia video
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            const originalGetUserMedia = navigator.mediaDevices.getUserMedia;
            
            navigator.mediaDevices.getUserMedia = function(constraints) {
                if (constraints && constraints.video) {
                    showBlackScreen('Video capture blocked');
                    logViolation('getUserMedia_video', 'Video capture attempt');
                    return Promise.reject(new Error('Video capture not allowed'));
                }
                return originalGetUserMedia.call(this, constraints);
            };
        }

        // Detect recording software patterns
        setInterval(function() {
            const widthDiff = window.outerWidth - window.innerWidth;
            const heightDiff = window.outerHeight - window.innerHeight;
            
            if (widthDiff > 300 || heightDiff > 300) {
                logViolation('recording_software', 'Recording software pattern detected');
            }
        }, 10000);
    }

    // ============================================================================
    // KEYBOARD PROTECTION
    // ============================================================================
    
    function protectKeyboard() {
        document.addEventListener('keydown', function(e) {
            if (isExemptedElement(document.activeElement)) return true;
            
            let shouldBlock = false;
            let message = '';

            if (e.key === 'F12' || 
                (e.ctrlKey && e.shiftKey && ['I', 'J', 'C'].includes(e.key.toUpperCase()))) {
                shouldBlock = true;
                message = 'Developer tools blocked';
            }
            else if (e.ctrlKey && e.key.toUpperCase() === 'U') {
                shouldBlock = true;
                message = 'View source blocked';
            }
            else if (e.ctrlKey && e.key.toUpperCase() === 'S') {
                shouldBlock = true;
                message = 'Save page blocked';
            }
            else if (e.ctrlKey && e.key.toUpperCase() === 'P') {
                shouldBlock = true;
                message = 'Print blocked';
            }

            if (shouldBlock) {
                e.preventDefault();
                e.stopPropagation();
                
                if (CONFIG.enableAggressiveBlocking) {
                    showBlackScreen(message);
                }
                
                logViolation('keyboard_shortcut', message);
                return false;
            }
        }, true);

        // Right-click blocking
        document.addEventListener('contextmenu', function(e) {
            if (isExemptedElement(e.target)) return true;
            
            const allowedElements = ['INPUT', 'TEXTAREA', 'SELECT'];
            if (allowedElements.includes(e.target.tagName)) return true;
            
            e.preventDefault();
            e.stopPropagation();
            
            if (CONFIG.enableAggressiveBlocking) {
                showBlackScreen('Right-click blocked');
            }
            
            logViolation('right_click', 'Right-click blocked');
            return false;
        }, true);
    }

    // ============================================================================
    // SELECTION & COPY PROTECTION
    // ============================================================================
    
    function protectSelection() {
        document.addEventListener('selectstart', function(e) {
            if (isExemptedElement(e.target)) return true;
            
            const allowedElements = ['INPUT', 'TEXTAREA', 'SELECT'];
            if (allowedElements.includes(e.target.tagName)) return true;
            
            e.preventDefault();
            return false;
        }, true);

        document.addEventListener('copy', function(e) {
            if (isExemptedElement(document.activeElement)) return true;
            
            const allowedElements = ['INPUT', 'TEXTAREA', 'SELECT'];
            if (allowedElements.includes(document.activeElement.tagName)) return true;
            
            e.preventDefault();
            e.stopPropagation();
            
            navigator.clipboard.writeText('').catch(() => {});
            
            if (CONFIG.enableAggressiveBlocking) {
                showBlackScreen('Copy blocked');
            }
            
            logViolation('copy_blocked', 'Copy attempt');
            return false;
        }, true);

        document.addEventListener('dragstart', function(e) {
            if (e.target.tagName === 'IMG' || e.target.tagName === 'VIDEO') {
                e.preventDefault();
                logViolation('drag_blocked', 'Drag blocked');
                return false;
            }
        }, true);
    }

    // ============================================================================
    // LOGGING SYSTEM
    // ============================================================================
    
    let logQueue = [];
    let isLogging = false;

    function logViolation(type, description) {
        if (!CONFIG.logViolations) return;
        
        violationCount++;
        suspiciousActivityLevel++;
        
        const userEmail = document.querySelector('[data-user-email]')?.dataset.userEmail || 'Unknown';
        
        logQueue.push({
            type: type,
            description: `${description} [User: ${userEmail}, Count: ${violationCount}, Level: ${suspiciousActivityLevel}]`,
            timestamp: new Date().toISOString(),
            userEmail: userEmail
        });
        
        if (!isLogging) {
            processLogQueue();
        }
    }

    function processLogQueue() {
        if (logQueue.length === 0) {
            isLogging = false;
            return;
        }
        
        isLogging = true;
        const item = logQueue.shift();
        
        const csrfToken = getCSRFToken();
        
        if (!csrfToken) {
            console.warn('⚠️ CSRF token not found');
            setTimeout(processLogQueue, 100);
            return;
        }
        
        const payload = {
            violation_type: item.type,
            description: item.description,
            timestamp: item.timestamp,
            page_url: window.location.href,
            user_agent: navigator.userAgent
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
            console.warn('⚠️ Logging failed');
        })
        .finally(() => {
            setTimeout(processLogQueue, 100);
        });
    }

    // ============================================================================
    // CSS INJECTION
    // ============================================================================
    
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            body, * {
                -webkit-user-select: none !important;
                -moz-user-select: none !important;
                user-select: none !important;
            }

            input, textarea, select, button, a,
            .customer-sidebar, .nav-link {
                -webkit-user-select: text !important;
                -moz-user-select: text !important;
                user-select: text !important;
            }

            img, video, canvas {
                -webkit-user-drag: none !important;
                user-drag: none !important;
                pointer-events: none !important;
            }

            button, a, input, textarea, select {
                pointer-events: auto !important;
            }

            video::-webkit-media-controls {
                display: none !important;
            }

            ::selection {
                background: transparent !important;
            }
            
            .security-watermark {
                pointer-events: none !important;
                user-select: none !important;
                -webkit-user-select: none !important;
            }
        `;
        document.head.appendChild(style);
    }

    // ============================================================================
    // DEVTOOLS DETECTION
    // ============================================================================
    
    function detectDevTools() {
        setInterval(function() {
            const widthThreshold = window.outerWidth - window.innerWidth > 200;
            const heightThreshold = window.outerHeight - window.innerHeight > 200;
            
            if (widthThreshold || heightThreshold) {
                logViolation('devtools_open', 'DevTools may be open');
                
                if (CONFIG.enableAggressiveBlocking) {
                    showBlackScreen('Developer tools detected');
                }
            }
        }, 5000);
    }

    // ============================================================================
    // INITIALIZATION
    // ============================================================================
    
    function initialize() {
        console.log('%c🔒 MAXIMUM PROTECTION ACTIVE', 
            'color: #ef4444; font-size: 18px; font-weight: bold;');
        
        injectStyles();
        createWatermark();
        detectScreenshot();
        detectScreenRecording();
        protectKeyboard();
        protectSelection();
        detectDevTools();
        
        console.log('✅ All protection systems initialized with watermark');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    window.addEventListener('pageshow', function(event) {
        if (event.persisted) {
            initialize();
        }
    });

})();