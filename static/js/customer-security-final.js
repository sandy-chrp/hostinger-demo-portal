// static/js/customer-security-final.js
/**
 * Complete Banking-Level Security System
 * Uses existing backend endpoints
 */

(function() {
    'use strict';

    console.log('🔒 Banking Security System Loading...');

    // ==========================================
    // CONFIGURATION
    // ==========================================
    window.BankingSecurity = {
        config: {
            violationEndpoint: '/customers/ajax/log-security-violation/',
            maxViolations: 3,
            sessionTimeout: 15 * 60 * 1000,    // 15 minutes
            idleTimeout: 5 * 60 * 1000,        // 5 minutes
            warningTime: 2 * 60 * 1000,        // 2 minutes warning
            enableBlur: true,
            redirectUrl: '/auth/signin/'
        },

        state: {
            violations: 0,
            lastActivity: Date.now(),
            sessionStart: Date.now(),
            isBlurred: false,
            warningShown: false,
            devToolsOpen: false
        }
    };

    // ==========================================
    // UTILITY FUNCTIONS
    // ==========================================
    
    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
               getCookie('csrftoken');
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function logViolation(violationType, description = '') {
        console.log(`🚨 Security Violation: ${violationType}`);
        
        const data = {
            violation_type: violationType,
            description: description,
            page_url: window.location.href,
            timestamp: new Date().toISOString()
        };

        // Using existing endpoint from your URLs
        fetch(BankingSecurity.config.violationEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                BankingSecurity.state.violations++;
                console.log(`✅ Violation logged: ${data.violation_id}`);
                
                if (BankingSecurity.state.violations >= BankingSecurity.config.maxViolations) {
                    terminateSession();
                }
            }
        })
        .catch(err => console.error('Violation logging failed:', err));
    }

    function terminateSession() {
        console.log('🚫 Session Terminated');
        
        document.body.innerHTML = `
            <div style="display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-family: Arial, sans-serif; text-align: center; padding: 20px;">
                <div style="background: rgba(255,255,255,0.1); padding: 60px 40px; border-radius: 16px; backdrop-filter: blur(10px); box-shadow: 0 8px 32px rgba(0,0,0,0.3); max-width: 500px;">
                    <div style="font-size: 80px; margin-bottom: 20px;">🚫</div>
                    <h1 style="margin: 0 0 20px 0; font-size: 32px;">Session Terminated</h1>
                    <p style="margin: 0 0 15px 0; font-size: 18px; opacity: 0.9;">Multiple security violations detected</p>
                    <p style="margin: 0 0 30px 0; font-size: 14px; opacity: 0.8;">Please contact support if you believe this is an error.</p>
                    <a href="${BankingSecurity.config.redirectUrl}" style="display: inline-block; padding: 15px 40px; background: white; color: #667eea; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Return to Login</a>
                </div>
            </div>
        `;
    }

    function blurScreen(reason) {
        if (BankingSecurity.state.isBlurred) return;

        BankingSecurity.state.isBlurred = true;
        logViolation('screen_recording', `Screen blurred: ${reason}`);

        const mainContent = document.querySelector('main') || document.body;
        mainContent.style.filter = 'blur(10px)';
        mainContent.style.transition = 'filter 0.3s ease';
        
        showBlurOverlay(reason);
    }

    function showBlurOverlay(reason) {
        const overlay = document.createElement('div');
        overlay.id = 'blur-overlay';
        overlay.innerHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 99999; display: flex; justify-content: center; align-items: center; color: white; font-family: Arial, sans-serif;">
                <div style="text-align: center; padding: 40px; background: rgba(255,255,255,0.1); border-radius: 12px; backdrop-filter: blur(10px);">
                    <div style="font-size: 64px; margin-bottom: 20px;">⚠️</div>
                    <h2 style="margin: 0 0 15px 0;">Suspicious Activity Detected</h2>
                    <p style="margin: 0 0 20px 0; opacity: 0.9;">${reason}</p>
                    <p style="margin: 0 0 25px 0; font-size: 14px;">Your session has been protected for security.</p>
                    <button onclick="window.location.href='${BankingSecurity.config.redirectUrl}'" style="background: #f44336; color: white; border: none; padding: 12px 30px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 16px;">Return to Login</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    // ==========================================
    // SCREENSHOT PROTECTION
    // ==========================================

    // Enhanced screenshot detection
    document.addEventListener('keydown', function(e) {
        let blocked = false;
        let violationType = '';

        // PrintScreen
        if (e.keyCode === 44 || e.key === 'PrintScreen') {
            blocked = true;
            violationType = 'screenshot_attempt';
        }

        // Windows: Win + Shift + S (Snip & Sketch)
        if (e.key === 'Meta' && e.shiftKey && e.keyCode === 83) {
            blocked = true;
            violationType = 'screenshot_tool_detected';
        }

        // Windows: Alt + PrintScreen
        if (e.altKey && (e.keyCode === 44 || e.key === 'PrintScreen')) {
            blocked = true;
            violationType = 'screenshot_attempt';
        }

        // Mac: Cmd + Shift + 3, 4, 5, 6
        if (e.metaKey && e.shiftKey && [51, 52, 53, 54].includes(e.keyCode)) {
            blocked = true;
            violationType = 'screenshot_attempt';
        }

        // Copy shortcuts
        if ((e.ctrlKey || e.metaKey) && [67, 88, 86, 65].includes(e.keyCode)) {
            blocked = true;
            violationType = 'copy_attempt';
        }

        // Developer tools
        if (e.keyCode === 123 || 
            (e.ctrlKey && e.shiftKey && [73, 74].includes(e.keyCode)) ||
            (e.ctrlKey && e.keyCode === 85)) {
            blocked = true;
            violationType = 'devtools_detected';
        }

        if (blocked) {
            e.preventDefault();
            e.stopPropagation();
            logViolation(violationType, `Key combination: ${e.key || e.keyCode}`);
            showViolationAlert(violationType);
            return false;
        }
    }, true);

    // Clear clipboard on PrintScreen
    document.addEventListener('keyup', function(e) {
        if (e.key === 'PrintScreen' || e.keyCode === 44) {
            navigator.clipboard.writeText('').catch(() => {});
        }
    });

    // ==========================================
    // COPY/PASTE PROTECTION
    // ==========================================

    ['copy', 'cut'].forEach(event => {
        document.addEventListener(event, function(e) {
            e.preventDefault();
            e.stopPropagation();
            e.clipboardData?.setData('text/plain', 'Content copying is disabled for security.');
            logViolation('copy_attempt', `${event} event`);
            showViolationAlert('copy_attempt');
            return false;
        }, true);
    });

    document.addEventListener('paste', function(e) {
        if (!e.target.classList.contains('allow-paste')) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    }, true);

    // Disable right-click
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        logViolation('right_click_attempt', 'Context menu blocked');
        return false;
    }, true);

    // Disable text selection
    document.addEventListener('selectstart', function(e) {
        if (!e.target.classList.contains('allow-select')) {
            e.preventDefault();
            return false;
        }
    }, true);

    // Disable drag
    document.addEventListener('dragstart', function(e) {
        e.preventDefault();
        logViolation('drag_attempt', 'Drag operation blocked');
        return false;
    }, true);

    // ==========================================
    // DEVTOOLS DETECTION
    // ==========================================

    function detectDevTools() {
        const widthDiff = window.outerWidth - window.innerWidth;
        const heightDiff = window.outerHeight - window.innerHeight;
        const threshold = 160;

        if (widthDiff > threshold || heightDiff > threshold) {
            if (!BankingSecurity.state.devToolsOpen) {
                BankingSecurity.state.devToolsOpen = true;
                logViolation('devtools_detected', 'Developer tools opened');
                blurScreen('Developer tools detected');
            }
        } else {
            BankingSecurity.state.devToolsOpen = false;
        }
    }

    // Check every 500ms
    setInterval(detectDevTools, 500);

    // Debugger detection
    setInterval(function() {
        const start = performance.now();
        debugger; // eslint-disable-line no-debugger
        const end = performance.now();
        
        if (end - start > 100) {
            logViolation('devtools_detected', 'Debugger statement executed');
            blurScreen('Debugger detected');
        }
    }, 3000);

    // ==========================================
    // EXTENSION/TOOL DETECTION
    // ==========================================

    function detectScreenRecordingTools() {
        // Check for recording software keywords
        const userAgent = navigator.userAgent.toLowerCase();
        const suspiciousKeywords = [
            'obs', 'streamlabs', 'xsplit', 'bandicam', 'camtasia', 
            'fraps', 'screencastify', 'loom', 'quicktime'
        ];

        for (let keyword of suspiciousKeywords) {
            if (userAgent.includes(keyword)) {
                logViolation('screen_recording', `Recording software detected: ${keyword}`);
                blurScreen(`Recording software detected: ${keyword}`);
                return;
            }
        }

        // Check for canvas fingerprinting (extensions use this)
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl');
            if (gl) {
                const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                if (debugInfo) {
                    const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                    if (renderer.includes('SwiftShader') || renderer.includes('llvmpipe')) {
                        logViolation('screen_recording', 'Virtual renderer detected');
                        blurScreen('Virtual rendering environment detected');
                    }
                }
            }
        } catch (e) {
            // Canvas blocked
        }
    }

    // Check every 10 seconds
    setInterval(detectScreenRecordingTools, 10000);

    // ==========================================
    // SESSION MANAGEMENT
    // ==========================================

    function updateActivity() {
        BankingSecurity.state.lastActivity = Date.now();
        BankingSecurity.state.warningShown = false;
    }

    function checkSession() {
        const now = Date.now();
        const idleTime = now - BankingSecurity.state.lastActivity;
        const sessionTime = now - BankingSecurity.state.sessionStart;

        // Check idle timeout
        if (idleTime > BankingSecurity.config.idleTimeout) {
            window.location.href = `${BankingSecurity.config.redirectUrl}?timeout=idle`;
            return;
        }

        // Check max session time
        if (sessionTime > BankingSecurity.config.sessionTimeout) {
            window.location.href = `${BankingSecurity.config.redirectUrl}?timeout=expired`;
            return;
        }

        // Show warning
        if (idleTime > (BankingSecurity.config.idleTimeout - BankingSecurity.config.warningTime) && !BankingSecurity.state.warningShown) {
            showTimeoutWarning();
            BankingSecurity.state.warningShown = true;
        }
    }

    function showTimeoutWarning() {
        const warning = document.createElement('div');
        warning.id = 'timeout-warning';
        warning.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; background: linear-gradient(135deg, #ff9800, #ff5722); color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 10000; max-width: 300px; animation: slideIn 0.3s;">
                <h4 style="margin: 0 0 10px 0;">⏰ Session Expiring</h4>
                <p style="margin: 0 0 15px 0; font-size: 14px;">Your session will expire in 2 minutes.</p>
                <button onclick="this.parentElement.parentElement.remove(); window.BankingSecurity.updateActivity();" style="background: white; color: #ff9800; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%;">I'm Still Here</button>
            </div>
        `;
        document.body.appendChild(warning);
    }

    // ==========================================
    // VIOLATION ALERTS
    // ==========================================

    function showViolationAlert(type) {
        const messages = {
            'screenshot_attempt': 'Screenshots are not allowed',
            'copy_attempt': 'Content copying is disabled',
            'devtools_detected': 'Developer tools are not permitted',
            'right_click_attempt': 'Right-click is disabled',
            'drag_attempt': 'Drag & drop is not allowed'
        };

        const message = messages[type] || 'Security violation detected';
        
        const alert = document.createElement('div');
        alert.className = 'security-alert';
        alert.innerHTML = `
            <div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #f44336; color: white; padding: 15px 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 10001; animation: shake 0.5s;">
                <strong>⚠️ ${message}</strong>
            </div>
        `;
        document.body.appendChild(alert);

        setTimeout(() => alert.remove(), 3000);
    }

    // ==========================================
    // INITIALIZE
    // ==========================================

    function initialize() {
        console.log('✅ Banking Security System Active');

        // Monitor user activity
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'].forEach(event => {
            document.addEventListener(event, updateActivity, { passive: true });
        });

        // Check session every second
        setInterval(checkSession, 1000);

        // Monitor tab visibility
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                logViolation('suspicious_activity', 'Tab hidden during session');
            } else {
                updateActivity();
            }
        });

        // Initial tool detection
        detectScreenRecordingTools();

        // Add CSS animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(400px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes shake {
                0%, 100% { transform: translateX(-50%); }
                25% { transform: translateX(-52%); }
                75% { transform: translateX(-48%); }
            }
        `;
        document.head.appendChild(style);

        // Expose functions globally
        window.BankingSecurity.updateActivity = updateActivity;
        window.BankingSecurity.logViolation = logViolation;
        window.BankingSecurity.blurScreen = blurScreen;
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

})();