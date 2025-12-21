# genealogy/templatetags/propositions_tags.py

from django import template
from django.contrib.auth import get_user_model
from ..models import ModificationProposal

User = get_user_model()
register = template.Library()

@register.simple_tag
def get_pending_proposals_count():
    """Get count of pending modification proposals"""
    try:
        return ModificationProposal.objects.filter(status='pending').count()
    except Exception:
        return 0

@register.inclusion_tag('genealogy/templatetags/pending_proposals_badge.html')
def pending_proposals_badge():
    """Render pending proposals count badge"""
    count = get_pending_proposals_count()
    return {
        'count': count,
        'show_badge': count > 0
    }