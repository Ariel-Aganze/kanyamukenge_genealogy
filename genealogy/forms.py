from django import forms
from django.contrib.auth import get_user_model
from .models import Person, Partnership, ParentChild, ModificationProposal, FamilyEvent, Document

User = get_user_model()

class PersonForm(forms.ModelForm):
    """Form for creating/editing person information"""
    
    class Meta:
        model = Person
        fields = [
            'first_name', 'last_name', 'maiden_name', 'gender',
            'birth_date', 'birth_place', 'death_date', 'death_place',
            'biography', 'profession', 'education', 'photo', 'visibility'
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
            'birth_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'type': 'date'
            }),
            'birth_place': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Lieu de naissance'
            }),
            'death_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'type': 'date'
            }),
            'death_place': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Lieu de décès'
            }),
            'biography': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 4,
                'placeholder': 'Biographie, histoire de vie, anecdotes...'
            }),
            'profession': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Profession'
            }),
            'education': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 3,
                'placeholder': 'Formation, éducation...'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'visibility': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        birth_date = cleaned_data.get('birth_date')
        death_date = cleaned_data.get('death_date')
        
        if birth_date and death_date and birth_date >= death_date:
            raise forms.ValidationError("La date de naissance doit être antérieure à la date de décès.")
        
        return cleaned_data


class PartnershipForm(forms.ModelForm):
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
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        # ✅ Extraire person1 AVANT d'appeler super()
        self.person1 = kwargs.pop('person1', None)
        
        super().__init__(*args, **kwargs)
        
        # ✅ Filtrer les choix pour person2 (exclure person1 si fourni)
        if self.person1:
            # Exclure la personne elle-même des choix
            self.fields['person2'].queryset = Person.objects.exclude(id=self.person1.id)
        
        # ✅ Personnaliser les choix pour person2
        self.fields['person2'].queryset = Person.objects.all().order_by('first_name', 'last_name')
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
        # FIXED: Proper parameter handling
        super().__init__(*args, **kwargs)
        self.parent = parent
        
        if parent:
            # Exclude parent from child choices and existing children
            existing_children = [rel.child.id for rel in ParentChild.objects.filter(parent=parent)]
            self.fields['child'].queryset = Person.objects.exclude(
                id__in=[parent.id] + existing_children
            ).order_by('first_name', 'last_name')
            self.fields['child'].empty_label = "Sélectionner un enfant"


class ModificationProposalForm(forms.ModelForm):
    """Form for proposing modifications to person data"""
    
    FIELD_CHOICES = [
        ('first_name', 'Prénom'),
        ('last_name', 'Nom de famille'),
        ('maiden_name', 'Nom de jeune fille'),
        ('birth_date', 'Date de naissance'),
        ('birth_place', 'Lieu de naissance'),
        ('death_date', 'Date de décès'),
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
            'new_value': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 3,
                'placeholder': 'Nouvelle valeur...'
            }),
            'justification': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'rows': 4,
                'placeholder': 'Justification de la modification, sources...'
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
            'placeholder': 'Rechercher une personne...'
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
        choices=[('', 'Tous'), ('True', 'Décédés'), ('False', 'Vivants')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
        })
    )