"""
Email notification utilities for genealogy system
Provides email notifications for various genealogy actions
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

def get_base_url():
    """Get the base URL for the application"""
    return getattr(settings, 'BASE_URL', 'http://localhost:8000')

def get_admin_emails():
    """Get list of admin email addresses"""
    from accounts.models import User
    admin_users = User.objects.filter(role='admin', is_active=True)
    return [user.email for user in admin_users]

def send_admin_notification(subject, message, html_message=None):
    """Send notification to all admin users"""
    admin_emails = get_admin_emails()
    if not admin_emails:
        logger.warning("No admin emails found for notification")
        return False
    
    try:
        send_mail(
            subject=f"[Famille KANYAMUKENGE] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Admin notification sent: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send admin notification: {str(e)}")
        return False

def send_user_notification(user_email, subject, message, html_message=None):
    """Send notification to a specific user"""
    try:
        send_mail(
            subject=f"[Famille KANYAMUKENGE] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"User notification sent to {user_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send user notification to {user_email}: {str(e)}")
        return False

# Person-related notifications
def notify_person_created(person, user):
    """Notify admins when a new person is created"""
    subject = "Nouvelle personne ajoutée"
    message = f"""
Une nouvelle personne a été ajoutée au système généalogique:

Personne: {person.get_full_name()}
Date de naissance: {person.birth_date if person.birth_date else 'Non spécifiée'}
Lieu de naissance: {person.birth_place if person.birth_place else 'Non spécifié'}
Ajoutée par: {user.get_full_name()} ({user.email})

Voir la personne: {get_base_url()}{reverse('genealogy:person_detail', args=[person.id])}
"""
    
    html_message = f"""
<h3>Nouvelle personne ajoutée</h3>
<p>Une nouvelle personne a été ajoutée au système généalogique:</p>
<ul>
    <li><strong>Personne:</strong> {person.get_full_name()}</li>
    <li><strong>Date de naissance:</strong> {person.birth_date if person.birth_date else 'Non spécifiée'}</li>
    <li><strong>Lieu de naissance:</strong> {person.birth_place if person.birth_place else 'Non spécifié'}</li>
    <li><strong>Ajoutée par:</strong> {user.get_full_name()} ({user.email})</li>
</ul>
<p><a href="{get_base_url()}{reverse('genealogy:person_detail', args=[person.id])}">Voir la personne</a></p>
"""
    
    return send_admin_notification(subject, message, html_message)

def notify_person_edited(person, user, changed_fields=None):
    """Notify admins when a person's information is edited"""
    subject = "Informations d'une personne modifiées"
    
    changes_text = ""
    if changed_fields:
        changes_text = "\nChamps modifiés: " + ", ".join(changed_fields)
    
    message = f"""
Les informations d'une personne ont été modifiées:

Personne: {person.get_full_name()}
Modifiée par: {user.get_full_name()} ({user.email}){changes_text}

Voir la personne: {get_base_url()}{reverse('genealogy:person_detail', args=[person.id])}
"""
    
    html_message = f"""
<h3>Informations d'une personne modifiées</h3>
<p>Les informations d'une personne ont été modifiées:</p>
<ul>
    <li><strong>Personne:</strong> {person.get_full_name()}</li>
    <li><strong>Modifiée par:</strong> {user.get_full_name()} ({user.email})</li>
    {f'<li><strong>Champs modifiés:</strong> {", ".join(changed_fields)}</li>' if changed_fields else ''}
</ul>
<p><a href="{get_base_url()}{reverse('genealogy:person_detail', args=[person.id])}">Voir la personne</a></p>
"""
    
    return send_admin_notification(subject, message, html_message)

def notify_person_deleted(person_name, user):
    """Notify admins when a person is deleted"""
    subject = "Personne supprimée"
    message = f"""
Une personne a été supprimée du système généalogique:

Personne: {person_name}
Supprimée par: {user.get_full_name()} ({user.email})
"""
    
    html_message = f"""
<h3>Personne supprimée</h3>
<p>Une personne a été supprimée du système généalogique:</p>
<ul>
    <li><strong>Personne:</strong> {person_name}</li>
    <li><strong>Supprimée par:</strong> {user.get_full_name()} ({user.email})</li>
</ul>
"""
    
    return send_admin_notification(subject, message, html_message)

