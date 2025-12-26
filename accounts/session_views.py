"""
Session management views for timeout and activity checking
"""

import time
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View
from genealogy.utils import create_audit_log


@login_required
@require_http_methods(["GET", "POST"])
def session_check(request):
    """
    AJAX endpoint to check session status and remaining time
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'unauthenticated',
            'redirect': '/accounts/login/'
        })
    
    # Get timeout settings
    session_timeout = getattr(settings, 'SESSION_TIMEOUT_SECONDS', 7200)
    warning_time = getattr(settings, 'SESSION_WARNING_SECONDS', 300)
    
    # Check for custom timeout (e.g., admin users)
    custom_timeout = request.session.get('custom_timeout')
    if custom_timeout:
        session_timeout = custom_timeout
    
    current_time = time.time()
    last_activity = request.session.get('last_activity', current_time)
    
    time_elapsed = current_time - last_activity
    time_remaining = session_timeout - time_elapsed
    
    if time_remaining <= 0:
        return JsonResponse({
            'status': 'expired',
            'message': 'Votre session a expiré. Redirection vers la page de connexion...',
            'redirect': '/accounts/login/'
        })
    elif time_remaining <= warning_time:
        return JsonResponse({
            'status': 'warning',
            'time_remaining': int(time_remaining),
            'time_remaining_minutes': int(time_remaining // 60),
            'message': f'Votre session expirera dans {int(time_remaining//60)} minute(s) et {int(time_remaining%60)} seconde(s).'
        })
    else:
        return JsonResponse({
            'status': 'active',
            'time_remaining': int(time_remaining),
            'time_remaining_minutes': int(time_remaining // 60)
        })


@login_required
@require_http_methods(["POST"])
def extend_session(request):
    """
    AJAX endpoint to extend user session
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Utilisateur non authentifié'
        })
    
    # Update last activity time
    current_time = time.time()
    request.session['last_activity'] = current_time
    
    # Get timeout settings
    session_timeout = getattr(settings, 'SESSION_TIMEOUT_SECONDS', 7200)
    custom_timeout = request.session.get('custom_timeout')
    if custom_timeout:
        session_timeout = custom_timeout
    
    # Log session extension for audit
    try:
        create_audit_log(
            user=request.user,
            action='session_extend',
            model_name='User',
            object_id=request.user.id,
            changes={'action': 'Session extended'},
            request=request
        )
    except Exception:
        pass  # Don't fail if audit logging fails
    
    return JsonResponse({
        'status': 'success',
        'message': 'Session prolongée avec succès',
        'time_remaining': session_timeout,
        'time_remaining_minutes': int(session_timeout // 60)
    })


@method_decorator(login_required, name='dispatch')
class SessionManagementView(View):
    """
    View for handling various session management operations
    """
    
    def get(self, request):
        """Get session information"""
        current_time = time.time()
        last_activity = request.session.get('last_activity', current_time)
        session_timeout = getattr(settings, 'SESSION_TIMEOUT_SECONDS', 7200)
        
        custom_timeout = request.session.get('custom_timeout')
        if custom_timeout:
            session_timeout = custom_timeout
        
        time_elapsed = current_time - last_activity
        time_remaining = session_timeout - time_elapsed
        
        return JsonResponse({
            'user': {
                'username': request.user.username,
                'full_name': request.user.get_full_name(),
                'role': getattr(request.user, 'role', 'user')
            },
            'session': {
                'time_remaining': int(max(0, time_remaining)),
                'time_remaining_minutes': int(max(0, time_remaining) // 60),
                'total_timeout': session_timeout,
                'last_activity': last_activity,
                'session_key': request.session.session_key[:8] + '...'  # Partial for security
            },
            'settings': {
                'warning_time': getattr(settings, 'SESSION_WARNING_SECONDS', 300),
                'auto_extend': getattr(settings, 'SESSION_AUTO_EXTEND', False)
            }
        })
    
    def post(self, request):
        """Handle session management actions"""
        action = request.POST.get('action')
        
        if action == 'extend':
            return extend_session(request)
        elif action == 'check':
            return session_check(request)
        elif action == 'logout':
            # This will be handled by the logout view
            return JsonResponse({
                'status': 'redirect',
                'redirect': '/accounts/logout/'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Action non reconnue'
            })


@login_required
def session_info(request):
    """
    Get detailed session information for debugging/admin purposes
    """
    if not request.user.is_staff:  # Only for staff/admin users
        return JsonResponse({
            'status': 'error',
            'message': 'Accès non autorisé'
        })
    
    current_time = time.time()
    session_data = {
        'session_key': request.session.session_key,
        'session_data': dict(request.session),
        'current_time': current_time,
        'user_id': request.user.id,
        'user_role': getattr(request.user, 'role', 'user'),
        'session_timeout': getattr(settings, 'SESSION_TIMEOUT_SECONDS', 7200),
        'warning_time': getattr(settings, 'SESSION_WARNING_SECONDS', 300)
    }
    
    # Remove sensitive data before returning
    if 'current_session_key' in session_data['session_data']:
        session_data['session_data']['current_session_key'] = '***'
    
    return JsonResponse({
        'status': 'success',
        'data': session_data
    })