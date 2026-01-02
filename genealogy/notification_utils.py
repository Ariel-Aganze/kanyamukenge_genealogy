"""
Notification utilities for genealogy system
Replaces email_utils.py with in-app notification system
"""

from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

def get_admin_users():
    """Get all admin users who should receive notifications"""
    return User.objects.filter(role='admin', is_active=True)

def create_notification(
    recipients, 
    notification_type, 
    title, 
    message, 
    related_person=None, 
    related_user=None, 
    related_proposal=None,
    action_url=None,
    priority='normal',
    created_by=None,
    expires_in_days=30
):
    """
    Create notifications for multiple recipients
    
    Args:
        recipients: List of User objects or single User object
        notification_type: Type from NOTIFICATION_TYPES choices
        title: Short title for the notification
        message: Detailed message
        related_person: Related Person object (optional)
        related_user: Related User object (optional)
        related_proposal: Related ModificationProposal object (optional)
        action_url: URL to navigate to when clicked (optional)
        priority: Priority level ('low', 'normal', 'high', 'urgent')
        created_by: User who created the notification
        expires_in_days: Days until notification expires (default 30)
    """
    from .models import Notification  # Import here to avoid circular imports
    
    # Ensure recipients is a list
    if isinstance(recipients, User):
        recipients = [recipients]
    
    # Calculate expiration date
    expires_at = timezone.now() + timedelta(days=expires_in_days) if expires_in_days else None
    
    notifications_created = []
    
    try:
        with transaction.atomic():
            for recipient in recipients:
                notification = Notification.objects.create(
                    recipient=recipient,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    related_person=related_person,
                    related_user=related_user,
                    related_proposal=related_proposal,
                    action_url=action_url,
                    priority=priority,
                    created_by=created_by,
                    expires_at=expires_at
                )
                notifications_created.append(notification)
                
        logger.info(f"Created {len(notifications_created)} notifications of type '{notification_type}'")
        return notifications_created
        
    except Exception as e:
        logger.error(f"Failed to create notifications: {str(e)}")
        return []

def notify_admins(
    notification_type, 
    title, 
    message, 
    **kwargs
):
    """Send notification to all admin users"""
    admin_users = get_admin_users()
    if not admin_users:
        logger.warning("No admin users found for notification")
        return []
    
    return create_notification(
        recipients=admin_users,
        notification_type=notification_type,
        title=title,
        message=message,
        **kwargs
    )

# Person-related notifications
def notify_person_created(person, user):
    """Notify admins when a new person is created"""
    title = "Nouvelle personne ajoutée"
    message = f"""
{person.get_full_name()} a été ajouté(e) au système généalogique par {user.get_full_name()}.

Informations:
• Date de naissance: {person.birth_date if person.birth_date else 'Non spécifiée'}
• Lieu de naissance: {person.birth_place if person.birth_place else 'Non spécifié'}
• Tribu: {person.tribus if person.tribus else 'Non spécifiée'}
• Clan: {person.clan if person.clan else 'Non spécifié'}
"""
    
    action_url = reverse('genealogy:person_detail', args=[person.id])
    
    return notify_admins(
        notification_type='person_created',
        title=title,
        message=message,
        related_person=person,
        related_user=user,
        action_url=action_url,
        created_by=user,
        priority='normal'
    )

def notify_person_edited(person, user, changed_fields=None):
    """Notify admins when a person's information is edited"""
    title = f"Informations modifiées - {person.get_full_name()}"
    
    changes_text = ""
    if changed_fields:
        changes_text = f"\n\nChamps modifiés: {', '.join(changed_fields)}"
    
    message = f"""
Les informations de {person.get_full_name()} ont été modifiées par {user.get_full_name()}.{changes_text}
"""
    
    action_url = reverse('genealogy:person_detail', args=[person.id])
    
    return notify_admins(
        notification_type='person_edited',
        title=title,
        message=message,
        related_person=person,
        related_user=user,
        action_url=action_url,
        created_by=user,
        priority='low'
    )

def notify_person_deleted(person_name, user):
    """Notify admins when a person is deleted"""
    title = f"Personne supprimée - {person_name}"
    message = f"""
{person_name} a été supprimé(e) du système généalogique par {user.get_full_name()}.

Cette action ne peut pas être annulée.
"""
    
    return notify_admins(
        notification_type='person_deleted',
        title=title,
        message=message,
        related_user=user,
        created_by=user,
        priority='high'
    )

def notify_child_added(parent, child, user):
    """Notify admins when a child is added to a person"""
    title = f"Nouvelle relation parent-enfant"
    message = f"""
Une nouvelle relation parent-enfant a été établie par {user.get_full_name()}:

• Parent: {parent.get_full_name()}
• Enfant: {child.get_full_name()}
"""
    
    action_url = reverse('genealogy:person_detail', args=[parent.id])
    
    return notify_admins(
        notification_type='child_added',
        title=title,
        message=message,
        related_person=parent,
        related_user=user,
        action_url=action_url,
        created_by=user,
        priority='normal'
    )

