from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from PIL import Image
import os

User = get_user_model()

class Person(models.Model):
    """Model representing a person in the family tree"""
    
    GENDER_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
        ('O', 'Autre'),
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('family', 'Famille seulement'),
        ('private', 'Privé'),
    ]
    
    # Basic Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    maiden_name = models.CharField(max_length=100, blank=True, null=True, help_text="Nom de jeune fille")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    tribus = models.CharField(max_length=100, blank=True, null=True, help_text="Tribu d'appartenance")
    clan = models.CharField(max_length=100, blank=True, null=True, help_text="Clan d'appartenance")
    
    # Dates
    birth_date = models.DateField(null=True, blank=True)
    death_date = models.DateField(null=True, blank=True)
    birth_place = models.CharField(max_length=200, blank=True, null=True)
    death_place = models.CharField(max_length=200, blank=True, null=True)
    
    # Additional Information
    biography = models.TextField(blank=True, null=True, help_text="Histoire de vie, anecdotes, souvenirs")
    profession = models.CharField(max_length=100, blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    
    # Photo
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    
    # System fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_people')
    owned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='owned_people')
    user_account = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='person')
    
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='family')
    is_deceased = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'genealogy_person'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['birth_date']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        try:
            full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
            if not full_name:
                full_name = "Nom non défini"
            if self.maiden_name:
                full_name += f" (née {self.maiden_name})"
            return full_name
        except:
            return f"Person #{self.pk}" if self.pk else "Nouvelle personne"
    
    def get_full_name(self):
        """Get full name safely"""
        return str(self)
    
    def get_age(self):
        """Calculate age of person safely"""
        # ✅ Vérification que birth_date existe
        if not self.birth_date:
            return None
        
        try:
            # ✅ Déterminer la date de fin (décès ou aujourd'hui)
            if self.is_deceased and self.death_date:
                end_date = self.death_date
            else:
                end_date = timezone.now().date()
            
            # ✅ Calculer l'âge
            age = end_date.year - self.birth_date.year
            
            # ✅ Ajuster si l'anniversaire n'est pas encore passé
            if (end_date.month, end_date.day) < (self.birth_date.month, self.birth_date.day):
                age -= 1
            
            # ✅ Retourner seulement des âges positifs
            return age if age >= 0 else None
            
        except (AttributeError, TypeError, ValueError):
            return None
    
    def get_birth_year(self):
        """Get birth year safely"""
        try:
            return self.birth_date.year if self.birth_date else None
        except (AttributeError, TypeError):
            return None
    
    def get_death_year(self):
        """Get death year safely"""
        try:
            return self.death_date.year if self.death_date else None
        except (AttributeError, TypeError):
            return None
    
    def get_parents(self):
        """Get parents of this person"""
        try:
            # Éviter l'import circulaire
            from .models import ParentChild
            parent_relations = ParentChild.objects.filter(child=self, status='confirmed')
            return [rel.parent for rel in parent_relations if rel.parent]
        except:
            return []
    
    def get_children(self):
        """Get children of this person"""
        try:
            from .models import ParentChild
            child_relations = ParentChild.objects.filter(parent=self, status='confirmed')
            return [rel.child for rel in child_relations if rel.child]
        except:
            return []
    
    def get_partners(self):
        """Get partners/spouses of this person"""
        try:
            from .models import Partnership
            partnerships = Partnership.objects.filter(
                models.Q(person1=self) | models.Q(person2=self),
                status='confirmed'
            )
            partners = []
            for partnership in partnerships:
                if partnership.person1_id == self.id and partnership.person2:
                    partners.append(partnership.person2)
                elif partnership.person2_id == self.id and partnership.person1:
                    partners.append(partnership.person1)
            return partners
        except:
            return []
    
    def get_siblings(self):
        """Get siblings of this person"""
        try:
            parents = self.get_parents()
            if not parents:
                return []
            
            siblings = set()
            for parent in parents:
                children = parent.get_children()
                for child in children:
                    if child.id != self.id:
                        siblings.add(child)
            
            return list(siblings)
        except:
            return []
    
    def can_be_modified_by(self, user):
        """Check if user can modify this person"""
        if not user or not user.is_authenticated:
            return False
        
        try:
            # Admin a tous les droits
            if hasattr(user, 'role') and user.role == 'admin':
                return True
            
            # Propriétaire de la fiche
            if self.owned_by_id == user.id:
                return True
            
            # Créateur de la fiche
            if self.created_by_id == user.id:
                return True
            
            # La personne elle-même (si elle a un compte)
            if self.user_account_id == user.id:
                return True
            
            return False
        except:
            return False
    
    def save(self, *args, **kwargs):
        """Save with additional logic"""
        try:
            # ✅ Auto-set is_deceased if death_date is provided
            if self.death_date:
                self.is_deceased = True
            elif not self.death_date:
                self.is_deceased = False
            
            super().save(*args, **kwargs)
            
            # ✅ Resize photo if needed (with error handling)
            if self.photo:
                try:
                    self.resize_photo()
                except Exception as e:
                    # Log l'erreur mais ne pas empêcher la sauvegarde
                    print(f"Erreur lors du redimensionnement de la photo: {e}")
                    
        except Exception as e:
            # Re-lancer l'erreur pour les erreurs critiques de sauvegarde
            raise e
    
    def resize_photo(self):
        """Resize photo to reasonable dimensions"""
        try:
            if self.photo and hasattr(self.photo, 'path') and os.path.exists(self.photo.path):
                # Importer PIL avec gestion d'erreur
                try:
                    from PIL import Image
                except ImportError:
                    print("PIL non disponible, redimensionnement ignoré")
                    return
                
                img = Image.open(self.photo.path)
                
                # Resize to max 800x800 while maintaining aspect ratio
                if img.height > 800 or img.width > 800:
                    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                    img.save(self.photo.path, optimize=True, quality=85)
                    
        except Exception as e:
            print(f"Erreur lors du redimensionnement: {e}")
    
    def is_alive(self):
        """Check if person is alive"""
        return not self.is_deceased
    
    def get_age_display(self):
        """Get formatted age for display"""
        age = self.get_age()
        if age is None:
            return "Âge inconnu"
        elif self.is_deceased:
            return f"{age} ans (au décès)"
        else:
            return f"{age} ans"
    
    def get_lifespan_display(self):
        """Get formatted lifespan for display"""
        birth_year = self.get_birth_year()
        death_year = self.get_death_year()
        
        if birth_year and death_year:
            return f"{birth_year} - {death_year}"
        elif birth_year:
            return f"Né en {birth_year}" + ("" if not self.is_deceased else " - ?")
        else:
            return "Dates inconnues"


