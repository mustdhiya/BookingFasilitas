# practicum/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from rooms.models import Room
from research.models import Lecturer  
from core.models import TimeStampedModel


class Practicum(TimeStampedModel):
    """Jadwal Praktikum"""

    TYPE_CHOICES = (
        ('inteligensi', 'Praktikum Inteligensi'),
        ('inventory',   'Praktikum Inventory'),
        ('wawancara',   'Praktikum Wawancara'),
        ('konseling',   'Praktikum Konseling'),
    )

    type         = models.CharField(max_length=20, choices=TYPE_CHOICES)
    session_name = models.CharField(max_length=100, verbose_name='Nama Sesi')

    lecturer     = models.ForeignKey(
        Lecturer,
        on_delete=models.PROTECT,
        related_name='practicum_sessions',
        verbose_name='Dosen Pengampu'
    )

    room         = models.ForeignKey(Room, on_delete=models.PROTECT, verbose_name='Ruangan')
    date         = models.DateField(verbose_name='Tanggal')
    start_time   = models.TimeField(verbose_name='Jam Mulai')
    end_time     = models.TimeField(verbose_name='Jam Selesai')

    capacity     = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Kapasitas'
    )
    description  = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    is_active    = models.BooleanField(default=True)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = 'Jadwal Praktikum'
        verbose_name_plural = 'Jadwal Praktikum'
        unique_together = [
            ['room', 'date', 'start_time'],
        ]

    def __str__(self):
        return f"{self.get_type_display()} — {self.session_name} ({self.date})"

    @property
    def registered_count(self):
        # menghitung semua yg aktif: pending + approved + waitlist
        return self.registrations.filter(
            status__in=['pending', 'approved', 'waitlist']
        ).count()

    @property
    def is_full(self):
        return self.registered_count >= self.capacity

    @property
    def is_almost_full(self):
        """True jika >= 80% kapasitas terisi"""
        return self.registered_count >= (self.capacity * 0.8)

    @property
    def fill_percentage(self):
        """Persentase pengisian 0-100"""
        if self.capacity == 0:
            return 0
        return min(int((self.registered_count / self.capacity) * 100), 100)

class PracticumRegistration(TimeStampedModel):
    """Pendaftaran Mahasiswa ke Praktikum"""

    STATUS_CHOICES = (
        ('pending',   'Menunggu'),
        ('approved',  'Disetujui'),
        ('waitlist',  'Waitlist'),
        ('cancelled', 'Dibatalkan'),
    )

    practicum            = models.ForeignKey(
        Practicum,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    student              = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='practicum_registrations'
    )
    status               = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    attendance_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    certificate_issued   = models.BooleanField(default=False)
    certificate_file     = models.FileField(
        upload_to='practicum/certificates/',
        blank=True, null=True
    )

    class Meta:
        ordering = ['-created_at']
        unique_together = ['practicum', 'student']
        verbose_name = 'Pendaftaran Praktikum'
        verbose_name_plural = 'Pendaftaran Praktikum'

    def __str__(self):
        return f"{self.student.get_full_name()} — {self.practicum.session_name}"


class Attendance(TimeStampedModel):
    """Presensi per sesi praktikum"""
    registration = models.ForeignKey(
        PracticumRegistration,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date       = models.DateField()
    is_present = models.BooleanField(default=False)
    notes      = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['registration', 'date']
        verbose_name = 'Presensi'
        verbose_name_plural = 'Presensi'

    def __str__(self):
        return f"{self.registration.student.get_full_name()} — {self.date}"
