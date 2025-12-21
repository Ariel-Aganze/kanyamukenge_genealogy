from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import Person, Partnership, ParentChild, ModificationProposal, FamilyEvent, Document


class PersonForm(forms.ModelForm):
    """Form for creating and editing people - FIXED DATE HANDLING"""
    
    class Meta:
        model = Person
        fields = [
            'first_name', 'last_name', 'maiden_name', 'gender',
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
            # FIXED: Proper date input configuration
            'birth_date': forms.DateInput(
                attrs={
                    'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                    'type': 'date',
                    'placeholder': 'YYYY-MM-DD'
                },
                format='%Y-%m-%d'  # IMPORTANT: This ensures proper date formatting
            ),
            'birth_place': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Lieu de naissance'
            }),
            # FIXED: Proper date input configuration
            'death_date': forms.DateInput(
                attrs={
                    'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                    'type': 'date',
                    'placeholder': 'YYYY-MM-DD'
                },
                format='%Y-%m-%d'  # IMPORTANT: This ensures proper date formatting
            ),
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
                'placeholder': 'Éducation et formation...'
            }),
            'biography': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 4,
                'placeholder': 'Biographie, histoire de vie, anecdotes...'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'hidden',  # Hidden since we use drag & drop
                'accept': 'image/*'
            }),
            'visibility': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            })
        }

    # IMPORTANT: Override __init__ to handle date formatting properly
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set input formats for date fields to handle both input and display
        self.fields['birth_date'].input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
        self.fields['death_date'].input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
        
        # If we have an instance (editing), ensure dates are properly formatted
        if self.instance and self.instance.pk:
            if self.instance.birth_date:
                self.fields['birth_date'].widget.attrs['value'] = self.instance.birth_date.strftime('%Y-%m-%d')
            if self.instance.death_date:
                self.fields['death_date'].widget.attrs['value'] = self.instance.death_date.strftime('%Y-%m-%d')
    
    def clean(self):
        cleaned_data = super().clean()
        birth_date = cleaned_data.get('birth_date')
        death_date = cleaned_data.get('death_date')
        
        # Validate dates
        if birth_date and death_date:
            if death_date <= birth_date:
                raise ValidationError({
                    'death_date': 'La date de décès doit être postérieure à la date de naissance.'
                })
        
        # Validate birth date is not in the future
        if birth_date:
            from datetime import date
            if birth_date > date.today():
                raise ValidationError({
                    'birth_date': 'La date de naissance ne peut pas être dans le futur.'
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