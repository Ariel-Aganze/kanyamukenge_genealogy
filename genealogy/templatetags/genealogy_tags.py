from django import template

register = template.Library()

@register.simple_tag
def can_modify_person(person, user):
    """Check if user can modify person"""
    if not user.is_authenticated:
        return False
    
    if user.role == 'admin':
        return True
    
    if person.owned_by == user:
        return True
        
    if person.user_account == user:
        return True
    
    return False

@register.filter
def can_modify(person, user):
    """Check if user can modify person"""
    if not user.is_authenticated:
        return False
    
    # Si c'est un admin
    if hasattr(user, 'role') and user.role == 'admin':
        return True
    
    # Si c'est le propriétaire (ajustez selon votre modèle)
    if hasattr(person, 'owned_by') and person.owned_by == user:
        return True
        
    # Si c'est la personne elle-même
    if hasattr(person, 'user_account') and person.user_account == user:
        return True
    
    return False