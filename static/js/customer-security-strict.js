// customer-security-strict.js - STRICT PROTECTION
(function() {
    'use strict';

    console.log('🔒 Strict Security Initializing...');

    // ==========================================
    // GET CSRF TOKEN
    // ==========================================
    function getCSRFToken() {
        let token = document.querySelector('[name=csrf-token]')?.content;
        if (!token) token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!token) {
            const cookieValue = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
            if (cookieValue) token = cookieValue.split('=')[1];
        }
        return token;
    }

    // ==========================================
    // EXEMPTED ELEMENTS (Only navigation and forms)
    // ==========================================
    function isExemptedElement(element) {
        if (!element) return false;
        
        // Only exempt these specific elements
        const exemptSelectors = [
            'INPUT',
            'TEXTAREA', 
            'SELECT',
            'BUTTON',
            '.sidebar-nav a',
            '.customer-header a',
            '.btn',
            '#tawkchat-container',
            'iframe[src*="tawk"]'
        ];

        // Check if it's a form element
        if (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(element.tagName)) {
            return true;
        }

        // Check if inside Tawk chat
        if (element.closest('#tawkchat-container, iframe[src*="tawk"]')) {
            return true;
        }

        return false;
    }

    // ==========================================
    // 1. BLOCK RIGHT CLICK - STRICT
    // ==========================================
    document.addEventListener('contextmenu', function(e) {
        // Only allow on input fields
        if (isExemptedElement(e.target)) {
            return true;
        }

        e.preventDefault();
        e.stopPropagation();
        showWarning('⚠️ Right-click is disabled');
        logActivity('right_click_blocked', 'Right-click attempt blocked');
        return false;
    }, true); // Use capture phase

    // ==========================================
    // 2. BLOCK COPY - STRICT
    // ==========================================
    document.addEventListener('copy', function(e) {
        if (isExemptedElement(e.target)) {
            return true;
        }

        e.preventDefault();
        e.stopPropagation();
        e.clipboardData.setData('text/plain', '');
        showWarning('⚠️ Copy is disabled');
        logActivity('copy_blocked', 'Copy attempt blocked');
        return false;
    }, true);

    // ==========================================
    // 3. BLOCK CUT - STRICT
    // ==========================================
    document.addEventListener('cut', function(e) {
        if (isExemptedElement(e.target)) {
            return true;
        }

        e.preventDefault();
        e.stopPropagation();
        showWarning('⚠️ Cut is disabled');
        logActivity('cut_blocked', 'Cut attempt blocked');
        return false;
    }, true);

    // ==========================================
    // 4. BLOCK PASTE (Except in forms)
    // ==========================================
    document.addEventListener('paste', function(e) {
        if (isExemptedElement(e.target)) {
            return true;
        }

        e.preventDefault();
        e.stopPropagation();
        showWarning('⚠️ Paste is disabled');
        return false;
    }, true);

    // ==========================================
    // 5. BLOCK TEXT SELECTION - STRICT
    // ==========================================
    document.addEventListener('selectstart', function(e) {
        if (isExemptedElement(e.target)) {
            return true;
        }

        e.preventDefault();
        e.stopPropagation();
        return false;
    }, true);

    // Also block selection using CSS
    document.addEventListener('mousedown', function(e) {
        if (!isExemptedElement(e.target)) {
            e.preventDefault();
        }
    }, true);

    // ==========================================
    // 6. BLOCK KEYBOARD SHORTCUTS
    // ==========================================
    document.addEventListener('keydown', function(e) {
        // F12 - Developer Tools
        if (e.keyCode === 123 || e.key === 'F12') {
            e.preventDefault();
            showWarning('⚠️ Developer tools are disabled');
            logActivity('f12_blocked', 'F12 pressed');
            return false;
        }

        // Ctrl+Shift+I - Inspect
        if (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.key === 'I')) {
            e.preventDefault();
            showWarning('⚠️ Inspect element is disabled');
            logActivity('inspect_blocked', 'Ctrl+Shift+I pressed');
            return false;
        }

        // Ctrl+Shift+J - Console
        if (e.ctrlKey && e.shiftKey && (e.keyCode === 74 || e.key === 'J')) {
            e.preventDefault();
            showWarning('⚠️ Console is disabled');
            logActivity('console_blocked', 'Ctrl+Shift+J pressed');
            return false;
        }

        // Ctrl+Shift+C - Inspect
        if (e.ctrlKey && e.shiftKey && (e.keyCode === 67 || e.key === 'C')) {
            e.preventDefault();
            showWarning('⚠️ Inspect is disabled');
            logActivity('inspect_blocked', 'Ctrl+Shift+C pressed');
            return false;
        }

        // Ctrl+U - View Source
        if (e.ctrlKey && (e.keyCode === 85 || e.key === 'u')) {
            e.preventDefault();
            showWarning('⚠️ View source is disabled');
            logActivity('view_source_blocked', 'Ctrl+U pressed');
            return false;
        }

        // Ctrl+S - Save
        if (e.ctrlKey && (e.keyCode === 83 || e.key === 's')) {
            e.preventDefault();
            showWarning('⚠️ Save is disabled');
            logActivity('save_blocked', 'Ctrl+S pressed');
            return false;
        }

        // Ctrl+P - Print
        if (e.ctrlKey && (e.keyCode === 80 || e.key === 'p')) {
            e.preventDefault();
            showWarning('⚠️ Print is disabled');
            logActivity('print_blocked', 'Ctrl+P pressed');
            return false;
        }

        // Ctrl+C - Copy (Backup block)
        if (e.ctrlKey && (e.keyCode === 67 || e.key === 'c') && !e.shiftKey) {
            if (!isExemptedElement(e.target)) {
                e.preventDefault();
                showWarning('⚠️ Copy is disabled');
                logActivity('ctrl_c_blocked', 'Ctrl+C pressed');
                return false;
            }
        }

        // Ctrl+X - Cut (Backup block)
        if (e.ctrlKey && (e.keyCode === 88 || e.key === 'x')) {
            if (!isExemptedElement(e.target)) {
                e.preventDefault();
                showWarning('⚠️ Cut is disabled');
                logActivity('ctrl_x_blocked', 'Ctrl+X pressed');
                return false;
            }
        }

        // Ctrl+A - Select All (except in forms)
        if (e.ctrlKey && (e.keyCode === 65 || e.key === 'a')) {
            if (!isExemptedElement(e.target)) {
                e.preventDefault();
                showWarning('⚠️ Select all is disabled');
                return false;
            }
        }
    }, true);

    // ==========================================
    // 7. BLOCK PRINTSCREEN
    // ==========================================
    document.addEventListener('keyup', function(e) {
        if (e.key === 'PrintScreen' || e.keyCode === 44) {
            navigator.clipboard.writeText('').catch(() => {});
            showWarning('⚠️ Screenshots are disabled');
            logActivity('printscreen_blocked', 'PrintScreen pressed');
            blurScreen();
        }
    }, true);

    // ==========================================
    // 8. BLUR SCREEN ON SCREENSHOT
    // ==========================================
    function blurScreen() {
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            z-index: 999999;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        overlay.innerHTML = `
            <div style="text-align: center; color: #ef4444; font-size: 24px; font-weight: bold;">
                <i class="fas fa-ban" style="font-size: 64px; display: block; margin-bottom: 20px;"></i>
                Screenshot Detected!<br>
                <span style="font-size: 16px;">This action has been logged</span>
            </div>
        `;
        document.body.appendChild(overlay);
        setTimeout(() => overlay.remove(), 2000);
    }

    // ==========================================
    // 9. PREVENT DRAG & DROP
    // ==========================================
    document.addEventListener('dragstart', function(e) {
        e.preventDefault();
        showWarning('⚠️ Dragging is disabled');
        return false;
    }, true);

    // ==========================================
    // 10. DISABLE DEVELOPER TOOLS DETECTION
    // ==========================================
    let devtoolsOpen = false;
    const detectDevTools = () => {
        const widthThreshold = window.outerWidth - window.innerWidth > 160;
        const heightThreshold = window.outerHeight - window.innerHeight > 160;
        
        if (widthThreshold || heightThreshold) {
            if (!devtoolsOpen) {
                devtoolsOpen = true;
                showWarning('⚠️ Developer tools detected');
                logActivity('devtools_detected', 'Developer tools opened');
            }
        } else {
            devtoolsOpen = false;
        }
    };

    setInterval(detectDevTools, 1000);

    // ==========================================
    // 11. SHOW WARNING POPUP
    // ==========================================
    function showWarning(message) {
        const existing = document.getElementById('security-warning-toast');
        if (existing) existing.remove();
        
        const toast = document.createElement('div');
        toast.id = 'security-warning-toast';
        toast.innerHTML = `
            <i class="fas fa-shield-alt"></i>
            <span>${message}</span>
        `;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            z-index: 999999;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
            font-size: 14px;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // ==========================================
    // 12. LOG ACTIVITY TO SERVER
    // ==========================================
    let logQueue = [];
    let isLogging = false;

    function logActivity(type, description) {
        logQueue.push({ type, description, time: Date.now() });
        if (!isLogging) processQueue();
    }

    function processQueue() {
        if (logQueue.length === 0) {
            isLogging = false;
            return;
        }

        isLogging = true;
        const item = logQueue.shift();

        // Debounce - only log if 2 seconds passed
        if (window.lastLogTime && (Date.now() - window.lastLogTime) < 2000) {
            setTimeout(processQueue, 100);
            return;
        }

        window.lastLogTime = Date.now();
        const csrfToken = getCSRFToken();

        if (!csrfToken) {
            console.warn('⚠️ CSRF token missing');
            setTimeout(processQueue, 100);
            return;
        }

        fetch('/customer/ajax/log-security-violation/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                violation_type: item.type,
                description: item.description,
                timestamp: new Date(item.time).toISOString(),
                page_url: window.location.href
            }),
            credentials: 'same-origin'
        })
        .then(response => response.ok ? response.json() : Promise.reject())
        .then(() => console.log('✅ Activity logged'))
        .catch(() => console.warn('⚠️ Logging failed'))
        .finally(() => setTimeout(processQueue, 100));
    }

    // ==========================================
    // 13. ADD CSS STYLES
    // ==========================================
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }

        /* Disable selection on everything except forms */
        * {
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            user-select: none !important;
        }

        /* Allow selection only in forms */
        input, textarea, select {
            -webkit-user-select: text !important;
            -moz-user-select: text !important;
            -ms-user-select: text !important;
            user-select: text !important;
        }

        /* Disable drag on all images */
        img {
            -webkit-user-drag: none !important;
            user-drag: none !important;
            pointer-events: none !important;
        }

        /* Disable drag on videos */
        video {
            -webkit-user-drag: none !important;
            user-drag: none !important;
        }

        /* Hide video download button */
        video::-webkit-media-controls-download-button {
            display: none !important;
        }

        video::-internal-media-controls-download-button {
            display: none !important;
        }

        /* Prevent text selection styling */
        ::selection {
            background: transparent !important;
            color: inherit !important;
        }

        ::-moz-selection {
            background: transparent !important;
            color: inherit !important;
        }
    `;
    document.head.appendChild(style);

    // ==========================================
    // 14. CONTINUOUS MONITORING
    // ==========================================
    
    // Monitor clipboard continuously
    setInterval(() => {
        if (document.hasFocus() && !isExemptedElement(document.activeElement)) {
            navigator.clipboard.writeText('').catch(() => {});
        }
    }, 1000);

    // Clear selection continuously
    setInterval(() => {
        if (window.getSelection && !isExemptedElement(document.activeElement)) {
            const selection = window.getSelection();
            if (selection.toString().length > 0) {
                selection.removeAllRanges();
            }
        }
    }, 500);

    console.log('%c🔒 STRICT SECURITY ACTIVE', 'color: #ef4444; font-size: 16px; font-weight: bold;');
    console.log('%c• Right-click: BLOCKED', 'color: #6b7280; font-size: 12px;');
    console.log('%c• Copy/Paste: BLOCKED', 'color: #6b7280; font-size: 12px;');
    console.log('%c• Text Selection: BLOCKED', 'color: #6b7280; font-size: 12px;');
    console.log('%c• Screenshots: BLOCKED', 'color: #6b7280; font-size: 12px;');
    console.log('%c• Developer Tools: MONITORED', 'color: #6b7280; font-size: 12px;');

})();