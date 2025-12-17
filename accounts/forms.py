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