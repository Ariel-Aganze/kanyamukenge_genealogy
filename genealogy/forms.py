from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError

from accounts.models import User
from .models import Person, Partnership, ParentChild, ModificationProposal, FamilyEvent, Document
from django.contrib.auth.forms import UserCreationForm



class PersonForm(forms.ModelForm):
    """Form for creating and editing people - UPDATED WITH TRIBUS AND CLAN"""
    
    class Meta:
        model = Person
        fields = [
            'first_name', 'last_name', 'maiden_name', 'gender',
            'tribus', 'clan',  # NEW FIELDS
            'birth_date', 'birth_place', 'death_date', 'death_place',
            'profession', 'education', 'biography', 'photo', 'visibility'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Nom de famille'
            }),
            'maiden_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Nom de jeune fille (optionnel)'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            # NEW FIELDS - Tribus and Clan widgets
            'tribus': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Tribu (optionnel)'
            }),
            'clan': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Clan (optionnel)'
            }),
            # FIXED: Proper date input configuration
            'birth_date': forms.DateInput(
                attrs={
                    'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                    'type': 'date'
                },
                format='%Y-%m-%d'
            ),
            'death_date': forms.DateInput(
                attrs={
                    'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                    'type': 'date'
                },
                format='%Y-%m-%d'
            ),
            'birth_place': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Lieu de naissance'
            }),
            'death_place': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Lieu de décès'
            }),
            'profession': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Profession'
            }),
            'education': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 3,
                'placeholder': 'Formation, éducation, diplômes...'
            }),
            'biography': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 4,
                'placeholder': 'Biographie, histoire de vie, anecdotes...'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'accept': 'image/*'
            }),
            'visibility': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set date input format
        self.fields['birth_date'].input_formats = ['%Y-%m-%d']
        self.fields['death_date'].input_formats = ['%Y-%m-%d']
        
        # Handle date field values properly
        if self.instance and self.instance.pk:
            if self.instance.birth_date:
                self.initial['birth_date'] = self.instance.birth_date.strftime('%Y-%m-%d')
            if self.instance.death_date:
                self.initial['death_date'] = self.instance.death_date.strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        birth_date = cleaned_data.get('birth_date')
        death_date = cleaned_data.get('death_date')
        
        # Validate that birth date is not in the future
        if birth_date:
            from datetime import date
            if birth_date > date.today():
                raise ValidationError({
                    'birth_date': 'La date de naissance ne peut pas être dans le futur.'
                })
        
        # Validate that death date is after birth date
        if birth_date and death_date:
            if death_date <= birth_date:
                raise ValidationError({
                    'death_date': 'La date de décès doit être postérieure à la date de naissance.'
                })
        
        # Validate death date is not in the future
        if death_date:
            from datetime import date
            if death_date > date.today():
                raise ValidationError({
                    'death_date': 'La date de décès ne peut pas être dans le futur.'
                })
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Auto-set is_deceased based on death_date
        if instance.death_date:
            instance.is_deceased = True
        else:
            instance.is_deceased = False
        
        if commit:
            instance.save()
        
        return instance


class PartnershipForm(forms.ModelForm):
    """Form for creating partnerships/marriages"""
    
    class Meta:
        model = Partnership
        fields = ['person2', 'partnership_type', 'start_date', 'end_date', 'location', 'notes']
        widgets = {
            'person2': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'partnership_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'type': 'date'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Lieu du mariage/union'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 3,
                'placeholder': 'Notes additionnelles...'
            })
        }

    def __init__(self, *args, person1=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.person1 = person1
        
        if person1:
            # Exclude person1 from partner choices
            self.fields['person2'].queryset = Person.objects.exclude(id=person1.id).order_by('first_name', 'last_name')
            self.fields['person2'].empty_label = "Sélectionner un conjoint"


class ParentChildForm(forms.ModelForm):
    """Form for creating parent-child relationships"""
    
    class Meta:
        model = ParentChild
        fields = ['child', 'relationship_type', 'notes']
        widgets = {
            'child': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'relationship_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 3,
                'placeholder': 'Notes additionnelles...'
            })
        }

    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        
        if parent:
            # Exclude parent from child choices and existing children
            existing_children_ids = list(ParentChild.objects.filter(
                parent=parent
            ).values_list('child_id', flat=True))
            
            # Also exclude the parent themselves
            excluded_ids = [parent.id] + existing_children_ids
            
            self.fields['child'].queryset = Person.objects.exclude(
                id__in=excluded_ids
            ).order_by('first_name', 'last_name')
            self.fields['child'].empty_label = "Sélectionner un enfant"
            
            # Add helpful labels
            self.fields['child'].help_text = f"Sélectionnez l'enfant à ajouter à {parent.get_full_name()}"
            
    def clean(self):
        cleaned_data = super().clean()
        child = cleaned_data.get('child')
        
        if self.parent and child:
            # Check if the child is the same as the parent
            if child.id == self.parent.id:
                raise forms.ValidationError("Une personne ne peut pas être son propre parent.")
            
            # Check if relationship already exists
            if ParentChild.objects.filter(parent=self.parent, child=child).exists():
                raise forms.ValidationError(f"{child.get_full_name()} est déjà enregistré(e) comme enfant de {self.parent.get_full_name()}.")
            
            # Check age logic if birth dates exist
            if self.parent.birth_date and child.birth_date:
                parent_birth = self.parent.birth_date
                child_birth = child.birth_date
                
                if parent_birth >= child_birth:
                    raise forms.ValidationError("Le parent doit être né avant l'enfant.")
                
                # Check reasonable age difference (at least 10 years)
                age_diff = (child_birth - parent_birth).days / 365.25
                if age_diff < 10:
                    raise forms.ValidationError("L'écart d'âge entre parent et enfant semble trop petit (moins de 10 ans).")
        
        return cleaned_data


