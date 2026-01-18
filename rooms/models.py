from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import User
from core.models import TimeStampedModel

class Room(TimeStampedModel):
    """Master data ruangan"""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'
    
    def __str__(self):
        return f"{self.code} - {self.name} (Cap: {self.capacity})"


class RoomBooking(TimeStampedModel):
    """Peminjaman ruangan"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_bookings')
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='bookings')
    
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    participants = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    purpose = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True)
    
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_room_bookings'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-booking_date', '-start_time']
        verbose_name = 'Room Booking'
        verbose_name_plural = 'Room Bookings'
        indexes = [
            models.Index(fields=['booking_date', 'room']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.room.name} - {self.booking_date} ({self.status})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate capacity
        if self.participants > self.room.capacity:
            raise ValidationError(f'Jumlah peserta melebihi kapasitas ruangan ({self.room.capacity})')
        
        # Validate time range
        if self.start_time >= self.end_time:
            raise ValidationError('Jam mulai harus lebih awal dari jam selesai')


class RoomBlockSchedule(TimeStampedModel):
    """Jadwal blok rutin ruangan"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='block_schedules')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Recurring schedule
    day_of_week = models.PositiveSmallIntegerField(
        choices=[(0, 'Senin'), (1, 'Selasa'), (2, 'Rabu'), (3, 'Kamis'), (4, 'Jumat'), (5, 'Sabtu'), (6, 'Minggu')],
        null=True,
        blank=True
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Or specific date range
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['room', 'day_of_week', 'start_time']
        verbose_name = 'Room Block Schedule'
        verbose_name_plural = 'Room Block Schedules'
    
    def __str__(self):
        return f"{self.room.name} - {self.name}"
