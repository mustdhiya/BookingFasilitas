from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class UserSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='active_sessions'
    )
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_seen_at']

    def __str__(self):
        return f"{self.user.email} - {self.session_key}"

class User(AbstractUser):

    ROLE_CHOICES = (
        ('mahasiswa', 'Mahasiswa'),
        ('dosen', 'Dosen'),
        ('laboran', 'Laboran/Admin'),
        ('eksternal', 'Eksternal'),
    )

    USER_TYPE_CHOICES = (
        ('umkt', 'UMKT'),
        ('non_umkt', 'Non-UMKT / Umum'),
    )
    # ── Rejection tracking ─────────────────────────────
    rejection_reason = models.TextField(
        blank=True, null=True,
        verbose_name='Alasan Penolakan'
    )
    rejected_at = models.DateTimeField(blank=True, null=True)
    rejected_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rejected_users',
        verbose_name='Ditolak oleh'
    )
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='mahasiswa')
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='umkt')

    nim_nip = models.CharField(max_length=20, blank=True, null=True, verbose_name='NIM/NIP')
    prodi = models.CharField(max_length=100, blank=True, null=True, verbose_name='Program Studi')
    angkatan = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Angkatan')
    instansi = models.CharField(max_length=200, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    ktm_photo = models.ImageField(upload_to='ktm/', blank=True, null=True, verbose_name='Foto KTM/KTP')

    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_users',
        verbose_name='Diverifikasi oleh'
    )

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

    @property
    def is_umkt(self):
        return self.user_type == 'umkt'

    @property
    def display_id(self):
        """NIM untuk UMKT, nama untuk non-UMKT"""
        return self.nim_nip or self.username


class LoginHistory(models.Model):

    FAIL_REASONS = (
        ('wrong_password', 'Password salah'),
        ('not_found', 'Akun tidak ditemukan'),
        ('not_verified', 'Akun belum diverifikasi'),
        ('inactive', 'Akun dinonaktifkan'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        null=True, blank=True
    )
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.CharField(max_length=500, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    browser     = models.CharField(max_length=100, blank=True)  # ← TAMBAH
    os          = models.CharField(max_length=50, blank=True)
    location    = models.CharField(max_length=200, blank=True)  # ← TAMBAH
    success     = models.BooleanField(default=True)
    fail_reason = models.CharField(max_length=20, choices=FAIL_REASONS, blank=True, null=True)
    login_at    = models.DateTimeField(auto_now_add=True)  # ← RENAME dari timestamp

    class Meta:
        ordering = ['-login_at']
        verbose_name = 'Login History'
        verbose_name_plural = 'Login Histories'

    def __str__(self):
        status = 'sukses' if self.success else 'gagal'
        user_info = self.user.email if self.user else 'unknown'
        return f"{user_info} - {status} - {self.login_at:%d %b %Y %H:%M}"