def notify_child_added(parent, child, user):
    """Notify admins when a child is added to a person"""
    subject = "Nouvelle relation parent-enfant"
    message = f"""
Une nouvelle relation parent-enfant a été ajoutée:

Parent: {parent.get_full_name()}
Enfant: {child.get_full_name()}
Ajoutée par: {user.get_full_name()} ({user.email})

Voir le parent: {get_base_url()}{reverse('genealogy:person_detail', args=[parent.id])}
Voir l'enfant: {get_base_url()}{reverse('genealogy:person_detail', args=[child.id])}
"""
    
    html_message = f"""
<h3>Nouvelle relation parent-enfant</h3>
<p>Une nouvelle relation parent-enfant a été ajoutée:</p>
<ul>
    <li><strong>Parent:</strong> {parent.get_full_name()}</li>
    <li><strong>Enfant:</strong> {child.get_full_name()}</li>
    <li><strong>Ajoutée par:</strong> {user.get_full_name()} ({user.email})</li>
</ul>
<p>
    <a href="{get_base_url()}{reverse('genealogy:person_detail', args=[parent.id])}">Voir le parent</a> | 
    <a href="{get_base_url()}{reverse('genealogy:person_detail', args=[child.id])}">Voir l'enfant</a>
</p>
"""
    
    return send_admin_notification(subject, message, html_message)

def notify_modification_proposed(person, user, field_name, old_value, new_value):
    """Notify admins when a modification is proposed"""
    subject = "Nouvelle proposition de modification"
    message = f"""
Une nouvelle proposition de modification a été soumise:

Personne: {person.get_full_name()}
Champ: {field_name}
Valeur actuelle: {old_value}
Valeur proposée: {new_value}
Proposée par: {user.get_full_name()} ({user.email})

Voir la personne: {get_base_url()}{reverse('genealogy:person_detail', args=[person.id])}
"""
    
    html_message = f"""
<h3>Nouvelle proposition de modification</h3>
<p>Une nouvelle proposition de modification a été soumise:</p>
<ul>
    <li><strong>Personne:</strong> {person.get_full_name()}</li>
    <li><strong>Champ:</strong> {field_name}</li>
    <li><strong>Valeur actuelle:</strong> {old_value}</li>
    <li><strong>Valeur proposée:</strong> {new_value}</li>
    <li><strong>Proposée par:</strong> {user.get_full_name()} ({user.email})</li>
</ul>
<p><a href="{get_base_url()}{reverse('genealogy:person_detail', args=[person.id])}">Voir la personne</a></p>
"""
    
    return send_admin_notification(subject, message, html_message)

# User management notifications
def notify_user_created(new_user, created_by):
    """Notify user when their account is created and notify admins"""
    # Notify the new user
    user_subject = "Bienvenue dans la famille KANYAMUKENGE"
    user_message = f"""
Bonjour {new_user.get_full_name()},

Votre compte a été créé avec succès sur la plateforme généalogique de la famille KANYAMUKENGE.

Informations de votre compte:
- Email: {new_user.email}
- Rôle: {new_user.get_role_display()}

Vous pouvez maintenant vous connecter et explorer votre arbre généalogique familial.

Connexion: {get_base_url()}/accounts/login/

Bienvenue dans la famille!
"""
    
    user_html_message = f"""
<h2>Bienvenue dans la famille KANYAMUKENGE</h2>
<p>Bonjour {new_user.get_full_name()},</p>
<p>Votre compte a été créé avec succès sur la plateforme généalogique de la famille KANYAMUKENGE.</p>

<h3>Informations de votre compte:</h3>
<ul>
    <li><strong>Email:</strong> {new_user.email}</li>
    <li><strong>Rôle:</strong> {new_user.get_role_display()}</li>
</ul>

<p>Vous pouvez maintenant vous connecter et explorer votre arbre généalogique familial.</p>
<p><a href="{get_base_url()}/accounts/login/">Se connecter</a></p>

<p><strong>Bienvenue dans la famille!</strong></p>
"""
    
    # Send welcome email to user
    user_notified = send_user_notification(new_user.email, user_subject, user_message, user_html_message)
    
    # Notify admins
    admin_subject = "Nouveau compte utilisateur créé"
    admin_message = f"""
Un nouveau compte utilisateur a été créé:

Utilisateur: {new_user.get_full_name()}
Email: {new_user.email}
Rôle: {new_user.get_role_display()}
Créé par: {created_by.get_full_name()} ({created_by.email})

Gérer les utilisateurs: {get_base_url()}{reverse('genealogy:manage_users')}
"""
    
    admin_html_message = f"""
<h3>Nouveau compte utilisateur créé</h3>
<p>Un nouveau compte utilisateur a été créé:</p>
<ul>
    <li><strong>Utilisateur:</strong> {new_user.get_full_name()}</li>
    <li><strong>Email:</strong> {new_user.email}</li>
    <li><strong>Rôle:</strong> {new_user.get_role_display()}</li>
    <li><strong>Créé par:</strong> {created_by.get_full_name()} ({created_by.email})</li>
</ul>
<p><a href="{get_base_url()}{reverse('genealogy:manage_users')}">Gérer les utilisateurs</a></p>
"""
    
    admin_notified = send_admin_notification(admin_subject, admin_message, admin_html_message)
    
    return user_notified and admin_notified