class Partnership(models.Model):
    """Model representing marriage or partnership between two people"""
    
    PARTNERSHIP_TYPE_CHOICES = [
        ('marriage', 'Mariage'),
        ('partnership', 'Union libre'),
        ('engagement', 'Fiançailles'),
    ]
    
    STATUS_CHOICES = [
        ('proposed', 'Proposé'),
        ('confirmed', 'Confirmé'),
        ('rejected', 'Rejeté'),
    ]
    
    person1 = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='partnerships_as_person1')
    person2 = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='partnerships_as_person2')
    
    partnership_type = models.CharField(max_length=20, choices=PARTNERSHIP_TYPE_CHOICES, default='marriage')
    start_date = models.DateField(null=True, blank=True, help_text="Date de mariage ou début de l'union")
    end_date = models.DateField(null=True, blank=True, help_text="Date de divorce ou fin de l'union")
    location = models.CharField(max_length=200, blank=True, null=True, help_text="Lieu de mariage")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'genealogy_partnership'
        unique_together = [['person1', 'person2']]
    
    def __str__(self):
        # ✅ CORRECTION : Vérifier que les personnes existent avant de les afficher
        try:
            person1_name = str(self.person1) if self.person1_id else "Non défini"
            person2_name = str(self.person2) if self.person2_id else "Non défini"
            return f"{person1_name} & {person2_name} ({self.partnership_type})"
        except:
            return f"Partnership #{self.pk}" if self.pk else "Nouvelle union"
    
    def clean(self):
        """Validate partnership"""
        from django.core.exceptions import ValidationError
        
        if not self.person1_id or not self.person2_id:
            return
        
        if self.person1_id == self.person2_id:
            raise ValidationError("Une personne ne peut pas être en union avec elle-même.")
        
        if self.person1_id and self.person2_id and self.person1_id > self.person2_id:
            self.person1_id, self.person2_id = self.person2_id, self.person1_id
    
    def save(self, *args, **kwargs):
        if self.person1_id and self.person2_id:
            self.clean()
        super().save(*args, **kwargs)


class ParentChild(models.Model):
    """Model representing parent-child relationship"""
    
    RELATIONSHIP_TYPE_CHOICES = [
        ('biological', 'Biologique'),
        ('adopted', 'Adopté'),
        ('stepchild', 'Beau-fils/Belle-fille'),
        ('foster', 'Famille d\'accueil'),
    ]
    
    STATUS_CHOICES = [
        ('proposed', 'Proposé'),
        ('confirmed', 'Confirmé'),
        ('rejected', 'Rejeté'),
    ]
    
    parent = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='children_relationships')
    child = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='parent_relationships')
    
    relationship_type = models.CharField(max_length=20, choices=RELATIONSHIP_TYPE_CHOICES, default='biological')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'genealogy_parent_child'
        unique_together = [['parent', 'child']]
    
    def __str__(self):
        return f"{self.parent} -> {self.child} ({self.relationship_type})"
    
    def clean(self):
        """Validate parent-child relationship"""
        from django.core.exceptions import ValidationError
    
        # FIXED: Use parent_id and child_id instead of parent and child objects
        if hasattr(self, 'parent_id') and hasattr(self, 'child_id'):
            if self.parent_id and self.child_id and self.parent_id == self.child_id:
                raise ValidationError("Une personne ne peut pas être son propre parent.")
    
        # Only check age if we can safely access the parent and child objects
        try:
            if (self.parent_id and self.child_id and 
                hasattr(self, '_parent_cache') and hasattr(self, '_child_cache') and
                self.parent.birth_date and self.child.birth_date):
                if self.parent.birth_date >= self.child.birth_date:
                    raise ValidationError("Le parent doit être né avant l'enfant.")
        except:
            # Skip age validation if we can't access the objects safely
            pass
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class ModificationProposal(models.Model):
    """Model for tracking proposed modifications to person data"""
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='modification_proposals')
    proposed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proposed_modifications')
    
    field_name = models.CharField(max_length=50, help_text="Nom du champ à modifier")
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField()
    justification = models.TextField(help_text="Justification de la modification")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_modifications')
    review_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'genealogy_modification_proposal'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Modification de {self.field_name} pour {self.person} par {self.proposed_by}"