def notify_modification_proposed(person, user, field_name, old_value, new_value):
    """Notify admins when a modification is proposed"""
    title = f"Nouvelle proposition de modification"
    message = f"""
{user.get_full_name()} a proposé une modification pour {person.get_full_name()}:

• Champ: {field_name}
• Valeur actuelle: {old_value}
• Valeur proposée: {new_value}

Cette proposition nécessite votre approbation.
"""
    
    action_url = reverse('genealogy:person_detail', args=[person.id])
    
    return notify_admins(
        notification_type='modification_proposed',
        title=title,
        message=message,
        related_person=person,
        related_user=user,
        action_url=action_url,
        created_by=user,
        priority='high'
    )

def notify_proposal_reviewed(proposal, reviewer, approved=True):
    """Notify the proposer when their modification proposal is reviewed"""
    status = "approuvée" if approved else "rejetée"
    title = f"Proposition {status}"
    
    message = f"""
Votre proposition de modification pour {proposal.person.get_full_name()} a été {status} par {reviewer.get_full_name()}.

• Champ modifié: {proposal.field_name}
• Valeur proposée: {proposal.new_value}
"""
    
    if proposal.review_notes:
        message += f"\n• Notes de révision: {proposal.review_notes}"
    
    action_url = reverse('genealogy:person_detail', args=[proposal.person.id])
    notification_type = 'proposal_approved' if approved else 'proposal_rejected'
    priority = 'normal' if approved else 'high'
    
    return create_notification(
        recipients=[proposal.proposed_by],
        notification_type=notification_type,
        title=title,
        message=message,
        related_person=proposal.person,
        related_user=reviewer,
        related_proposal=proposal,
        action_url=action_url,
        created_by=reviewer,
        priority=priority
    )

# User management notifications
def notify_user_created(new_user, created_by):
    """Notify user when their account is created and notify admins"""
    # Notify the new user
    user_title = "Bienvenue dans la famille KANYAMUKENGE"
    user_message = f"""
Bonjour {new_user.get_full_name()},

Votre compte a été créé avec succès par {created_by.get_full_name()}.

• Email: {new_user.email}
• Rôle: {new_user.get_role_display()}

Vous pouvez maintenant explorer votre arbre généalogique familial.

Bienvenue dans la famille!
"""
    
    # Create notification for the new user
    user_notifications = create_notification(
        recipients=[new_user],
        notification_type='user_created',
        title=user_title,
        message=user_message,
        related_user=new_user,
        action_url=reverse('genealogy:dashboard'),
        created_by=created_by,
        priority='normal'
    )
    
    # Notify admins
    admin_title = f"Nouvel utilisateur créé - {new_user.get_full_name()}"
    admin_message = f"""
Un nouveau compte utilisateur a été créé par {created_by.get_full_name()}:

• Nom: {new_user.get_full_name()}
• Email: {new_user.email}
• Rôle: {new_user.get_role_display()}
"""
    
    admin_notifications = notify_admins(
        notification_type='user_created',
        title=admin_title,
        message=admin_message,
        related_user=new_user,
        created_by=created_by,
        priority='low'
    )
    
    return user_notifications + admin_notifications

def notify_user_deleted(user_name, user_email, deleted_by):
    """Notify admins when a user is deleted"""
    title = f"Utilisateur supprimé - {user_name}"
    message = f"""
L'utilisateur {user_name} ({user_email}) a été supprimé par {deleted_by.get_full_name()}.

Cette action ne peut pas être annulée.
"""
    
    return notify_admins(
        notification_type='user_deleted',
        title=title,
        message=message,
        related_user=deleted_by,
        created_by=deleted_by,
        priority='high'
    )

def notify_user_deactivated(user, deactivated_by):
    """Notify admins when a user is deactivated"""
    title = f"Utilisateur désactivé - {user.get_full_name()}"
    message = f"""
L'utilisateur {user.get_full_name()} ({user.email}) a été désactivé par {deactivated_by.get_full_name()}.

L'utilisateur ne peut plus se connecter jusqu'à réactivation.
"""
    
    return notify_admins(
        notification_type='user_deactivated',
        title=title,
        message=message,
        related_user=user,
        created_by=deactivated_by,
        priority='normal'
    )

# Utility functions
def mark_notifications_as_read(user, notification_ids=None):
    """Mark notifications as read for a user"""
    from .models import Notification
    
    queryset = Notification.objects.filter(recipient=user, is_read=False)
    
    if notification_ids:
        queryset = queryset.filter(id__in=notification_ids)
    
    updated = queryset.update(
        is_read=True,
        read_at=timezone.now()
    )
    
    logger.info(f"Marked {updated} notifications as read for user {user.get_full_name()}")
    return updated

def delete_expired_notifications():
    """Delete expired notifications (can be run as a management command)"""
    from .models import Notification
    
    expired_count = Notification.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()[0]
    
    logger.info(f"Deleted {expired_count} expired notifications")
    return expired_count

def get_unread_notifications_count(user):
    """Get count of unread notifications for a user"""
    from .models import Notification
    
    try:
        return Notification.objects.filter(recipient=user, is_read=False).count()
    except:
        return 0