def notify_user_deleted(deleted_user_name, deleted_user_email, deleted_by):
    """Notify user when their account is deleted and notify admins"""
    # Notify the deleted user
    user_subject = "Votre compte a été supprimé"
    user_message = f"""
Bonjour {deleted_user_name},

Nous vous informons que votre compte sur la plateforme généalogique de la famille KANYAMUKENGE a été supprimé.

Si vous pensez qu'il s'agit d'une erreur, veuillez contacter l'administration à {settings.CONTACT_EMAIL}.

Cordialement,
L'équipe KANYAMUKENGE
"""
    
    user_html_message = f"""
<h2>Votre compte a été supprimé</h2>
<p>Bonjour {deleted_user_name},</p>
<p>Nous vous informons que votre compte sur la plateforme généalogique de la famille KANYAMUKENGE a été supprimé.</p>
<p>Si vous pensez qu'il s'agit d'une erreur, veuillez contacter l'administration à <a href="mailto:{settings.CONTACT_EMAIL}">{settings.CONTACT_EMAIL}</a>.</p>
<p>Cordialement,<br>L'équipe KANYAMUKENGE</p>
"""
    
    # Send notification to deleted user
    user_notified = send_user_notification(deleted_user_email, user_subject, user_message, user_html_message)
    
    # Notify admins
    admin_subject = "Compte utilisateur supprimé"
    admin_message = f"""
Un compte utilisateur a été supprimé:

Utilisateur: {deleted_user_name}
Email: {deleted_user_email}
Supprimé par: {deleted_by.get_full_name()} ({deleted_by.email})

Gérer les utilisateurs: {get_base_url()}{reverse('genealogy:manage_users')}
"""
    
    admin_html_message = f"""
<h3>Compte utilisateur supprimé</h3>
<p>Un compte utilisateur a été supprimé:</p>
<ul>
    <li><strong>Utilisateur:</strong> {deleted_user_name}</li>
    <li><strong>Email:</strong> {deleted_user_email}</li>
    <li><strong>Supprimé par:</strong> {deleted_by.get_full_name()} ({deleted_by.email})</li>
</ul>
<p><a href="{get_base_url()}{reverse('genealogy:manage_users')}">Gérer les utilisateurs</a></p>
"""
    
    admin_notified = send_admin_notification(admin_subject, admin_message, admin_html_message)
    
    return user_notified and admin_notified

def notify_user_deactivated(deactivated_user, deactivated_by):
    """Notify user when their account is deactivated"""
    # Notify the deactivated user
    user_subject = "Votre compte a été désactivé"
    user_message = f"""
Bonjour {deactivated_user.get_full_name()},

Nous vous informons que votre compte sur la plateforme généalogique de la famille KANYAMUKENGE a été temporairement désactivé.

Vous ne pourrez plus accéder à la plateforme jusqu'à ce que votre compte soit réactivé par un administrateur.

Pour toute question, veuillez contacter l'administration à {settings.CONTACT_EMAIL}.

Cordialement,
L'équipe KANYAMUKENGE
"""
    
    user_html_message = f"""
<h2>Votre compte a été désactivé</h2>
<p>Bonjour {deactivated_user.get_full_name()},</p>
<p>Nous vous informons que votre compte sur la plateforme généalogique de la famille KANYAMUKENGE a été temporairement désactivé.</p>
<p>Vous ne pourrez plus accéder à la plateforme jusqu'à ce que votre compte soit réactivé par un administrateur.</p>
<p>Pour toute question, veuillez contacter l'administration à <a href="mailto:{settings.CONTACT_EMAIL}">{settings.CONTACT_EMAIL}</a>.</p>
<p>Cordialement,<br>L'équipe KANYAMUKENGE</p>
"""
    
    # Send notification to deactivated user
    user_notified = send_user_notification(deactivated_user.email, user_subject, user_message, user_html_message)
    
    # Notify admins
    admin_subject = "Compte utilisateur désactivé"
    admin_message = f"""
Un compte utilisateur a été désactivé:

Utilisateur: {deactivated_user.get_full_name()}
Email: {deactivated_user.email}
Désactivé par: {deactivated_by.get_full_name()} ({deactivated_by.email})

Gérer les utilisateurs: {get_base_url()}{reverse('genealogy:manage_users')}
"""
    
    admin_html_message = f"""
<h3>Compte utilisateur désactivé</h3>
<p>Un compte utilisateur a été désactivé:</p>
<ul>
    <li><strong>Utilisateur:</strong> {deactivated_user.get_full_name()}</li>
    <li><strong>Email:</strong> {deactivated_user.email}</li>
    <li><strong>Désactivé par:</strong> {deactivated_by.get_full_name()} ({deactivated_by.email})</li>
</ul>
<p><a href="{get_base_url()}{reverse('genealogy:manage_users')}">Gérer les utilisateurs</a></p>
"""
    
    admin_notified = send_admin_notification(admin_subject, admin_message, admin_html_message)
    
    return user_notified and admin_notified