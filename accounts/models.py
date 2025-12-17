from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string

class User(AbstractUser):
    """Custom User model with additional fields for genealogy system"""
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('member', 'Family Member'),
        ('visitor', 'Visitor'),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Permissions for genealogy system
    can_add_children = models.BooleanField(default=True)
    can_modify_own_info = models.BooleanField(default=True)
    can_view_private_info = models.BooleanField(default=False)
    can_export_data = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    class Meta:
        db_table = 'accounts_user'


class OTPToken(models.Model):
    """OTP tokens for admin authentication"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        if not self.expires_at:
            from django.conf import settings
            expire_minutes = getattr(settings, 'OTP_EXPIRE_MINUTES', 10)
            self.expires_at = timezone.now() + timedelta(minutes=expire_minutes)
        super().save(*args, **kwargs)
    
    def generate_token(self):
        """Generate a 6-digit OTP token"""
        return ''.join(random.choices(string.digits, k=6))
    
    def is_valid(self):
        """Check if token is still valid"""
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"OTP for {self.user.email} - {self.token}"
    
    class Meta:
        db_table = 'accounts_otp_token'
        ordering = ['-created_at']


class UserInvitation(models.Model):
    """Invitations sent to family members"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    email = models.EmailField()
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    token = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default='member')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)  # 7 days to accept
        super().save(*args, **kwargs)
    
    def generate_token(self):
        """Generate a unique invitation token"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=64))
    
    def is_valid(self):
        """Check if invitation is still valid"""
        return self.status == 'pending' and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Invitation for {self.email} by {self.invited_by.get_full_name()}"
    
    class Meta:
        db_table = 'accounts_user_invitation'
        ordering = ['-created_at']