class FamilyEvent(models.Model):
    """Model for family events (births, deaths, marriages, etc.)"""
    
    EVENT_TYPE_CHOICES = [
        ('birth', 'Naissance'),
        ('death', 'Décès'),
        ('marriage', 'Mariage'),
        ('divorce', 'Divorce'),
        ('baptism', 'Baptême'),
        ('graduation', 'Diplôme'),
        ('other', 'Autre'),
    ]
    
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # People involved in the event
    people = models.ManyToManyField(Person, related_name='events')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'genealogy_family_event'
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.event_type})"


class Document(models.Model):
    """Model for storing family documents and photos"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('birth_certificate', 'Acte de naissance'),
        ('death_certificate', 'Acte de décès'),
        ('marriage_certificate', 'Acte de mariage'),
        ('photo', 'Photo'),
        ('document', 'Document'),
        ('other', 'Autre'),
    ]
    
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='documents/')
    description = models.TextField(blank=True, null=True)
    
    # People related to this document
    people = models.ManyToManyField(Person, related_name='documents', blank=True)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'genealogy_document'
        ordering = ['-upload_date']
    
    def __str__(self):
        return self.title


class AuditLog(models.Model):
    """Model for tracking all system changes"""
    
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('approve', 'Approbation'),
        ('reject', 'Rejet'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'genealogy_audit_log'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} {self.action} {self.model_name} at {self.timestamp}"


class Notification(models.Model):
    """Model for in-app notifications to replace email notifications"""
    
    NOTIFICATION_TYPES = [
        ('person_created', 'Nouvelle personne ajoutée'),
        ('person_edited', 'Personne modifiée'),
        ('person_deleted', 'Personne supprimée'),
        ('child_added', 'Relation parent-enfant ajoutée'),
        ('modification_proposed', 'Proposition de modification'),
        ('proposal_approved', 'Proposition approuvée'),
        ('proposal_rejected', 'Proposition rejetée'),
        ('user_created', 'Nouvel utilisateur créé'),
        ('user_deleted', 'Utilisateur supprimé'),
        ('user_deactivated', 'Utilisateur désactivé'),
        ('partnership_created', 'Nouveau partenariat'),
        ('system_alert', 'Alerte système'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Faible'),
        ('normal', 'Normal'),
        ('high', 'Élevé'),
        ('urgent', 'Urgent'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Optional related objects
    related_person = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True)
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='related_notifications')
    related_proposal = models.ForeignKey('ModificationProposal', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Metadata
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # URLs for navigation
    action_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL to navigate when notification is clicked")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When notification should be automatically deleted")
    
    # Creator information
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_notifications')
    
    class Meta:
        db_table = 'genealogy_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def get_icon(self):
        """Get appropriate icon for notification type"""
        icon_map = {
            'person_created': 'user-plus',
            'person_edited': 'edit-3',
            'person_deleted': 'user-minus',
            'child_added': 'users',
            'modification_proposed': 'edit-2',
            'proposal_approved': 'check-circle',
            'proposal_rejected': 'x-circle',
            'user_created': 'user-plus',
            'user_deleted': 'user-minus',
            'user_deactivated': 'user-x',
            'partnership_created': 'heart',
            'system_alert': 'alert-triangle',
        }
        return icon_map.get(self.notification_type, 'bell')
    
    def get_color_class(self):
        """Get appropriate color class for notification type"""
        color_map = {
            'person_created': 'bg-green-100 text-green-600',
            'person_edited': 'bg-blue-100 text-blue-600',
            'person_deleted': 'bg-red-100 text-red-600',
            'child_added': 'bg-purple-100 text-purple-600',
            'modification_proposed': 'bg-yellow-100 text-yellow-600',
            'proposal_approved': 'bg-green-100 text-green-600',
            'proposal_rejected': 'bg-red-100 text-red-600',
            'user_created': 'bg-blue-100 text-blue-600',
            'user_deleted': 'bg-red-100 text-red-600',
            'user_deactivated': 'bg-orange-100 text-orange-600',
            'partnership_created': 'bg-pink-100 text-pink-600',
            'system_alert': 'bg-yellow-100 text-yellow-600',
        }
        return color_map.get(self.notification_type, 'bg-gray-100 text-gray-600')
    
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False