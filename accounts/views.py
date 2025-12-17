from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponseRedirect
from .models import User, OTPToken, UserInvitation
from .forms import (
    UserRegistrationForm, LoginForm, AdminOTPForm, 
    InvitationForm, ProfileUpdateForm
)

def login_view(request):
    """Handle user login with OTP for admins"""
    if request.user.is_authenticated:
        return redirect('genealogy:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Check if user is admin - require OTP
            if user.role == 'admin':
                # Generate and send OTP
                otp = OTPToken.objects.create(user=user)
                send_otp_email(user, otp.token)
                
                # Store user ID in session for OTP verification
                request.session['otp_user_id'] = user.id
                messages.success(request, 'Un code de vérification a été envoyé à votre email.')
                return redirect('accounts:otp_verify')
            else:
                # Regular login for non-admin users
                login(request, user)
                return redirect('genealogy:dashboard')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def otp_verify(request):
    """Verify OTP for admin users"""
    user_id = request.session.get('otp_user_id')
    if not user_id:
        messages.error(request, 'Session expirée. Veuillez vous reconnecter.')
        return redirect('accounts:login')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = AdminOTPForm(user=user, data=request.POST)
        if form.is_valid():
            token = form.cleaned_data['otp_token']
            
            try:
                otp = OTPToken.objects.get(
                    user=user,
                    token=token,
                    is_used=False
                )
                
                if otp.is_valid():
                    # Mark OTP as used
                    otp.is_used = True
                    otp.save()
                    
                    # Clear session
                    del request.session['otp_user_id']
                    
                    # Login user
                    login(request, user)
                    messages.success(request, 'Connexion réussie.')
                    return redirect('genealogy:dashboard')
                else:
                    messages.error(request, 'Le code OTP a expiré.')
            except OTPToken.DoesNotExist:
                messages.error(request, 'Code OTP invalide.')
    else:
        form = AdminOTPForm(user=user)
    
    return render(request, 'accounts/otp_verify.html', {
        'form': form,
        'user': user
    })


def resend_otp(request):
    """Resend OTP code to admin user"""
    user_id = request.session.get('otp_user_id')
    if not user_id:
        messages.error(request, 'Session expirée. Veuillez vous reconnecter.')
        return redirect('accounts:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Invalidate old OTP tokens
    OTPToken.objects.filter(user=user, is_used=False).update(is_used=True)
    
    # Generate new OTP
    otp = OTPToken.objects.create(user=user)
    send_otp_email(user, otp.token)
    
    messages.success(request, 'Un nouveau code de vérification a été envoyé.')
    return redirect('accounts:otp_verify')


def register(request, token):
    """Register new user via invitation token"""
    invitation = get_object_or_404(UserInvitation, token=token)
    
    if not invitation.is_valid():
        messages.error(request, 'Cette invitation a expiré ou n\'est plus valide.')
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = invitation.email
            user.role = invitation.role
            user.is_verified = True
            user.save()
            
            # Mark invitation as accepted
            invitation.status = 'accepted'
            invitation.accepted_at = timezone.now()
            invitation.save()
            
            # Send welcome email
            send_welcome_email(user)
            
            # Log user in
            login(request, user)
            messages.success(request, 'Bienvenue dans la famille KANYAMUKENGE! Votre compte a été créé avec succès.')
            return redirect('genealogy:dashboard')
    else:
        form = UserRegistrationForm(initial={'email': invitation.email})
    
    return render(request, 'accounts/register.html', {
        'form': form,
        'invitation': invitation
    })


@login_required
def send_invitation(request):
    """Send invitation to new family member"""
    if request.user.role != 'admin':
        messages.error(request, 'Seuls les administrateurs peuvent envoyer des invitations.')
        return redirect('genealogy:dashboard')
    
    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.invited_by = request.user
            invitation.save()
            
            # Send invitation email
            send_invitation_email(invitation)
            
            messages.success(request, f'Invitation envoyée à {invitation.email}.')
            return redirect('genealogy:manage_users')
    else:
        form = InvitationForm()
    
    return render(request, 'accounts/send_invitation.html', {'form': form})


@login_required
def profile_update(request):
    """Update user profile"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def profile_view(request):
    """View user profile"""
    return render(request, 'accounts/profile.html')


def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('genealogy:home')


# Email helper functions
def send_otp_email(user, token):
    """Send OTP token via email"""
    subject = 'Code de vérification - Famille KANYAMUKENGE'
    message = f"""
    Bonjour {user.get_full_name()},
    
    Voici votre code de vérification pour accéder au système généalogique de la famille KANYAMUKENGE:
    
    Code: {token}
    
    Ce code expire dans {settings.OTP_EXPIRE_MINUTES} minutes.
    
    Si vous n'avez pas demandé ce code, ignorez ce message.
    
    Cordialement,
    L'équipe KANYAMUKENGE
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_invitation_email(invitation):
    """Send invitation email to new family member"""
    subject = 'Invitation - Famille KANYAMUKENGE'
    registration_url = f"{settings.ALLOWED_HOSTS[0]}{reverse('accounts:register', kwargs={'token': invitation.token})}"
    
    message = f"""
    Bonjour,
    
    Vous êtes invité(e) à rejoindre l'arbre généalogique de la famille KANYAMUKENGE par {invitation.invited_by.get_full_name()}.
    
    Pour créer votre compte et accéder à l'arbre familial, cliquez sur le lien ci-dessous:
    {registration_url}
    
    Cette invitation expire le {invitation.expires_at.strftime('%d/%m/%Y à %H:%M')}.
    
    Si vous avez des questions, contactez {invitation.invited_by.get_full_name()} à l'adresse: {invitation.invited_by.email}
    
    Cordialement,
    La famille KANYAMUKENGE
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [invitation.email],
        fail_silently=False,
    )


def send_welcome_email(user):
    """Send welcome email to new user"""
    subject = 'Bienvenue - Famille KANYAMUKENGE'
    message = f"""
    Bienvenue {user.get_full_name()},
    
    Votre compte a été créé avec succès sur la plateforme généalogique de la famille KANYAMUKENGE.
    
    Vous pouvez maintenant:
    - Explorer l'arbre généalogique de la famille
    - Ajouter vos propres informations
    - Contribuer à l'enrichissement de notre histoire familiale
    
    Nous sommes heureux de vous accueillir dans cette initiative de préservation de notre patrimoine familial.
    
    Cordialement,
    La famille KANYAMUKENGE
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )