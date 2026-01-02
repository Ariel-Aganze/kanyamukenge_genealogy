from django import template
from django.contrib.auth import get_user_model

User = get_user_model()
register = template.Library()

@register.simple_tag
def get_unread_notifications_count(user):
    """Get count of unread notifications for a user - simplified version"""
    try:
        # Import here to avoid circular imports
        from genealogy.models import Notification
        return Notification.objects.filter(recipient=user, is_read=False).count()
    except:
        # If Notification model doesn't exist yet, return 0
        return 0

@register.inclusion_tag('genealogy/templatetags/notifications_badge.html')
def notifications_badge(user):
    """Render notifications count badge - simplified version"""
    try:
        # Import here to avoid circular imports
        from genealogy.models import Notification
        count = Notification.objects.filter(recipient=user, is_read=False).count()
        return {
            'count': count,
            'show_badge': count > 0,
            'user': user
        }
    except:
        # If Notification model doesn't exist yet, return empty
        return {
            'count': 0,
            'show_badge': False,
            'user': user
        }

@register.simple_tag
def get_recent_notifications(user, limit=5):
    """Get recent notifications for a user"""
    try:
        from genealogy.models import Notification
        return Notification.objects.filter(recipient=user).order_by('-created_at')[:limit]
    except:
        return []

@register.inclusion_tag('genealogy/templatetags/notifications_dropdown.html')
def notifications_dropdown(user):
    """Render notifications dropdown content"""
    try:
        from genealogy.models import Notification
        notifications = Notification.objects.filter(recipient=user).order_by('-created_at')[:10]
        unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
        return {
            'notifications': notifications,
            'unread_count': unread_count,
            'user': user,
            'has_notifications': notifications.exists()
        }
    except:
        return {
            'notifications': [],
            'unread_count': 0,
            'user': user,
            'has_notifications': False
        }

@register.filter
def time_since_short(value):
    """Custom filter for short time since format"""
    if not value:
        return ""
    
    from django.utils import timezone
    import datetime
    
    now = timezone.now()
    diff = now - value
    
    if diff.days > 7:
        return value.strftime('%d/%m')
    elif diff.days > 0:
        return f"{diff.days}j"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours}h"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes}m"
    else:
        return "maintenant"