from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from accounts.models import User
from core.models import TimeStampedModel


# tools/models.py — tambahkan KATEGORI_CHOICES dan field kategori ke TestTool

class TestTool(TimeStampedModel):

    UNIT_CHOICES = (
        ('lembar', 'Lembar'),
        ('set',    'Set'),
        ('buah',   'Buah'),
    )

    KATEGORI_CHOICES = (
        ('inteligensi', 'Inteligensi'),
        ('kepribadian', 'Kepribadian'),
        ('minat',       'Minat & Bakat'),
        ('klinis',      'Klinis'),
        ('lainnya',     'Lainnya'),
    )

    TRANSACTION_TYPE_CHOICES = (
        ('pinjam', 'Peminjaman'),
        ('sewa',   'Penyewaan'),
        ('beli',   'Pembelian'),
    )

    code             = models.CharField(max_length=20, unique=True)
    name             = models.CharField(max_length=150)
    description      = models.TextField(blank=True, null=True)
    kategori         = models.CharField(max_length=20, choices=KATEGORI_CHOICES, default='lainnya')
    unit             = models.CharField(max_length=20, choices=UNIT_CHOICES, default='lembar')
    stock            = models.PositiveIntegerField(default=0)
    price_per_unit   = models.PositiveIntegerField(default=0)
    is_active        = models.BooleanField(default=True)
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
        default='pinjam',
    )

    class Meta:
        ordering            = ['code']
        verbose_name        = 'Test Tool'
        verbose_name_plural = 'Test Tools'

    def __str__(self):
        return f"{self.code} – {self.name} (Stok: {self.stock} {self.unit})"

    @property
    def is_available(self):
        return self.is_active and self.stock > 0



class ToolRental(TimeStampedModel):
    """Peminjaman alat tes — konsep harian"""

    STATUS_CHOICES = [
        ('pending',          'Menunggu Persetujuan'),
        ('approved',         'Disetujui'),
        ('payment_pending',  'Menunggu Verifikasi Bayar'), 
        ('borrowed',         'Sedang Dipinjam'),
        ('overdue',          'Terlambat'),
        ('returning',        'Diajukan Kembali'),
        ('returned',         'Selesai'),
        ('declined',         'Ditolak'),
        ('cancelled',        'Dibatalkan'),
    ]
    TRANSACTION_TYPE_CHOICES = (
        ('pinjam', 'Peminjaman'),
        ('sewa',   'Penyewaan'),
        ('beli',   'Pembelian'),
    )

    # Tambahkan field ini setelah field `user`:
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
        default='pinjam',
    )

    # Tambahkan field ini setelah field `is_paid`:
    fine_amount = models.PositiveIntegerField(
        default=0,
        help_text='Denda keterlambatan dalam Rupiah'
    )


    INSTITUTION_CHOICES = (
        ('umkt',     'UMKT'),
        ('non_umkt', 'Non-UMKT'),
    )

    PURPOSE_CHOICES = (
        ('seleksi_dosen',    'Seleksi Dosen UMKT'),
        ('seleksi_karyawan', 'Seleksi Karyawan Non-UMKT'),
        ('pelatihan',        'Pelatihan Alat Tes Internal'),
        ('penelitian',       'Penelitian Individu/Kelompok'),
        ('lainnya',          'Kegiatan Lainnya'),
    )

    PAYMENT_CHOICES = (
        ('before', 'Sebelum Peminjaman'),
        ('after',  'Sesudah Peminjaman'),
    )

    # ── Peminjam ──────────────────────────────────────────────────────
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tool_rentals')
    institution = models.CharField(max_length=20, choices=INSTITUTION_CHOICES, default='umkt')
    purpose     = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    activity_letter = models.FileField(
        upload_to='tool_rentals/letters/%Y/%m/',
        null=True, blank=True,
        help_text='Surat kegiatan (PDF/JPG/PNG)'
    )

    # ── Alat & Jumlah ─────────────────────────────────────────────────
    tool     = models.ForeignKey(TestTool, on_delete=models.PROTECT, related_name='rentals')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    components = models.JSONField(
        default=list,
        blank=True,
        help_text='Komponen yang dipinjam: ["buku_tes", "lj", "norma"]'
    )

    # ── Rentang tanggal ───────────────────────────────────────────────
    date_start = models.DateField(verbose_name='Tanggal Mulai Pinjam')
    date_end   = models.DateField(verbose_name='Tanggal Kembali')

    # ── Pembayaran ────────────────────────────────────────────────────
    payment_time  = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='before')
    total_cost    = models.PositiveIntegerField(default=0, editable=False)
    is_paid       = models.BooleanField(default=False)
    payment_proof = models.FileField(
        upload_to='tool_rentals/payments/%Y/%m/',
        null=True, blank=True
    )
    agreement_file = models.FileField(
        upload_to='tool_rentals/agreements/%Y/%m/',
        null=True, blank=True,
        help_text='Surat perjanjian yang sudah ditandatangani'
    )

    # ── Status & Admin ────────────────────────────────────────────────
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_tool_rentals'
    )
    approved_at  = models.DateTimeField(null=True, blank=True)
    returned_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_start', '-created_at']
        verbose_name       = 'Tool Rental'
        verbose_name_plural = 'Tool Rentals'
        indexes = [
            models.Index(fields=['date_start', 'tool']),
            models.Index(fields=['status']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return (
            f"{self.tool.name} × {self.quantity} — "
            f"{self.user.get_full_name() or self.user.email} "
            f"({self.date_start} s/d {self.date_end})"
        )

    @property
    def duration_days(self):
        return (self.date_end - self.date_start).days + 1

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
            self.status == 'borrowed' and
            self.date_end < timezone.localdate()
        )

    def save(self, *args, **kwargs):
        # Auto-hitung total biaya
        self.total_cost = self.tool.price_per_unit * self.quantity
        super().save(*args, **kwargs)

    def clean(self):
        if self.date_end and self.date_start and self.date_end < self.date_start:
            raise ValidationError('Tanggal kembali tidak boleh sebelum tanggal mulai.')

        if self.tool_id and self.quantity and self.quantity > self.tool.stock:
            raise ValidationError(
                f'Stok tidak cukup. Stok tersedia: {self.tool.stock} {self.tool.unit}.'
            )

