import os
from django import template
from django.templatetags.static import static
from django.conf import settings

register = template.Library()

@register.filter
def static_exists(value):
    """
    Template filter to check if a static file exists.
    Usage: {% if 'images/photo.jpg'|static_exists %}
    """
    try:
        # Try to get the static file path
        static_path = static(value)
        
        # Check if file exists in any of the static directories
        for static_dir in settings.STATICFILES_DIRS:
            full_path = os.path.join(static_dir, value)
            if os.path.exists(full_path):
                return True
        
        # Check in STATIC_ROOT if collectstatic was run
        if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            full_path = os.path.join(settings.STATIC_ROOT, value)
            if os.path.exists(full_path):
                return True
                
        return False
    except:
        return False

@register.simple_tag
def static_or_default(static_path, default_css_class="bg-gradient-to-br from-green-800 to-green-900"):
    """
    Template tag to return static URL or default CSS class.
    Usage: {% static_or_default 'images/photo.jpg' 'bg-red-500' %}
    """
    try:
        if static_exists(static_path):
            return static(static_path)
        else:
            return default_css_class
    except:
        return default_css_class