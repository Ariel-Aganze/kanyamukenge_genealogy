from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import User, OTPToken, UserInvitation

class UserRegistrationForm(UserCreationForm):
    """Form for user registration via invitation"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Adresse email'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Prénom'
        })
    )
    last_name = forms.CharField(
        max_length=30,
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
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': "Nom d'utilisateur"
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Mot de passe'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Confirmer le mot de passe'
        })


class LoginForm(AuthenticationForm):
    """Custom login form with styling"""
    
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Adresse email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
            'placeholder': 'Mot de passe'
        })
    )


class AdminOTPForm(forms.Form):
    """Form for admin OTP verification"""
    
    otp_token = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent text-center text-2xl tracking-widest',
            'placeholder': '000000',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'autocomplete': 'one-time-code'
        })
    )
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_otp_token(self):
        token = self.cleaned_data.get('otp_token')
        if not token or len(token) != 6 or not token.isdigit():
            raise forms.ValidationError("Le code OTP doit contenir 6 chiffres.")
        
        if self.user:
            try:
                otp = OTPToken.objects.get(
                    user=self.user,
                    token=token,
                    is_used=False
                )
                if not otp.is_valid():
                    raise forms.ValidationError("Ce code OTP a expiré.")
            except OTPToken.DoesNotExist:
                raise forms.ValidationError("Code OTP invalide.")
        
        return token


class InvitationForm(forms.ModelForm):
    """Form for sending invitations to family members"""
    
    class Meta:
        model = UserInvitation
        fields = ['email', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent',
                'placeholder': 'Adresse email du membre à inviter'
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            })
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Un utilisateur avec cette adresse email existe déjà.")
        
        # Check if there's a pending invitation
        if UserInvitation.objects.filter(email=email, status='pending').exists():
            raise forms.ValidationError("Une invitation est déjà en attente pour cette adresse email.")
        
        return email


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-brand-border rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-transparent'
            }),
        }

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