# research/models.py
from django.db import models
from core.models import TimeStampedModel
from accounts.models import User


# ── Dosen (tidak perlu akun, di-CRUD admin) ───────────────────────────────
class Lecturer(TimeStampedModel):
    """
    Master data dosen — dikelola admin.
    Dosen tidak perlu membuat akun.
    """
    FOCUS_CHOICES = (
        ('klinis',       'Psikologi Klinis'),
        ('perkembangan', 'Psikologi Perkembangan'),
        ('sosial',       'Psikologi Sosial'),
        ('industri',     'Psikologi Industri & Organisasi'),
        ('pendidikan',   'Psikologi Pendidikan'),
        ('umum',         'Umum'),
    )

    name         = models.CharField(max_length=200, verbose_name='Nama Dosen')
    nip          = models.CharField(max_length=50, blank=True, null=True, verbose_name='NIP')
    focus        = models.CharField(max_length=20, choices=FOCUS_CHOICES, verbose_name='Bidang Fokus')
    email        = models.EmailField(blank=True, null=True)
    phone        = models.CharField(max_length=20, blank=True, null=True)
    photo        = models.ImageField(upload_to='lecturers/', blank=True, null=True)
    bio          = models.TextField(blank=True, null=True, verbose_name='Deskripsi Singkat')
    is_active    = models.BooleanField(default=True)

    class Meta:
        ordering = ['focus', 'name']
        verbose_name = 'Dosen'
        verbose_name_plural = 'Dosen'

    def __str__(self):
        return f"{self.name} — {self.get_focus_display()}"

    @property
    def active_titles_count(self):
        return self.research_titles.filter(is_active=True).count()


# ── Judul Payung (per dosen, di-CRUD admin) ───────────────────────────────
class ResearchTitle(TimeStampedModel):
    """
    Judul payung penelitian yang dibuat admin per dosen.
    Mahasiswa memilih judul payung ini lalu input judul skripsi masing-masing.
    """
    lecturer     = models.ForeignKey(
        Lecturer,
        on_delete=models.PROTECT,
        related_name='research_titles',
        verbose_name='Dosen Pembimbing'
    )
    title        = models.CharField(max_length=300, verbose_name='Judul Payung')
    description  = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    focus        = models.CharField(
        max_length=20,
        choices=Lecturer.FOCUS_CHOICES,
        verbose_name='Bidang'
    )
    quota        = models.PositiveIntegerField(
        default=5,
        verbose_name='Kuota Mahasiswa'
    )
    is_active    = models.BooleanField(default=True)

    class Meta:
        ordering = ['lecturer', 'title']
        verbose_name = 'Judul Payung'
        verbose_name_plural = 'Judul Payung'

    def __str__(self):
        return f"{self.title} ({self.lecturer.name})"

    @property
    def slots_used(self):
        return self.requests.filter(status__in=['pending', 'approved']).count()

    @property
    def slots_remaining(self):
        return self.quota - self.slots_used

    @property
    def is_full(self):
        return self.slots_remaining <= 0

    @property
    def is_almost_full(self):
        return self.slots_used >= (self.quota * 0.8)

    @property
    def fill_percentage(self):
        if self.quota == 0:
            return 0
        return min(int((self.slots_used / self.quota) * 100), 100)


# ── Request Penelitian (Mahasiswa) ────────────────────────────────────────
class ResearchRequest(TimeStampedModel):
    """
    Mahasiswa memilih dosen + judul payung (atau individu),
    lalu memasukkan judul skripsi masing-masing.
    """
    TYPE_CHOICES = (
        ('payung',    'Dalam Judul Payung'),
        ('individu',  'Individu (tanpa judul payung)'),
    )
    STATUS_CHOICES = (
        ('pending',   'Menunggu'),
        ('approved',  'Disetujui'),
        ('rejected',  'Ditolak'),
        ('completed', 'Selesai'),
    )

    student         = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='research_requests',
        verbose_name='Mahasiswa'
    )
    lecturer        = models.ForeignKey(
        Lecturer,
        on_delete=models.PROTECT,
        related_name='student_requests',
        verbose_name='Dosen Pembimbing'
    )
    # Null jika tipe individu
    research_title  = models.ForeignKey(
        ResearchTitle,
        on_delete=models.PROTECT,
        related_name='requests',
        null=True,
        blank=True,
        verbose_name='Judul Payung (opsional)'
    )
    request_type    = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='payung',
        verbose_name='Tipe Request'
    )
    thesis_title    = models.CharField(
        max_length=300,
        verbose_name='Judul Skripsi'
    )
    proposal        = models.FileField(
        upload_to='research/proposals/',
        blank=True,
        null=True,
        verbose_name='File Proposal'
    )

    status          = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    admin_notes     = models.TextField(blank=True, null=True, verbose_name='Catatan Admin')
    approved_by     = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_research_requests'
    )
    approved_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Request Penelitian'
        verbose_name_plural = 'Request Penelitian'

    def __str__(self):
        return f"{self.student.get_full_name()} — {self.thesis_title}"


# ── Sesi Bimbingan (Log per request) ─────────────────────────────────────
class GuidanceSession(TimeStampedModel):
    """Log bimbingan per request penelitian mahasiswa."""
    request    = models.ForeignKey(
        ResearchRequest,
        on_delete=models.CASCADE,
        related_name='guidance_sessions'
    )
    date       = models.DateField(verbose_name='Tanggal Bimbingan')
    topic      = models.CharField(max_length=200, verbose_name='Topik')
    notes      = models.TextField(verbose_name='Catatan')
    attachment = models.FileField(
        upload_to='research/guidance/',
        blank=True, null=True,
        verbose_name='Lampiran'
    )

    class Meta:
        ordering = ['-date']
        verbose_name = 'Sesi Bimbingan'
        verbose_name_plural = 'Sesi Bimbingan'

    def __str__(self):
        return f"{self.request.student.get_full_name()} — {self.date}"
