// static/js/customer-security-balanced.js
// Balanced approach - No auto-logout

(function() {
    'use strict';
    
    console.log('🔒 Balanced Security Active');
    
    let warningShown = false;
    
    function showWarning(reason) {
        if (warningShown) return;
        warningShown = true;
        
        // Log to server
        fetch('/customers/ajax/log-security-violation/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                violation_type: 'screenshot_attempt',
                description: reason,
                severity: 'high'
            })
        });
        
        // Show overlay for 3 seconds only
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: #000; z-index: 999999; color: white; display: flex;
            justify-content: center; align-items: center; font-size: 24px;
        `;
        overlay.innerHTML = `
            <div style="text-align: center; background: red; padding: 30px; border-radius: 15px;">
                <div style="font-size: 60px;">🚫</div>
                <div>Screenshot Not Allowed</div>
                <div style="font-size: 16px; margin-top: 10px;">Security Protection Active</div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // Remove overlay after 3 seconds
        setTimeout(() => {
            overlay.remove();
            warningShown = false;
        }, 3000);
    }
    
    // Simple key detection
    document.addEventListener('keydown', function(e) {
        // PrintScreen
        if (e.keyCode === 44) {
            e.preventDefault();
            showWarning('PrintScreen Key');
            return false;
        }
        
        // Snip Tool
        if (e.metaKey && e.shiftKey && e.keyCode === 83) {
            e.preventDefault();
            showWarning('Windows Snip Tool');
            return false;
        }
        
        // F12
        if (e.keyCode === 123) {
            e.preventDefault();
            showWarning('Developer Tools');
            return false;
        }
    });
    
    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    }
    
})();