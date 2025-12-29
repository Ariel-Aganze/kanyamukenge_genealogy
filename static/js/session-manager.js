/**
 * Session Timeout Management
 * Handles automatic logout, warnings, and session extension
 */

class SessionManager {
    constructor(options = {}) {
        this.options = {
            checkInterval: options.checkInterval || 30000, // Check every 30 seconds
            warningTime: options.warningTime || 300, // Show warning 5 minutes before expiry
            autoExtend: options.autoExtend || false, // Auto-extend session on activity
            endpoints: {
                check: options.endpoints?.check || '/accounts/session-check/',
                extend: options.endpoints?.extend || '/accounts/extend-session/',
                logout: options.endpoints?.logout || '/accounts/logout/'
            },
            ...options
        };
        
        this.isActive = true;
        this.warningShown = false;
        this.checkTimer = null;
        this.activityTimer = null;
        this.warningModal = null;
        
        this.init();
    }
    
    init() {
        console.log('🔐 Initializing Session Manager...');
        this.setupActivityTracking();
        this.startSessionChecking();
        this.createWarningModal();
    }
    
    setupActivityTracking() {
        // Track user activity
        const activities = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
        
        activities.forEach(event => {
            document.addEventListener(event, () => {
                this.onUserActivity();
            }, { passive: true });
        });
        
        // Track page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.checkSessionStatus();
            }
        });
    }
    
    onUserActivity() {
        if (!this.isActive) return;
        
        // Reset activity timer
        if (this.activityTimer) {
            clearTimeout(this.activityTimer);
        }
        
        // If auto-extend is enabled and warning is shown, extend session
        if (this.options.autoExtend && this.warningShown) {
            this.extendSession();
        }
        
        // Set timer for next activity check
        this.activityTimer = setTimeout(() => {
            // No activity for a while
        }, 60000); // 1 minute
    }
    
    startSessionChecking() {
        this.checkSessionStatus();
        
        this.checkTimer = setInterval(() => {
            this.checkSessionStatus();
        }, this.options.checkInterval);
    }
    
    async checkSessionStatus() {
        try {
            const response = await fetch(this.options.endpoints.check, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.handleSessionResponse(data);
            
        } catch (error) {
            console.error('⚠️ Session check failed:', error);
            // On network error, reduce check frequency
            this.options.checkInterval = Math.min(this.options.checkInterval * 1.5, 120000);
        }
    }
    
    handleSessionResponse(data) {
        switch (data.status) {
            case 'expired':
                this.handleSessionExpired(data);
                break;
                
            case 'warning':
                this.handleSessionWarning(data);
                break;
                
            case 'active':
                this.handleSessionActive(data);
                break;
                
            case 'unauthenticated':
                this.handleUnauthenticated(data);
                break;
                
            default:
                console.warn('Unknown session status:', data.status);
        }
    }
    
    handleSessionExpired(data) {
        console.log('⏰ Session expired');
        this.isActive = false;
        this.stopChecking();
        
        this.showExpiredMessage(data.message || 'Votre session a expiré.');
        
        setTimeout(() => {
            window.location.href = data.redirect || '/accounts/login/';
        }, 3000);
    }
    
    handleSessionWarning(data) {
        if (!this.warningShown) {
            console.log('⚠️ Session warning:', data.time_remaining_minutes, 'minutes remaining');
            this.showWarningModal(data);
            this.warningShown = true;
        } else {
            // Update existing warning
            this.updateWarningModal(data);
        }
    }
    
    handleSessionActive(data) {
        if (this.warningShown) {
            this.hideWarningModal();
            this.warningShown = false;
        }
        
        // Reset check interval to normal
        this.options.checkInterval = 30000;
    }
    
    handleUnauthenticated(data) {
        this.isActive = false;
        this.stopChecking();
        window.location.href = data.redirect || '/accounts/login/';
    }
    
    async extendSession() {
        try {
            const response = await fetch(this.options.endpoints.extend, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'same-origin',
                body: JSON.stringify({ action: 'extend' })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log('✅ Session extended successfully');
                this.hideWarningModal();
                this.warningShown = false;
                
                // Show success notification
                this.showNotification('Session prolongée avec succès', 'success');
            }
            
        } catch (error) {
            console.error('❌ Failed to extend session:', error);
            this.showNotification('Erreur lors de la prolongation de session', 'error');
        }
    }
    
    createWarningModal() {
        // Create modal HTML
        const modalHTML = `
            <div id="session-warning-modal" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center hidden">
                <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                    <div class="p-6">
                        <div class="flex items-center mb-4">
                            <div class="flex-shrink-0">
                                <svg class="h-8 w-8 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 19.5c-.77.833.192 2.5 1.732 2.5z"/>
                                </svg>
                            </div>
                            <div class="ml-4">
                                <h3 class="text-lg font-medium text-gray-900">Avertissement de Session</h3>
                            </div>
                        </div>
                        <div class="mb-4">
                            <p id="session-warning-message" class="text-sm text-gray-700">
                                Votre session expirera bientôt.
                            </p>
                            <div class="mt-3">
                                <div id="session-countdown" class="text-2xl font-bold text-amber-600">
                                    05:00
                                </div>
                            </div>
                        </div>
                        <div class="flex justify-end space-x-3">
                            <button id="session-logout-btn" class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 border border-gray-300 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500">
                                Se déconnecter
                            </button>
                            <button id="session-extend-btn" class="px-4 py-2 text-sm font-medium text-white bg-brand-primary border border-transparent rounded-md hover:bg-green-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500">
                                Prolonger la session
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Add event listeners
        document.getElementById('session-extend-btn').addEventListener('click', () => {
            this.extendSession();
        });
        
        document.getElementById('session-logout-btn').addEventListener('click', () => {
            window.location.href = this.options.endpoints.logout;
        });
        
        this.warningModal = document.getElementById('session-warning-modal');
    }
    
    showWarningModal(data) {
        const messageEl = document.getElementById('session-warning-message');
        const countdownEl = document.getElementById('session-countdown');
        
        messageEl.textContent = data.message || 'Votre session expirera bientôt.';
        
        this.updateCountdown(data.time_remaining);
        this.warningModal.classList.remove('hidden');
        
        // Start countdown timer
        this.countdownInterval = setInterval(() => {
            this.checkSessionStatus(); // This will update the countdown
        }, 1000);
    }
    
    updateWarningModal(data) {
        this.updateCountdown(data.time_remaining);
    }
    
    updateCountdown(timeRemaining) {
        const countdownEl = document.getElementById('session-countdown');
        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        
        countdownEl.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Change color as time gets low
        if (timeRemaining <= 60) {
            countdownEl.className = 'text-2xl font-bold text-red-600';
        } else if (timeRemaining <= 180) {
            countdownEl.className = 'text-2xl font-bold text-orange-600';
        } else {
            countdownEl.className = 'text-2xl font-bold text-amber-600';
        }
    }
    
    hideWarningModal() {
        if (this.warningModal) {
            this.warningModal.classList.add('hidden');
        }
        
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
    }
    
    showExpiredMessage(message) {
        this.showNotification(message, 'error', 0); // Don't auto-hide
    }
    
    showNotification(message, type = 'info', duration = 5000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 max-w-sm w-full bg-white border rounded-lg shadow-lg ${
            type === 'success' ? 'border-green-200' : 
            type === 'error' ? 'border-red-200' : 
            'border-blue-200'
        }`;
        
        const iconColor = type === 'success' ? 'text-green-500' : 
                         type === 'error' ? 'text-red-500' : 
                         'text-blue-500';
        
        notification.innerHTML = `
            <div class="p-4">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 ${iconColor}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            ${type === 'success' ? 
                                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>' :
                                type === 'error' ?
                                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>' :
                                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'
                            }
                        </svg>
                    </div>
                    <div class="ml-3 w-0 flex-1">
                        <p class="text-sm font-medium text-gray-900">${message}</p>
                    </div>
                    <div class="ml-4 flex-shrink-0 flex">
                        <button class="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none" onclick="this.parentElement.parentElement.parentElement.parentElement.remove()">
                            <span class="sr-only">Fermer</span>
                            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove notification
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, duration);
        }
    }
    
    getCSRFToken() {
        const tokenEl = document.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenEl) {
            return tokenEl.value;
        }
        
        // Try to get from cookies
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        return '';
    }
    
    stopChecking() {
        if (this.checkTimer) {
            clearInterval(this.checkTimer);
        }
        if (this.activityTimer) {
            clearTimeout(this.activityTimer);
        }
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
    }
    
    destroy() {
        this.isActive = false;
        this.stopChecking();
        
        if (this.warningModal) {
            this.warningModal.remove();
        }
    }
}

// Auto-initialize session manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on authenticated pages (check if user is logged in)
    if (document.body.dataset.authenticated === 'true' || 
        document.querySelector('.auth-required') ||
        window.location.pathname.includes('/dashboard/')) {
        
        console.log('🔐 Starting Session Manager...');
        
        // Initialize with default options (can be overridden)
        window.sessionManager = new SessionManager({
            checkInterval: 30000, // 30 seconds
            warningTime: 300, // 5 minutes
            autoExtend: false, // Require manual extension
            endpoints: {
                check: '/accounts/session-check/',
                extend: '/accounts/extend-session/',
                logout: '/accounts/logout/'
            }
        });
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.sessionManager) {
        window.sessionManager.destroy();
    }
});