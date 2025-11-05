
(function() {
    'use strict';
    console.log('🔒 ULTIMATE Security System Loading...');

    // ============================================
    // 1. BLOCK ALL SCREENSHOT SHORTCUTS
    // ============================================
    document.addEventListener('keydown', function(e) {
        let blocked = false;
        let message = '';
        
        // F12 - Developer Tools
        if (e.keyCode === 123) {
            blocked = true;
            message = '🚫 Developer Tools Blocked!';
        }
        
        // Ctrl+Shift+I - Developer Tools
        if (e.ctrlKey && e.shiftKey && e.keyCode === 73) {
            blocked = true;
            message = '🚫 Developer Tools Blocked!';
        }
        
        // Ctrl+Shift+J - Console
        if (e.ctrlKey && e.shiftKey && e.keyCode === 74) {
            blocked = true;
            message = '🚫 Console Blocked!';
        }
        
        // Ctrl+Shift+C - Inspect Element
        if (e.ctrlKey && e.shiftKey && e.keyCode === 67) {
            blocked = true;
            message = '🚫 Inspect Element Blocked!';
        }
        
        // Ctrl+U - View Source
        if (e.ctrlKey && e.keyCode === 85) {
            blocked = true;
            message = '🚫 View Source Blocked!';
        }
        
        // PrintScreen (PrtScn)
        if (e.keyCode === 44 || e.key === 'PrintScreen') {
            blocked = true;
            message = '🚫 Screenshot Blocked!';
            blurScreen();
            sendSecurityViolation('screenshot', 'PrintScreen key pressed');
        }
        
        // Windows Snipping Tool - Win + Shift + S
        if (e.metaKey && e.shiftKey && e.keyCode === 83) {
            blocked = true;
            message = '🚫 Snipping Tool Blocked!';
            blurScreen();
            sendSecurityViolation('screenshot', 'Snipping Tool attempt');
        }
        
        // Mac Screenshots - Cmd + Shift + 3/4/5/6
        if (e.metaKey && e.shiftKey && [51, 52, 53, 54].includes(e.keyCode)) {
            blocked = true;
            message = '🚫 Screenshot Blocked!';
            blurScreen();
            sendSecurityViolation('screenshot', 'Mac screenshot shortcut pressed');
        }
        
        // Alt + PrintScreen (Active Window Screenshot)
        if (e.altKey && (e.keyCode === 44 || e.key === 'PrintScreen')) {
            blocked = true;
            message = '🚫 Screenshot Blocked!';
            blurScreen();
            sendSecurityViolation('screenshot', 'Alt+PrintScreen pressed');
        }
        
        if (blocked) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            showBlockedAlert(message);
            console.log('🚫 Blocked:', message);
            return false;
        }
    }, true);

    // ============================================
    // 2. BLOCK RIGHT-CLICK COMPLETELY
    // ============================================
// ============================================
// 2. BLOCK RIGHT-CLICK (Smart - Allow on Links/Buttons)
// ============================================
document.addEventListener('contextmenu', function(e) {
    // Allow right-click on these elements
    if (e.target.tagName === 'INPUT' || 
        e.target.tagName === 'TEXTAREA' || 
        e.target.tagName === 'SELECT' ||
        e.target.tagName === 'BUTTON' ||
        e.target.tagName === 'A' ||
        e.target.closest('a') ||
        e.target.closest('button') ||
        e.target.closest('.nav-link')) {
        return true; // Allow
    }
    
    // Block on content
    e.preventDefault();
    e.stopPropagation();
    showBlockedAlert('🚫 Right-click Blocked!');
    sendSecurityViolation('right_click', 'Right-click attempted');
    return false;
}, true);

    // ============================================
    // 3. BLOCK COPY/CUT/PASTE (except inputs)
    // ============================================
    ['copy', 'cut', 'paste'].forEach(function(eventType) {
        document.addEventListener(eventType, function(e) {
            if (e.target.tagName === 'INPUT' || 
                e.target.tagName === 'TEXTAREA') {
                return true;
            }
            e.preventDefault();
            e.stopPropagation();
            showBlockedAlert(`🚫 ${eventType.toUpperCase()} Blocked!`);
            sendSecurityViolation(eventType, `${eventType} attempted on content`);
            return false;
        }, true);
    });

    // ============================================
    // 4. DISABLE TEXT SELECTION (except inputs)
    // ============================================
    document.addEventListener('selectstart', function(e) {
        if (e.target.tagName === 'INPUT' || 
            e.target.tagName === 'TEXTAREA') {
            return true;
        }
        e.preventDefault();
        return false;
    }, true);

    // Add CSS to prevent text selection
    const style = document.createElement('style');
    style.textContent = `
        body, div, p, span, h1, h2, h3, h4, h5, h6, a, li, td, th {
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            user-select: none !important;
        }
        input, textarea, select {
            -webkit-user-select: text !important;
            -moz-user-select: text !important;
            -ms-user-select: text !important;
            user-select: text !important;
        }
    `;
    document.head.appendChild(style);

    // ============================================
    // 5. TAB/WINDOW VISIBILITY DETECTION
    // ============================================
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            sendSecurityViolation('focus_lost', 'User switched tab or minimized window');
            setTimeout(function() {
                showVisibilityWarning();
            }, 100);
        }
    });

    // Detect window blur (user switched to another app)
    window.addEventListener('blur', function() {
        sendSecurityViolation('window_blur', 'User switched to another application');
    });

    // ============================================
    // 6. DEVTOOLS DETECTION (Advanced)
    // ============================================
    let devtoolsOpen = false;
    const threshold = 160;
    
    setInterval(function() {
        if (window.outerWidth - window.innerWidth > threshold || 
            window.outerHeight - window.innerHeight > threshold) {
            if (!devtoolsOpen) {
                devtoolsOpen = true;
                sendSecurityViolation('devtools_opened', 'Developer tools detected as open');
                showBlockedAlert('🚫 Developer Tools Detected! Closing recommended.');
            }
        } else {
            devtoolsOpen = false;
        }
    }, 1000);

    // ============================================
    // 7. SCREEN BLUR FUNCTION (on screenshot attempt)
    // ============================================
    function blurScreen() {
        document.body.style.filter = 'blur(25px) brightness(0.5)';
        document.body.style.transition = 'filter 0.1s';
        
        let overlay = document.createElement('div');
        overlay.id = 'screenshot-block-overlay';
        overlay.style = 'position:fixed;top:0;left:0;width:100vw;height:100vh;'+
            'background:rgba(0,0,0,0.9);color:#fff;'+
            'display:flex;align-items:center;justify-content:center;'+
            'font-size:2rem;z-index:999999;text-align:center;'+
            'font-weight:bold;';
        overlay.innerHTML = `
            <div>
                <i class="fas fa-exclamation-triangle" style="font-size:4rem;color:#ff4444;margin-bottom:20px;"></i>
                <br>
                🚫 SCREENSHOT ATTEMPT DETECTED!
                <br><br>
                <span style="font-size:1.2rem;color:#ffaaaa;">
                All activity is monitored and logged.<br>
                This action has been reported.
                </span>
            </div>
        `;
        document.body.appendChild(overlay);
        
        // Auto remove after 3 seconds
        setTimeout(function() {
            document.body.style.filter = '';
            let el = document.getElementById('screenshot-block-overlay');
            if (el) el.remove();
        }, 3000);
    }

    // ============================================
    // 8. BLOCKED ACTION ALERT
    // ============================================
    function showBlockedAlert(message) {
        let existing = document.getElementById('security-block-alert');
        if (existing) existing.remove();
        
        let alert = document.createElement('div');
        alert.id = 'security-block-alert';
        alert.style = 'position:fixed;top:20%;left:50%;transform:translate(-50%,-50%);'+
            'background:rgba(220,0,0,0.95);color:#fff;padding:25px 40px;'+
            'border-radius:15px;font-size:1.3rem;z-index:999998;'+
            'box-shadow:0 5px 25px rgba(0,0,0,0.5);text-align:center;'+
            'font-weight:bold;animation:shake 0.5s;';
        alert.innerHTML = `
            <i class="fas fa-ban" style="font-size:2rem;margin-bottom:10px;"></i>
            <br>${message}
            <br><br>
            <span style="font-size:0.9rem;font-weight:normal;">
            This action is prohibited and has been logged.
            </span>
        `;
        document.body.appendChild(alert);
        
        setTimeout(function() {
            alert.remove();
        }, 3000);
    }

    // Add shake animation
    const shakeStyle = document.createElement('style');
    shakeStyle.textContent = `
        @keyframes shake {
            0%, 100% { transform: translate(-50%, -50%) rotate(0deg); }
            25% { transform: translate(-50%, -50%) rotate(-5deg); }
            75% { transform: translate(-50%, -50%) rotate(5deg); }
        }
    `;
    document.head.appendChild(shakeStyle);

    // ============================================
    // 9. VISIBILITY WARNING (on tab switch)
    // ============================================
    function showVisibilityWarning() {
        if (document.hidden) return; // Don't show if still hidden
        
        let existing = document.getElementById('visibility-warning');
        if (existing) existing.remove();
        
        let warning = document.createElement('div');
        warning.id = 'visibility-warning';
        warning.style = 'position:fixed;top:45%;left:50%;transform:translate(-50%,-50%);'+
            'background:rgba(255,50,50,0.95);color:#fff;padding:20px 35px;'+
            'border-radius:12px;font-size:1.2rem;z-index:999998;'+
            'box-shadow:0 4px 20px rgba(0,0,0,0.4);text-align:center;font-weight:600;';
        warning.innerHTML = `
            ⚠️ TAB SWITCH DETECTED!<br>
            <span style="font-size:0.95rem;font-weight:normal;">
            Your activity is being monitored and logged.
            </span>
        `;
        document.body.appendChild(warning);
        
        setTimeout(function() {
            warning.remove();
        }, 2500);
    }

    // ============================================
    // 10. BACKEND LOGGING FUNCTION
    // ============================================
    function sendSecurityViolation(type, description) {
        const csrfToken = document.querySelector('[name=csrf-token]')?.content || 
                         window.CSRF_TOKEN || '{{ csrf_token }}';
        
        fetch('/customer/log_security_violation/', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                violation_type: type,
                description: description,
                page_url: window.location.pathname,
                timestamp: new Date().toISOString()
            })
        }).catch(function(err) {
            console.error('Failed to log violation:', err);
        });
    }

    // ============================================
    // 11. DISABLE DRAG & DROP
    // ============================================
    document.addEventListener('dragstart', function(e) {
        e.preventDefault();
        return false;
    }, true);

    // ============================================
    // 12. PREVENT PRINT DIALOG
    // ============================================
    window.addEventListener('beforeprint', function(e) {
        e.preventDefault();
        showBlockedAlert('🚫 Printing is disabled!');
        sendSecurityViolation('print_attempt', 'User tried to print page');
        return false;
    });

    // Block Ctrl+P
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.keyCode === 80) {
            e.preventDefault();
            e.stopPropagation();
            showBlockedAlert('🚫 Printing is disabled!');
            sendSecurityViolation('print_attempt', 'Ctrl+P pressed');
            return false;
        }
    }, true);

    // ============================================
// 2.5 LOGOUT CONFIRMATION
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        const logoutLinks = document.querySelectorAll('a[href*="signout"], a[href*="logout"]');
        logoutLinks.forEach(function(link) {
            link.addEventListener('click', function(e) {
                if (!confirm('⚠️ Are you sure you want to LOGOUT?')) {
                    e.preventDefault();
                    return false;
                }
            });
        });
    }, 500);
});

    console.log('✅ ULTIMATE Security System Active - Maximum Protection Enabled');

})();
