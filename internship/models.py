from django.db import models
from core.models import TimeStampedModel
from accounts.models import User
from research.models import Lecturer  # reuse dosen dari research
from django.db import models
from core.models import TimeStampedModel
from accounts.models import User
from research.models import Lecturer


class InternshipPartner(TimeStampedModel):
    """Master data mitra magang — CRUD admin."""
    name = models.CharField(max_length=200, verbose_name='Nama Instansi')
    address = models.TextField(blank=True, verbose_name='Alamat')
    field = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Bidang Magang',
        help_text='Psikologi Klinis, Industri, dll'
    )
    contact_person = models.CharField(max_length=150, blank=True, verbose_name='Kontak Person')
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    keterangan = models.TextField(
        blank=True,
        verbose_name='Keterangan',
        help_text='Contoh: Magang berbayar/tidak berbayar, jam kerja, syarat khusus, dll'
    )

    is_active = models.BooleanField(default=True)

    quota = models.PositiveIntegerField(
        default=0,
        verbose_name='Kuota',
        help_text='0 = tidak dibatasi'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Mitra Magang'
        verbose_name_plural = 'Mitra Magang'

    def __str__(self):
        return self.name

    @property
    def accepted_count(self):
        return self.internshiprequest_set.filter(
            status__in=['approved', 'ongoing']
        ).count()

    @property
    def quota_remaining(self):
        if self.quota == 0:
            return None
        return max(0, self.quota - self.accepted_count)

    @property
    def quota_percentage(self):
        if self.quota == 0:
            return 0
        if self.quota <= 0:
            return 0
        return min(100, int((self.accepted_count / self.quota) * 100))

    @property
    def quota_status(self):
        if self.quota == 0:
            return 'unlimited'
        remaining = self.quota_remaining
        if remaining == 0:
            return 'full'
        if remaining <= 2:
            return 'limited'
        return 'available'
    
class InternshipRequest(TimeStampedModel):
    """Pendaftaran magang mahasiswa."""
    STATUS_CHOICES = (
        ('pending', 'Menunggu'),
        ('approved', 'Disetujui'),
        ('ongoing', 'Berjalan'),
        ('completed', 'Selesai'),
        ('rejected', 'Ditolak'),
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='internship_requests',
        verbose_name='Mahasiswa'
    )
    
    # Mitra magang (opsional - bisa manual input)
    partner = models.ForeignKey(
        InternshipPartner,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Mitra Magang'
    )
    
    # Manual input jika tidak pilih mitra
    partner_name = models.CharField(max_length=200, blank=True, verbose_name='Nama Instansi')
    partner_address = models.TextField(blank=True, verbose_name='Alamat Instansi')
    partner_field = models.CharField(max_length=100, blank=True, verbose_name='Bidang Magang')
    
    supervisor_name = models.CharField(max_length=150, verbose_name='Supervisor Lapangan')
    supervisor_phone = models.CharField(max_length=20, verbose_name='No. HP Supervisor')
    
    start_date = models.DateField(verbose_name='Tanggal Mulai')
    end_date = models.DateField(verbose_name='Tanggal Selesai')
    total_days = models.PositiveIntegerField(default=0, verbose_name='Total Hari Magang')
    
    lecturer = models.ForeignKey(
        Lecturer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='internships',
        verbose_name='Dosen Pembimbing'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_internships'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Dokumen
    intro_letter = models.FileField(
        upload_to='internship/docs/',
        blank=True, null=True,
        verbose_name='Surat Pengantar'
    )
    final_report = models.FileField(
        upload_to='internship/reports/',
        blank=True, null=True,
        verbose_name='Laporan Akhir'
    )
    assessment = models.FileField(
        upload_to='internship/assessments/',
        blank=True, null=True,
        verbose_name='Penilaian Supervisor'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Pendaftaran Magang'
        verbose_name_plural = 'Pendaftaran Magang'

    def __str__(self):
        return f"{self.student.get_full_name()} — {self.partner_name or self.partner}"

    @property
    def is_active(self):
        return self.status in ['pending', 'approved', 'ongoing']

class InternshipLog(TimeStampedModel):
    """Log aktivitas harian magang (mirip sesi bimbingan)."""
    request = models.ForeignKey(
        InternshipRequest,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    date = models.DateField(verbose_name='Tanggal Kegiatan')
    topic = models.CharField(max_length=200, verbose_name='Kegiatan')
    notes = models.TextField(verbose_name='Deskripsi')
    attachment = models.FileField(
        upload_to='internship/logs/',
        blank=True, null=True,
        verbose_name='Lampiran'
    )

    class Meta:
        ordering = ['-date']
        verbose_name = 'Log Magang'
        verbose_name_plural = 'Log Magang'

    def __str__(self):
        return f"{self.request.student.get_full_name()} — {self.date}"
