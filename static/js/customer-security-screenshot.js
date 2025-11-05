// static/js/customer-security-screenshot.js
/**
 * Screenshot Detection & Prevention (NO WATERMARK)
 */

(function() {
    'use strict';

    console.log('🔒 Screenshot Protection Loading...');

    // ==========================================
    // SCREENSHOT DETECTION
    // ==========================================

    // Detect PrintScreen key
    document.addEventListener('keyup', function(e) {
        if (e.key === 'PrintScreen' || e.keyCode === 44) {
            navigator.clipboard.writeText('');
            
            if (window.CustomerSecurity) {
                window.CustomerSecurity.incrementViolation('screenshot_attempt');
            }
            
            showScreenshotWarning();
        }
    });

    // Detect screenshot shortcuts
    document.addEventListener('keydown', function(e) {
        // Windows: Win+Shift+S, Win+PrtScn
        if ((e.key === 'Meta' || e.metaKey) && e.shiftKey && e.keyCode === 83) {
            e.preventDefault();
            if (window.CustomerSecurity) {
                window.CustomerSecurity.incrementViolation('snipping_tool');
            }
            showScreenshotWarning();
            return false;
        }

        // Mac: Cmd+Shift+3, Cmd+Shift+4, Cmd+Shift+5
        if (e.metaKey && e.shiftKey && [51, 52, 53, 54].includes(e.keyCode)) {
            e.preventDefault();
            if (window.CustomerSecurity) {
                window.CustomerSecurity.incrementViolation('mac_screenshot');
            }
            showScreenshotWarning();
            return false;
        }

        // PrintScreen
        if (e.keyCode === 44 || e.key === 'PrintScreen') {
            e.preventDefault();
            navigator.clipboard.writeText('');
            if (window.CustomerSecurity) {
                window.CustomerSecurity.incrementViolation('printscreen');
            }
            return false;
        }
    });

    // ==========================================
    // SCREENSHOT WARNING
    // ==========================================

    function showScreenshotWarning() {
        const existing = document.getElementById('screenshot-warning');
        if (existing) return;

        const warning = document.createElement('div');
        warning.id = 'screenshot-warning';
        warning.innerHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 100000; display: flex; justify-content: center; align-items: center; animation: fadeIn 0.3s;">
                <div style="background: linear-gradient(135deg, #f44336, #e91e63); color: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.5); text-align: center; max-width: 500px; animation: scaleIn 0.3s;">
                    <div style="font-size: 80px; margin-bottom: 20px; animation: shake 0.5s;">⚠️</div>
                    <h2 style="margin: 0 0 15px 0; font-size: 28px;">Screenshot Detected!</h2>
                    <p style="margin: 0 0 20px 0; font-size: 16px; opacity: 0.95;">Screenshots and screen recordings are strictly prohibited for security purposes.</p>
                    <p style="margin: 0 0 25px 0; font-size: 14px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                        ⚡ This violation has been logged and reported.
                    </p>
                    <button onclick="this.closest('#screenshot-warning').remove();" style="background: white; color: #f44336; border: none; padding: 12px 30px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 16px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                        I Understand
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(warning);

        // Auto remove after 8 seconds
        setTimeout(() => {
            const el = document.getElementById('screenshot-warning');
            if (el) el.remove();
        }, 8000);
    }

    // ==========================================
    // DEVTOOLS DETECTION
    // ==========================================

    let devtoolsOpen = false;
    const threshold = 160;

    function detectDevTools() {
        const widthDiff = window.outerWidth - window.innerWidth;
        const heightDiff = window.outerHeight - window.innerHeight;

        if (widthDiff > threshold || heightDiff > threshold) {
            if (!devtoolsOpen) {
                devtoolsOpen = true;
                if (window.CustomerSecurity) {
                    window.CustomerSecurity.logEvent('devtools_opened');
                    window.CustomerSecurity.incrementViolation('devtools');
                }
                showDevToolsWarning();
            }
        } else {
            devtoolsOpen = false;
        }
    }

    function showDevToolsWarning() {
        const existing = document.getElementById('devtools-warning');
        if (existing) return;

        const warning = document.createElement('div');
        warning.id = 'devtools-warning';
        warning.innerHTML = `
            <div style="position: fixed; bottom: 20px; right: 20px; background: linear-gradient(135deg, #ff9800, #f44336); color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 10001; max-width: 320px; animation: slideIn 0.3s;">
                <h4 style="margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 24px;">⚡</span>
                    Developer Tools Detected
                </h4>
                <p style="margin: 0; font-size: 14px; opacity: 0.95;">For security reasons, please close developer tools immediately.</p>
            </div>
        `;
        document.body.appendChild(warning);

        setTimeout(() => {
            const el = document.getElementById('devtools-warning');
            if (el) el.remove();
        }, 5000);
    }

    // Check devtools every 500ms
    setInterval(detectDevTools, 500);

    // ==========================================
    // ADVANCED DETECTION
    // ==========================================

    // Detect debugger
    (function detectDebugger() {
        function check() {
            const start = performance.now();
            debugger; // eslint-disable-line no-debugger
            const end = performance.now();
            
            if (end - start > 100) {
                if (window.CustomerSecurity) {
                    window.CustomerSecurity.blurScreen('debugger_detected');
                }
            }
        }
        
        setInterval(check, 5000);
    })();

    // ==========================================
    // INITIALIZE
    // ==========================================

    function initialize() {
        // Add CSS animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            @keyframes scaleIn {
                from { transform: scale(0.8); opacity: 0; }
                to { transform: scale(1); opacity: 1; }
            }
            @keyframes shake {
                0%, 100% { transform: rotate(0deg); }
                25% { transform: rotate(-5deg); }
                75% { transform: rotate(5deg); }
            }
            @keyframes slideIn {
                from { transform: translateX(400px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);

        console.log('✅ Screenshot Protection Active (No Watermark)');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

})();