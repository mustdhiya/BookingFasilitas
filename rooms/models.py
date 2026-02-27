from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from accounts.models import User
from core.models import TimeStampedModel


class Room(TimeStampedModel):
    """Master data ruangan"""
    code        = models.CharField(max_length=10, unique=True)
    name        = models.CharField(max_length=100)
    capacity    = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    description = models.TextField(blank=True, null=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering       = ['code']
        verbose_name   = 'Room'
        verbose_name_plural = 'Rooms'

    def __str__(self):
        return f"{self.code} - {self.name} (Cap: {self.capacity})"


class RoomBooking(TimeStampedModel):
    """Peminjaman ruangan — konsep harian (satu atau beberapa hari)"""

    STATUS_CHOICES = (
        ('pending',   'Pending'),
        ('approved',  'Disetujui'),
        ('declined',  'Ditolak'),
        ('cancelled', 'Dibatalkan'),
        ('completed', 'Selesai'),
    )

    user  = models.ForeignKey(User,  on_delete=models.CASCADE,  related_name='room_bookings')
    room  = models.ForeignKey(Room,  on_delete=models.PROTECT,  related_name='bookings')

    # ── Rentang tanggal ────────────────────────────────────────────────
    date_start = models.DateField(verbose_name='Tanggal Mulai')
    date_end   = models.DateField(verbose_name='Tanggal Selesai')
    # date_end == date_start  →  peminjaman 1 hari
    # date_end >  date_start  →  peminjaman multi-hari

    participants = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Jumlah Peserta',
    )
    purpose = models.TextField(verbose_name='Keperluan')

    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True)

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_room_bookings',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_start']
        verbose_name       = 'Room Booking'
        verbose_name_plural = 'Room Bookings'
        indexes = [
            models.Index(fields=['date_start', 'room']),
            models.Index(fields=['date_end',   'room']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        if self.date_start == self.date_end:
            return f"{self.room.name} – {self.date_start} ({self.get_status_display()})"
        return f"{self.room.name} – {self.date_start} s/d {self.date_end} ({self.get_status_display()})"

    @property
    def duration_days(self):
        """Jumlah hari peminjaman (inklusif)"""
        return (self.date_end - self.date_start).days + 1

    @property
    def is_single_day(self):
        return self.date_start == self.date_end

    def clean(self):
        # Kapasitas
        if self.room_id and self.participants > self.room.capacity:
            raise ValidationError(
                f'Jumlah peserta ({self.participants}) melebihi kapasitas '
                f'ruangan ({self.room.capacity} orang).'
            )
        # Urutan tanggal
        if self.date_start and self.date_end and self.date_end < self.date_start:
            raise ValidationError('Tanggal selesai tidak boleh sebelum tanggal mulai.')

    def overlaps_with(self, other_start, other_end):
        """Cek apakah booking ini overlap dengan rentang tanggal lain."""
        return self.date_start <= other_end and self.date_end >= other_start


class RoomBlockSchedule(TimeStampedModel):
    """
    Blokir rutin ruangan — bisa berulang (per hari-dalam-minggu)
    atau satu rentang tanggal spesifik.
    Tidak lagi menyimpan start_time/end_time karena sistem berbasis hari penuh.
    """

    BLOCK_TYPE_CHOICES = (
        ('routine',     'Blok Rutin'),
        ('maintenance', 'Maintenance'),
        ('event',       'Kegiatan'),
        ('other',       'Lainnya'),
    )

    room        = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='block_schedules')
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    block_type  = models.CharField(max_length=20, choices=BLOCK_TYPE_CHOICES, default='routine')

    # ── Opsi 1: Berulang mingguan (isi day_of_week, kosongkan date_start/end) ──
    day_of_week = models.PositiveSmallIntegerField(
        choices=[
            (0, 'Senin'), (1, 'Selasa'), (2, 'Rabu'),
            (3, 'Kamis'), (4, 'Jumat'), (5, 'Sabtu'), (6, 'Minggu'),
        ],
        null=True, blank=True,
        help_text='Isi jika blokir berulang tiap minggu pada hari ini.',
    )

    # ── Opsi 2: Rentang tanggal spesifik (isi date_start/end, kosongkan day_of_week) ──
    date_start = models.DateField(null=True, blank=True)
    date_end   = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering       = ['room', 'day_of_week', 'date_start']
        verbose_name   = 'Room Block Schedule'
        verbose_name_plural = 'Room Block Schedules'

    def __str__(self):
        return f"{self.room.name} – {self.name}"

    def clean(self):
        has_recurring = self.day_of_week is not None
        has_specific  = self.date_start or self.date_end

        if has_recurring and has_specific:
            raise ValidationError(
                'Isi salah satu: berulang mingguan (day_of_week) '
                'ATAU rentang tanggal spesifik (date_start/date_end), tidak keduanya.'
            )
        if not has_recurring and not has_specific:
            raise ValidationError(
                'Wajib isi salah satu: day_of_week atau date_start/date_end.'
            )
        if has_specific and self.date_end and self.date_start:
            if self.date_end < self.date_start:
                raise ValidationError('date_end tidak boleh sebelum date_start.')

    def covers_date(self, date):
        """Apakah blokir ini mencakup tanggal tertentu?"""
        if not self.is_active:
            return False
        if self.day_of_week is not None:
            return date.weekday() == self.day_of_week
        if self.date_start and self.date_end:
            return self.date_start <= date <= self.date_end
        if self.date_start:
            return date == self.date_start
        return False
