from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from rooms.models import Room
from core.models import TimeStampedModel

class Practicum(TimeStampedModel):
    """Jadwal Praktikum"""
    
    TYPE_CHOICES = (
        ('inteligensi', 'Praktikum Inteligensi'),
        ('inventory', 'Praktikum Inventory'),
        ('wawancara', 'Praktikum Wawancara'),
        ('konseling', 'Praktikum Konseling'),
    )
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    session_name = models.CharField(max_length=100)
    instructor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='practicum_sessions')
    
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = 'Practicum'
        verbose_name_plural = 'Practicums'
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.session_name}"
    
    @property
    def registered_count(self):
        return self.registrations.filter(status='approved').count()
    
    @property
    def waitlist_count(self):
        return self.registrations.filter(status='waitlist').count()
    
    @property
    def is_full(self):
        return self.registered_count >= self.capacity


class PracticumRegistration(TimeStampedModel):
    """Pendaftaran Praktikum"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('waitlist', 'Waitlist'),
        ('cancelled', 'Cancelled'),
    )
    
    practicum = models.ForeignKey(Practicum, on_delete=models.CASCADE, related_name='registrations')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='practicum_registrations')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    certificate_issued = models.BooleanField(default=False)
    certificate_file = models.FileField(upload_to='practicum/certificates/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['practicum', 'student']
        verbose_name = 'Practicum Registration'
        verbose_name_plural = 'Practicum Registrations'
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.practicum.session_name}"


class Attendance(TimeStampedModel):
    """Presensi Praktikum"""
    registration = models.ForeignKey(
        PracticumRegistration,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField()
    is_present = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['registration', 'date']
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendances'
    
    def __str__(self):
        return f"{self.registration.student.get_full_name()} - {self.date}"
