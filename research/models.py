from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import User
from core.models import TimeStampedModel

class ResearchVariable(TimeStampedModel):
    """Variabel Penelitian"""
    
    FIELD_CHOICES = (
        ('klinis', 'Psikologi Klinis'),
        ('perkembangan', 'Psikologi Perkembangan'),
        ('sosial', 'Psikologi Sosial'),
        ('industri', 'Psikologi Industri & Organisasi'),
        ('pendidikan', 'Psikologi Pendidikan'),
    )
    
    name = models.CharField(max_length=200)
    field = models.CharField(max_length=20, choices=FIELD_CHOICES)
    description = models.TextField()
    supervisor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        limit_choices_to={'role': 'dosen'},
        related_name='research_variables'
    )
    
    quota = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['field', 'name']
        verbose_name = 'Research Variable'
        verbose_name_plural = 'Research Variables'
    
    def __str__(self):
        return f"{self.name} ({self.get_field_display()})"
    
    @property
    def slots_used(self):
        return self.requests.filter(status='approved').count()
    
    @property
    def slots_remaining(self):
        return self.quota - self.slots_used
    
    @property
    def is_full(self):
        return self.slots_remaining <= 0


class VariableRequest(TimeStampedModel):
    """Request Variabel Penelitian"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    )
    
    variable = models.ForeignKey(ResearchVariable, on_delete=models.PROTECT, related_name='requests')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='variable_requests')
    
    proposal = models.FileField(upload_to='research/proposals/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    admin_notes = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_variable_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['variable', 'student']
        verbose_name = 'Variable Request'
        verbose_name_plural = 'Variable Requests'
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.variable.name}"


class GuidanceSession(TimeStampedModel):
    """Log Bimbingan Penelitian"""
    request = models.ForeignKey(VariableRequest, on_delete=models.CASCADE, related_name='guidance_sessions')
    date = models.DateField()
    topic = models.CharField(max_length=200)
    notes = models.TextField()
    attachment = models.FileField(upload_to='research/guidance/', blank=True, null=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Guidance Session'
        verbose_name_plural = 'Guidance Sessions'
    
    def __str__(self):
        return f"{self.request.student.get_full_name()} - {self.date}"
