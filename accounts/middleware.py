import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages
from django.http import JsonResponse
from genealogy.utils import create_audit_log


class SessionTimeoutMiddleware(MiddlewareMixin):
    """
    Enhanced session timeout middleware with configurable timeouts and warnings
    """
    
    def process_request(self, request):
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return None
            
        # Skip for certain endpoints (like logout, static files, etc.)
        skip_paths = [
            reverse('accounts:logout'),
            '/static/',
            '/media/',
            '/admin/jsi18n/',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return None
            
        # Get timeout settings from Django settings or use defaults
        session_timeout = getattr(settings, 'SESSION_TIMEOUT_SECONDS', 7200)  # 2 hours default
        warning_time = getattr(settings, 'SESSION_WARNING_SECONDS', 300)  # 5 minutes warning
        
        current_time = time.time()
        
        # Check if this is a session activity check (AJAX request)
        if request.path == '/accounts/session-check/':
            last_activity = request.session.get('last_activity')
            if last_activity:
                time_elapsed = current_time - last_activity
                time_remaining = session_timeout - time_elapsed
                
                if time_remaining <= 0:
                    # Session has expired
                    return JsonResponse({
                        'status': 'expired',
                        'message': 'Votre session a expiré. Veuillez vous reconnecter.'
                    })
                elif time_remaining <= warning_time:
                    # Show warning
                    return JsonResponse({
                        'status': 'warning',
                        'time_remaining': int(time_remaining),
                        'message': f'Votre session expirera dans {int(time_remaining//60)} minute(s).'
                    })
                else:
                    # Session is still valid
                    return JsonResponse({
                        'status': 'active',
                        'time_remaining': int(time_remaining)
                    })
            else:
                # No last activity recorded, set it now
                request.session['last_activity'] = current_time
                return JsonResponse({
                    'status': 'active',
                    'time_remaining': session_timeout
                })
        
        # Regular request processing
        last_activity = request.session.get('last_activity')
        
        if last_activity:
            time_elapsed = current_time - last_activity
            
            # Check if session has expired
            if time_elapsed > session_timeout:
                # Create audit log for session timeout
                try:
                    create_audit_log(
                        user=request.user,
                        action='logout',
                        model_name='User',
                        object_id=request.user.id,
                        changes={'reason': 'Session timeout'},
                        request=request
                    )
                except Exception:
                    pass  # Don't break if audit logging fails
                
                # Add message about session expiry (with error handling)
                try:
                    messages.warning(request, 'Votre session a expiré pour des raisons de sécurité. Veuillez vous reconnecter.')
                except Exception:
                    # Messages framework not available, continue without message
                    pass
                
                # Logout user and redirect to login
                logout(request)
                return redirect('accounts:login')
        
        # Update last activity time
        request.session['last_activity'] = current_time
        
        # Also store user preferences for timeout (if admin wants different settings)
        if hasattr(request.user, 'role'):
            if request.user.role == 'admin':
                # Admins might have extended sessions
                admin_timeout = getattr(settings, 'ADMIN_SESSION_TIMEOUT_SECONDS', session_timeout)
                if admin_timeout != session_timeout:
                    request.session['custom_timeout'] = admin_timeout
        
        return None


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Additional security middleware for session management
    """
    
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
            
        # Check for concurrent sessions (optional security feature)
        if getattr(settings, 'PREVENT_CONCURRENT_SESSIONS', False):
            current_session_key = request.session.session_key
            stored_session_key = request.session.get('current_session_key')
            
            if stored_session_key and stored_session_key != current_session_key:
                # User has logged in from another device/browser
                try:
                    messages.warning(
                        request, 
                        'Vous avez été déconnecté car vous vous êtes connecté depuis un autre appareil.'
                    )
                except Exception:
                    # Messages framework not available, continue without message
                    pass
                logout(request)
                return redirect('accounts:login')
            
            # Store current session key
            request.session['current_session_key'] = current_session_key
        
        # Check for suspicious activity (IP changes, user agent changes)
        if getattr(settings, 'CHECK_SESSION_IP', False):
            current_ip = self.get_client_ip(request)
            stored_ip = request.session.get('session_ip')
            
            if stored_ip and stored_ip != current_ip:
                # IP has changed - could be session hijacking
                try:
                    create_audit_log(
                        user=request.user,
                        action='security_alert',
                        model_name='User',
                        object_id=request.user.id,
                        changes={
                            'alert_type': 'IP_change',
                            'old_ip': stored_ip,
                            'new_ip': current_ip
                        },
                        request=request
                    )
                except Exception:
                    pass
                
                try:
                    messages.error(
                        request,
                        'Activité suspecte détectée. Vous avez été déconnecté par sécurité.'
                    )
                except Exception:
                    # Messages framework not available, continue without message
                    pass
                logout(request)
                return redirect('accounts:login')
            
            # Store current IP
            request.session['session_ip'] = current_ip
            
        return None
    
    def get_client_ip(self, request):
        """Get the real IP address of the client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip