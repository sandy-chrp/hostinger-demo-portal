// static/js/customer-security-copypaste.js
/**
 * Copy/Paste Protection for Customer Portal
 */

(function() {
    'use strict';

    console.log('🔒 Copy/Paste Protection Loading...');

    // ==========================================
    // COPY/PASTE BLOCKING
    // ==========================================

    // Disable copy
    document.addEventListener('copy', function(e) {
        e.preventDefault();
        e.stopPropagation();
        e.clipboardData.setData('text/plain', 'Content copying is disabled for security.');
        
        if (window.CustomerSecurity) {
            window.CustomerSecurity.incrementViolation('copy_attempt');
        }
        
        showQuickAlert('Copy Disabled', 'Content copying is not allowed for security purposes.');
        return false;
    }, true);

    // Disable cut
    document.addEventListener('cut', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (window.CustomerSecurity) {
            window.CustomerSecurity.incrementViolation('cut_attempt');
        }
        
        showQuickAlert('Cut Disabled', 'Content cutting is not allowed.');
        return false;
    }, true);

    // Disable paste (in protected areas)
    document.addEventListener('paste', function(e) {
        if (!e.target.classList.contains('allow-paste')) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    }, true);

    // Disable text selection
    document.addEventListener('selectstart', function(e) {
        if (!e.target.classList.contains('allow-select')) {
            e.preventDefault();
            return false;
        }
    }, true);

    // Disable right-click context menu
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        
        if (window.CustomerSecurity) {
            window.CustomerSecurity.incrementViolation('context_menu');
        }
        
        showQuickAlert('Right-Click Disabled', 'Context menu is disabled for security.');
        return false;
    }, true);

    // Disable keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+C, Ctrl+X, Ctrl+V, Ctrl+A
        if (e.ctrlKey && [67, 88, 86, 65].includes(e.keyCode)) {
            e.preventDefault();
            if (window.CustomerSecurity) {
                window.CustomerSecurity.incrementViolation('keyboard_shortcut');
            }
            showQuickAlert('Shortcut Disabled', 'Keyboard shortcuts are disabled.');
            return false;
        }

        // Cmd+C, Cmd+X, Cmd+V, Cmd+A (Mac)
        if (e.metaKey && [67, 88, 86, 65].includes(e.keyCode)) {
            e.preventDefault();
            if (window.CustomerSecurity) {
                window.CustomerSecurity.incrementViolation('keyboard_shortcut');
            }
            return false;
        }

        // F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U (Developer tools)
        if (e.keyCode === 123 || 
            (e.ctrlKey && e.shiftKey && [73, 74].includes(e.keyCode)) ||
            (e.ctrlKey && e.keyCode === 85)) {
            e.preventDefault();
            if (window.CustomerSecurity) {
                window.CustomerSecurity.incrementViolation('devtools_attempt');
            }
            return false;
        }

        // Ctrl+F (Find)
        if (e.ctrlKey && e.keyCode === 70) {
            e.preventDefault();
            return false;
        }
    }, true);

    // ==========================================
    // DRAG & DROP BLOCKING
    // ==========================================

    document.addEventListener('dragstart', function(e) {
        e.preventDefault();
        return false;
    }, true);

    document.addEventListener('drop', function(e) {
        e.preventDefault();
        return false;
    }, true);

    // ==========================================
    // UTILITY FUNCTIONS
    // ==========================================

    function showQuickAlert(title, message) {
        // Remove existing alert
        const existing = document.getElementById('quick-security-alert');
        if (existing) existing.remove();

        const alert = document.createElement('div');
        alert.id = 'quick-security-alert';
        alert.innerHTML = `
            <div style="position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #f44336; color: white; padding: 15px 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 10001; animation: slideDown 0.3s ease;">
                <strong>${title}</strong>: ${message}
            </div>
        `;
        document.body.appendChild(alert);

        // Auto remove after 3 seconds
        setTimeout(() => alert.remove(), 3000);
    }

    // Add animation styles
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideDown {
            from { transform: translateX(-50%) translateY(-100%); opacity: 0; }
            to { transform: translateX(-50%) translateY(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);

    console.log('✅ Copy/Paste Protection Active');

})();