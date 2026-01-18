from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """Custom User Model"""
    
    ROLE_CHOICES = (
        ('mahasiswa', 'Mahasiswa'),
        ('dosen', 'Dosen'),
        ('laboran', 'Laboran/Admin'),
        ('eksternal', 'Eksternal'),
    )
    
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='mahasiswa')
    nim_nip = models.CharField(max_length=20, blank=True, null=True, verbose_name='NIM/NIP')
    instansi = models.CharField(max_length=200, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username


class LoginHistory(models.Model):
    """Track user login activities"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500)
    device_type = models.CharField(max_length=50)  # Desktop, Mobile, Tablet
    os = models.CharField(max_length=50)
    location = models.CharField(max_length=200, blank=True, null=True)
    success = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Login History'
        verbose_name_plural = 'Login Histories'
    
    def __str__(self):
        return f"{self.user.email} - {self.timestamp}"