class ModificationProposalForm(forms.ModelForm):
    """Form for proposing modifications to person data"""
    
    FIELD_CHOICES = [
        ('first_name', 'Prénom'),
        ('last_name', 'Nom de famille'),
        ('maiden_name', 'Nom de jeune fille'),
        ('birth_date', 'Date de naissance'),
        ('death_date', 'Date de décès'),
        ('birth_place', 'Lieu de naissance'),
        ('death_place', 'Lieu de décès'),
        ('profession', 'Profession'),
        ('biography', 'Biographie'),
    ]
    
    field_name = forms.ChoiceField(
        choices=FIELD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
        })
    )
    
    class Meta:
        model = ModificationProposal
        fields = ['field_name', 'new_value', 'justification']
        widgets = {
            'new_value': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Nouvelle valeur'
            }),
            'justification': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 3,
                'placeholder': 'Justification de la modification...'
            })
        }


class FamilyEventForm(forms.ModelForm):
    """Form for creating family events"""
    
    class Meta:
        model = FamilyEvent
        fields = ['title', 'event_type', 'date', 'location', 'description', 'people']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Titre de l\'événement'
            }),
            'event_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'type': 'date'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Lieu de l\'événement'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 4,
                'placeholder': 'Description de l\'événement...'
            }),
            'people': forms.CheckboxSelectMultiple(attrs={
                'class': 'space-y-2'
            })
        }


class DocumentForm(forms.ModelForm):
    """Form for uploading documents"""
    
    class Meta:
        model = Document
        fields = ['title', 'document_type', 'file', 'description', 'people']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Titre du document'
            }),
            'document_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 3,
                'placeholder': 'Description du document...'
            }),
            'people': forms.CheckboxSelectMultiple(attrs={
                'class': 'space-y-2'
            })
        }


class SearchForm(forms.Form):
    """Form for searching people in the family tree"""
    
    query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Nom, prénom, lieu...'
        })
    )
    
    birth_year_from = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Année de naissance (de)'
        })
    )
    
    birth_year_to = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Année de naissance (à)'
        })
    )
    
    gender = forms.ChoiceField(
        choices=[('', 'Tous')] + Person.GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
        })
    )
    
    is_deceased = forms.ChoiceField(
        choices=[
            ('', 'Tous'),
            ('False', 'Vivants'),
            ('True', 'Décédés'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
        })
    )

class DirectUserCreationForm(UserCreationForm):
    """Form for direct user creation by admins (no invitation email)"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Adresse email'
        }),
        help_text="Adresse email unique pour ce membre de la famille"
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Prénom'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Nom de famille'
        })
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Numéro de téléphone (optionnel)'
        }),
        help_text="Numéro de téléphone pour contact (optionnel)"
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        initial='member',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
        }),
        help_text="Rôle de l'utilisateur dans le système"
    )
    
    # Genealogy Permissions
    can_add_children = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-brand-primary focus:ring-brand-primary'
        }),
        label="Peut ajouter des enfants",
        help_text="Autoriser l'utilisateur à ajouter des relations parent-enfant"
    )
    
    can_modify_own_info = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-brand-primary focus:ring-brand-primary'
        }),
        label="Peut modifier ses propres informations",
        help_text="Autoriser l'utilisateur à modifier son profil et ses informations"
    )
    
    can_view_private_info = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-brand-primary focus:ring-brand-primary'
        }),
        label="Peut voir les informations privées",
        help_text="Autoriser l'utilisateur à voir les informations privées d'autres membres"
    )
    
    can_export_data = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-brand-primary focus:ring-brand-primary'
        }),
        label="Peut exporter les données",
        help_text="Autoriser l'utilisateur à exporter les données généalogiques"
    )
    
    is_verified = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-brand-primary focus:ring-brand-primary'
        }),
        label="Compte vérifié",
        help_text="Marquer le compte comme vérifié dès la création"
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'phone_number', 
            'role', 'password1', 'password2', 'can_add_children', 
            'can_modify_own_info', 'can_view_private_info', 'can_export_data', 
            'is_verified'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Style password fields
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': "Nom d'utilisateur unique"
        })
        self.fields['username'].help_text = "Nom d'utilisateur unique pour la connexion"
        
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Mot de passe'
        })
        self.fields['password1'].help_text = "Le mot de passe doit contenir au moins 8 caractères"
        
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Confirmer le mot de passe'
        })
        self.fields['password2'].help_text = "Retapez le même mot de passe pour confirmation"

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Un utilisateur avec cette adresse email existe déjà.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Set additional fields
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.role = self.cleaned_data['role']
        user.is_verified = self.cleaned_data.get('is_verified', True)
        
        # Set genealogy permissions
        user.can_add_children = self.cleaned_data.get('can_add_children', True)
        user.can_modify_own_info = self.cleaned_data.get('can_modify_own_info', True)
        user.can_view_private_info = self.cleaned_data.get('can_view_private_info', False)
        user.can_export_data = self.cleaned_data.get('can_export_data', False)
        
        # Activate the user immediately
        user.is_active = True
        
        if commit:
            user.save()
        
        return user