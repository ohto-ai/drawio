/**
 * Custom logo override for draw.io
 * This script replaces the default logo with a custom one
 */
(function() {
    'use strict';
    
    // Convert SVG to base64 data URL
    function getSVGDataURL() {
        // Custom SVG logo content
        const svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="36" viewBox="0 0 32 36" version="1.1">
            <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#4A90E2;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#357ABD;stop-opacity:1" />
                </linearGradient>
            </defs>
            <rect x="2" y="2" width="28" height="32" rx="4" ry="4" fill="url(#grad1)" stroke="#2E5B87" stroke-width="1"/>
            <circle cx="10" cy="12" r="3" fill="#FFFFFF" opacity="0.9"/>
            <circle cx="22" cy="12" r="3" fill="#FFFFFF" opacity="0.9"/>
            <circle cx="16" cy="24" r="3" fill="#FFFFFF" opacity="0.9"/>
            <line x1="10" y1="12" x2="22" y2="12" stroke="#FFFFFF" stroke-width="2" opacity="0.8"/>
            <line x1="10" y1="12" x2="16" y2="24" stroke="#FFFFFF" stroke-width="2" opacity="0.8"/>
            <line x1="22" y1="12" x2="16" y2="24" stroke="#FFFFFF" stroke-width="2" opacity="0.8"/>
        </svg>`;
        
        // Convert to base64
        const base64SVG = btoa(unescape(encodeURIComponent(svgContent)));
        return `data:image/svg+xml;base64,${base64SVG}`;
    }
    
    // Function to update the logo
    function updateCustomLogo() {
        // Override the global Editor.logoImage if it exists
        if (typeof Editor !== 'undefined') {
            const customLogoDataURL = getSVGDataURL();
            Editor.logoImage = customLogoDataURL;
            console.log('Custom logo applied to Editor.logoImage');
            
            // Update existing app icon if it exists
            const appIcon = document.querySelector('.geAppIcon');
            if (appIcon) {
                appIcon.style.backgroundImage = `url(${customLogoDataURL})`;
                console.log('Updated existing app icon with custom logo');
            }
        }
        
        // Also look for any existing app icons and update them
        const appIcons = document.querySelectorAll('.geAppIcon');
        appIcons.forEach(function(icon) {
            const customLogoDataURL = getSVGDataURL();
            icon.style.backgroundImage = `url(${customLogoDataURL})`;
        });
    }
    
    // Try to apply the logo immediately if Editor is available
    if (typeof Editor !== 'undefined') {
        updateCustomLogo();
    }
    
    // Set up a polling mechanism to catch the Editor when it becomes available
    let attempts = 0;
    const maxAttempts = 50; // Poll for up to 5 seconds
    const pollForEditor = setInterval(function() {
        attempts++;
        if (typeof Editor !== 'undefined' || attempts >= maxAttempts) {
            if (typeof Editor !== 'undefined') {
                updateCustomLogo();
            }
            clearInterval(pollForEditor);
        }
    }, 100);
    
    // Also listen for when the DOM is ready and apply logo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(updateCustomLogo, 1000);
        });
    } else {
        setTimeout(updateCustomLogo, 1000);
    }
    
    // Listen for window load event as a final fallback
    window.addEventListener('load', function() {
        setTimeout(updateCustomLogo, 2000);
    });
    
})();