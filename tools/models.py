from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from accounts.models import User
from core.models import TimeStampedModel

class Tool(TimeStampedModel):
    """Master data alat tes"""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    price_per_sheet = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = 'Tool'
        verbose_name_plural = 'Tools'
    
    def __str__(self):
        return f"{self.code} - {self.name} (Stock: {self.stock})"


class ToolRental(TimeStampedModel):
    """Peminjaman alat tes (12-step wizard)"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
    )
    
    PAYMENT_CHOICES = (
        ('before', 'Sebelum Peminjaman'),
        ('after', 'Sesudah Peminjaman'),
    )
    
    INSTANSI_CHOICES = (
        ('umkt', 'UMKT'),
        ('non-umkt', 'Non-UMKT'),
    )
    
    # Step 1-3: Data Peminjam
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tool_rentals')
    instansi = models.CharField(max_length=20, choices=INSTANSI_CHOICES)
    purpose = models.CharField(max_length=200)
    activity_letter = models.FileField(upload_to='tool_rentals/letters/')
    
    # Step 5-8: Alat Tes (simplified - bisa extend untuk multiple tools)
    tool = models.ForeignKey(Tool, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    
    with_book = models.BooleanField(default=False)
    with_answer_sheet = models.BooleanField(default=False)
    with_norms = models.BooleanField(default=False)
    
    # Step 9: Duration
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Step 10: Payment
    payment_time = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    payment_status = models.BooleanField(default=False)
    
    # Step 11: Agreement
    agreement_file = models.FileField(upload_to='tool_rentals/agreements/')
    
    # Calculated fields
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.PositiveIntegerField()
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True)
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_tool_rentals'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    returned_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Tool Rental'
        verbose_name_plural = 'Tool Rentals'
    
    def __str__(self):
        return f"{self.tool.name} - {self.user.get_full_name()} ({self.status})"
    
    def calculate_total(self):
        """Calculate total rental cost"""
        self.total_amount = self.tool.price_per_sheet * self.quantity
        return self.total_amount
    
    def calculate_duration(self):
        """Calculate rental duration in days"""
        delta = self.end_date - self.start_date
        self.duration_days = delta.days + 1
        return self.duration_days
    
    def save(self, *args, **kwargs):
        self.calculate_total()
        self.calculate_duration()
        super().save(*args, **kwargs)


class ToolBlockSchedule(TimeStampedModel):
    """Jadwal blok alat tes (misalnya saat pengadaan)"""
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name='block_schedules')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['start_date']
        verbose_name = 'Tool Block Schedule'
        verbose_name_plural = 'Tool Block Schedules'
    
    def __str__(self):
        return f"{self.tool.name} - {self.name}"
