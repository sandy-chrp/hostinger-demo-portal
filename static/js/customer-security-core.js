// static/js/customer-security-core.js
/**
 * Customer Portal Security System
 * Banking-level protection WITHOUT watermark
 */

(function() {
    'use strict';

    console.log('🔒 Customer Security System Loading...');

    // ==========================================
    // SECURITY CONFIGURATION
    // ==========================================
    window.CustomerSecurity = {
        config: {
            sessionTimeout: 15 * 60 * 1000,    // 15 minutes
            idleTimeout: 5 * 60 * 1000,        // 5 minutes
            warningTime: 2 * 60 * 1000,        // 2 minutes warning
            logEndpoint: '/customers/api/security-log/',
            maxViolations: 5,
            enableWatermark: false,            // ❌ Watermark DISABLED
            enableScreenBlur: true,            // ✅ Screen blur ENABLED
            blurIntensity: '10px'
        },

        state: {
            violations: 0,
            lastActivity: Date.now(),
            sessionStart: Date.now(),
            warningShown: false,
            isBlurred: false,
            suspiciousActivity: false
        }
    };

    // ==========================================
    // UTILITY FUNCTIONS
    // ==========================================
    
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

    function logSecurityEvent(eventType, details = {}) {
        const csrfToken = getCookie('csrftoken');
        
        fetch(CustomerSecurity.config.logEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                event_type: eventType,
                details: details,
                timestamp: new Date().toISOString(),
                url: window.location.href,
                user_agent: navigator.userAgent
            })
        }).catch(err => console.error('Security log failed:', err));
    }

    // ==========================================
    // SCREEN BLUR PROTECTION
    // ==========================================

    function blurScreen(reason) {
        if (CustomerSecurity.state.isBlurred) return;

        CustomerSecurity.state.isBlurred = true;
        logSecurityEvent('screen_blurred', { reason: reason });

        // Blur main content
        const mainContent = document.querySelector('main') || document.body;
        mainContent.style.filter = `blur(${CustomerSecurity.config.blurIntensity})`;
        mainContent.style.transition = 'filter 0.3s ease';
        
        // Show blur overlay
        const overlay = document.createElement('div');
        overlay.id = 'blur-overlay';
        overlay.innerHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 99999; display: flex; justify-content: center; align-items: center; color: white; font-family: Arial, sans-serif;">
                <div style="text-align: center; padding: 40px; background: rgba(255,255,255,0.1); border-radius: 12px; backdrop-filter: blur(10px);">
                    <div style="font-size: 64px; margin-bottom: 20px;">⚠️</div>
                    <h2 style="margin: 0 0 15px 0;">Suspicious Activity Detected</h2>
                    <p style="margin: 0 0 20px 0; opacity: 0.9;">Screen recording or unauthorized tool detected.</p>
                    <p style="margin: 0 0 25px 0; font-size: 14px;">Your session has been protected.</p>
                    <button onclick="window.location.href='/accounts/signin/'" style="background: #f44336; color: white; border: none; padding: 12px 30px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 16px;">Return to Login</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    function unblurScreen() {
        CustomerSecurity.state.isBlurred = false;
        
        const mainContent = document.querySelector('main') || document.body;
        mainContent.style.filter = 'none';
        
        const overlay = document.getElementById('blur-overlay');
        if (overlay) overlay.remove();
    }

    // ==========================================
    // EXTENSION/TOOL DETECTION
    // ==========================================

    function detectScreenRecordingTools() {
        // Check for common screen recording extensions
        const suspiciousExtensions = [
            'chrome-extension://',
            'moz-extension://',
            'loom', 'screencastify', 'awesome screenshot',
            'nimbus', 'fireshot', 'lightshot'
        ];

        // Check document title for recording indicators
        const titleLower = document.title.toLowerCase();
        for (let ext of suspiciousExtensions) {
            if (titleLower.includes(ext)) {
                CustomerSecurity.state.suspiciousActivity = true;
                blurScreen('recording_tool_detected');
                return true;
            }
        }

        // Check for canvas fingerprinting (used by some extensions)
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl');
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                if (renderer.includes('SwiftShader') || renderer.includes('llvmpipe')) {
                    // Virtual rendering detected (possible VM or screen capture tool)
                    CustomerSecurity.state.suspiciousActivity = true;
                    blurScreen('virtual_renderer_detected');
                    return true;
                }
            }
        } catch (e) {
            // Canvas access blocked or error
        }

        return false;
    }

    // Monitor for extension injection
    function detectExtensionInjection() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        const attrs = node.attributes;
                        if (attrs) {
                            for (let i = 0; i < attrs.length; i++) {
                                const attrValue = attrs[i].value.toLowerCase();
                                if (attrValue.includes('extension://') || 
                                    attrValue.includes('chrome-extension://') ||
                                    attrValue.includes('moz-extension://')) {
                                    CustomerSecurity.state.suspiciousActivity = true;
                                    blurScreen('extension_injection_detected');
                                    observer.disconnect();
                                    return;
                                }
                            }
                        }
                    }
                });
            });
        });

        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['src', 'href', 'data-src']
        });
    }

    // ==========================================
    // VIOLATION HANDLING
    // ==========================================

    function incrementViolation(type) {
        CustomerSecurity.state.violations++;
        logSecurityEvent('security_violation', { 
            type: type, 
            count: CustomerSecurity.state.violations 
        });

        if (CustomerSecurity.state.violations >= CustomerSecurity.config.maxViolations) {
            showSecurityBlock();
        } else if (CustomerSecurity.state.violations >= 3) {
            // Show warning after 3 violations
            showViolationWarning(CustomerSecurity.state.violations);
        }
    }

    function showViolationWarning(count) {
        const existing = document.getElementById('violation-warning');
        if (existing) existing.remove();

        const warning = document.createElement('div');
        warning.id = 'violation-warning';
        warning.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; background: linear-gradient(135deg, #f44336, #e91e63); color: white; padding: 20px; border-radius: 8px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); z-index: 10000; max-width: 350px; animation: shake 0.5s;">
                <h4 style="margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 24px;">⚠️</span>
                    Security Warning
                </h4>
                <p style="margin: 0 0 10px 0; font-size: 14px;">
                    <strong>${count}</strong> security violations detected.
                </p>
                <p style="margin: 0; font-size: 12px; opacity: 0.9;">
                    After ${CustomerSecurity.config.maxViolations} violations, your session will be terminated.
                </p>
            </div>
        `;
        document.body.appendChild(warning);

        setTimeout(() => warning.remove(), 5000);
    }

    function showSecurityBlock() {
        logSecurityEvent('session_terminated', { reason: 'max_violations' });
        
        document.body.innerHTML = `
            <div style="display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-family: Arial, sans-serif; text-align: center; padding: 20px;">
                <div style="background: rgba(255,255,255,0.1); padding: 60px 40px; border-radius: 16px; backdrop-filter: blur(10px); box-shadow: 0 8px 32px rgba(0,0,0,0.3); max-width: 500px;">
                    <div style="font-size: 80px; margin-bottom: 20px;">🚫</div>
                    <h1 style="margin: 0 0 20px 0; font-size: 32px;">Session Terminated</h1>
                    <p style="margin: 0 0 15px 0; font-size: 18px; opacity: 0.9;">Multiple security violations detected</p>
                    <p style="margin: 0 0 30px 0; font-size: 14px; opacity: 0.8;">Your account has been flagged for review.</p>
                    <a href="/accounts/signin/" style="display: inline-block; padding: 15px 40px; background: white; color: #667eea; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; transition: transform 0.2s;">Return to Login</a>
                </div>
            </div>
        `;
    }

    // ==========================================
    // SESSION MANAGEMENT
    // ==========================================
    
    function updateActivity() {
        CustomerSecurity.state.lastActivity = Date.now();
        CustomerSecurity.state.warningShown = false;
    }

    function checkSession() {
        const now = Date.now();
        const idleTime = now - CustomerSecurity.state.lastActivity;
        const sessionTime = now - CustomerSecurity.state.sessionStart;

        // Check idle timeout
        if (idleTime > CustomerSecurity.config.idleTimeout) {
            logSecurityEvent('session_timeout', { reason: 'idle' });
            window.location.href = '/accounts/signin/?timeout=idle';
            return;
        }

        // Check max session time
        if (sessionTime > CustomerSecurity.config.sessionTimeout) {
            logSecurityEvent('session_timeout', { reason: 'max_duration' });
            window.location.href = '/accounts/signin/?timeout=expired';
            return;
        }

        // Show warning before timeout
        if (idleTime > (CustomerSecurity.config.idleTimeout - CustomerSecurity.config.warningTime) && !CustomerSecurity.state.warningShown) {
            showTimeoutWarning();
            CustomerSecurity.state.warningShown = true;
        }
    }

    function showTimeoutWarning() {
        const warning = document.createElement('div');
        warning.id = 'timeout-warning';
        warning.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; background: linear-gradient(135deg, #ff9800, #ff5722); color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 10000; max-width: 300px; animation: slideIn 0.3s;">
                <h4 style="margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 24px;">⏰</span>
                    Session Expiring
                </h4>
                <p style="margin: 0 0 15px 0; font-size: 14px;">Your session will expire in 2 minutes due to inactivity.</p>
                <button onclick="this.parentElement.parentElement.remove(); window.CustomerSecurity.updateActivity();" style="background: white; color: #ff9800; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; width: 100%;">I'm Still Here</button>
            </div>
        `;
        document.body.appendChild(warning);

        // Auto redirect if not dismissed
        setTimeout(() => {
            const warningEl = document.getElementById('timeout-warning');
            if (warningEl) {
                window.location.href = '/accounts/signin/?timeout=idle';
            }
        }, CustomerSecurity.config.warningTime);
    }

    // ==========================================
    // INITIALIZE
    // ==========================================
    
    function initialize() {
        console.log('✅ Customer Security System Active');

        // Check for recording tools on load
        detectScreenRecordingTools();
        
        // Monitor for extension injection
        detectExtensionInjection();

        // Periodic checks for suspicious tools
        setInterval(detectScreenRecordingTools, 5000);

        // Monitor user activity
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'].forEach(event => {
            document.addEventListener(event, updateActivity, { passive: true });
        });

        // Check session every second
        setInterval(checkSession, 1000);

        // Monitor tab visibility
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                logSecurityEvent('tab_hidden', { timestamp: new Date().toISOString() });
            } else {
                updateActivity();
            }
        });

        // Detect multiple tabs
        const tabId = 'tab_' + Date.now() + '_' + Math.random();
        sessionStorage.setItem('tabId', tabId);
        
        window.addEventListener('storage', function(e) {
            if (e.key === 'tabId' && e.newValue !== tabId) {
                logSecurityEvent('multiple_tabs_detected');
            }
        });

        // Log session start
        logSecurityEvent('session_started', { 
            screen: { width: screen.width, height: screen.height },
            browser: navigator.userAgent,
            tabId: tabId
        });

        // Add CSS animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(400px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                20%, 40%, 60%, 80% { transform: translateX(5px); }
            }
        `;
        document.head.appendChild(style);
    }

    // Expose functions globally
    window.CustomerSecurity.updateActivity = updateActivity;
    window.CustomerSecurity.logEvent = logSecurityEvent;
    window.CustomerSecurity.incrementViolation = incrementViolation;
    window.CustomerSecurity.blurScreen = blurScreen;
    window.CustomerSecurity.unblurScreen = unblurScreen;

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

})();