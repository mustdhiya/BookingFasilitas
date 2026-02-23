from django.db import models
from django.conf import settings


class KonselingSession(models.Model):

    STATUS_CHOICES = [
        ('pending',   'Menunggu Persetujuan'),
        ('approved',  'Disetujui'),
        ('rejected',  'Ditolak'),
        ('done',      'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ]

    TUJUAN_CHOICES = [
        ('akademik',    'Masalah Akademik'),
        ('karir',       'Perencanaan Karir'),
        ('pribadi',     'Masalah Pribadi'),
        ('sosial',      'Masalah Sosial/Relasi'),
        ('keluarga',    'Masalah Keluarga'),
        ('kecemasan',   'Kecemasan / Stres'),
        ('lainnya',     'Lainnya'),
    ]

    # Relasi ke User
    user            = models.ForeignKey(
                          settings.AUTH_USER_MODEL,
                          on_delete=models.CASCADE,
                          related_name='konseling_sessions'
                      )

    # Jadwal
    tanggal_preferensi  = models.DateField(help_text='Tanggal yang diinginkan klien')
    waktu_preferensi    = models.TimeField(help_text='Jam yang diinginkan klien')
    tanggal_aktual      = models.DateField(null=True, blank=True, help_text='Jadwal final oleh admin')
    waktu_aktual        = models.TimeField(null=True, blank=True)

    # Konten sesi
    tujuan          = models.CharField(max_length=20, choices=TUJUAN_CHOICES)
    keluhan         = models.TextField(help_text='Deskripsi keluhan / tujuan konseling')
    catatan_admin   = models.TextField(blank=True, help_text='Catatan dari admin/psikolog')

    # Ruangan (diassign admin setelah approved)
    ruangan         = models.CharField(max_length=100, blank=True)

    # Psikolog (diassign admin)
    psikolog        = models.CharField(max_length=150, blank=True)

    # Tarif & Pembayaran
    tarif           = models.DecimalField(max_digits=10, decimal_places=0,
                                          null=True, blank=True)
    sudah_bayar     = models.BooleanField(default=False)
    bukti_bayar     = models.ImageField(upload_to='konseling/bukti/', null=True, blank=True)

    # Informed Consent
    consent_disetujui   = models.BooleanField(default=False)
    consent_timestamp   = models.DateTimeField(null=True, blank=True)

    # Status & Audit
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    alasan_tolak    = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sesi Konseling'
        verbose_name_plural = 'Sesi Konseling'

    def __str__(self):
        return f'{self.user.get_full_name()} — {self.get_tujuan_display()} ({self.tanggal_preferensi})'

    def get_status_display_badge(self):
        badge_map = {
            'pending':   'badge-warning',
            'approved':  'badge-success',
            'rejected':  'badge-danger',
            'done':      'badge-gray',
            'cancelled': 'badge-gray',
        }
        return badge_map.get(self.status, 'badge-gray')

    @property
    def is_umkt_user(self):
        return self.user.user_type == 'umkt'
