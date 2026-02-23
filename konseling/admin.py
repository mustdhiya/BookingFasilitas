from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import KonselingSession


def kirim_notifikasi(sesi, status):
    """Helper: kirim email notifikasi ke klien."""
    subjek_map = {
        'approved': 'Sesi Konseling Anda Disetujui',
        'rejected': 'Sesi Konseling Anda Ditolak',
        'done':     'Sesi Konseling Selesai',
    }
    pesan_map = {
        'approved': (
            f"Halo {sesi.user.get_full_name()},\n\n"
            f"Sesi konseling Anda pada {sesi.tanggal_aktual or sesi.tanggal_preferensi} "
            f"pukul {sesi.waktu_aktual or sesi.waktu_preferensi} telah DISETUJUI.\n"
            f"Ruangan: {sesi.ruangan or '-'}\n"
            f"Psikolog: {sesi.psikolog or '-'}\n\n"
            f"Catatan admin: {sesi.catatan_admin or '-'}\n\n"
            f"Harap hadir tepat waktu. Terima kasih."
        ),
        'rejected': (
            f"Halo {sesi.user.get_full_name()},\n\n"
            f"Mohon maaf, pengajuan sesi konseling Anda DITOLAK.\n"
            f"Alasan: {sesi.catatan_admin or 'Tidak ada keterangan.'}\n\n"
            f"Silakan ajukan ulang atau hubungi admin untuk info lebih lanjut."
        ),
        'done': (
            f"Halo {sesi.user.get_full_name()},\n\n"
            f"Sesi konseling Anda telah ditandai SELESAI.\n"
            f"Terima kasih telah menggunakan layanan konseling Lab Psikologi UMKT."
        ),
    }
    try:
        send_mail(
            subject=subjek_map.get(status, 'Update Sesi Konseling'),
            message=pesan_map.get(status, ''),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[sesi.user.email],
            fail_silently=True,
        )
    except Exception:
        pass


# ── ADMIN ACTIONS (bulk) ─────────────────────────────────────────────────────

@admin.action(description='✅ Setujui sesi yang dipilih')
def action_approve(modeladmin, request, queryset):
    updated = queryset.filter(status='pending').update(
        status='approved',
        tanggal_aktual=timezone.now().date(),
    )
    for sesi in queryset.filter(status='approved'):
        kirim_notifikasi(sesi, 'approved')
    modeladmin.message_user(
        request,
        f'{updated} sesi berhasil disetujui.',
        messages.SUCCESS,
    )


@admin.action(description='❌ Tolak sesi yang dipilih')
def action_reject(modeladmin, request, queryset):
    updated = queryset.filter(status='pending').update(status='rejected')
    for sesi in queryset.filter(status='rejected'):
        kirim_notifikasi(sesi, 'rejected')
    modeladmin.message_user(
        request,
        f'{updated} sesi ditolak.',
        messages.WARNING,
    )


@admin.action(description='🏁 Tandai selesai')
def action_done(modeladmin, request, queryset):
    updated = queryset.filter(status='approved').update(status='done')
    modeladmin.message_user(
        request,
        f'{updated} sesi ditandai selesai.',
        messages.SUCCESS,
    )


# ── MAIN ADMIN ───────────────────────────────────────────────────────────────

@admin.register(KonselingSession)
class KonselingSessionAdmin(admin.ModelAdmin):

    # ── List view ─────────────────────────────────────
    list_display  = [
        'id', 'nama_klien', 'tujuan', 'tanggal_preferensi',
        'status_badge', 'psikolog', 'tanggal_dibuat', 'aksi_cepat',
    ]
    list_filter   = ['status', 'tujuan', 'tanggal_preferensi']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'keluhan']
    ordering      = ['-created_at']
    date_hierarchy = 'tanggal_preferensi'
    actions       = [action_approve, action_reject, action_done]
    list_per_page = 25

    # ── Detail / change form ───────────────────────────
    readonly_fields = [
        'user', 'tanggal_preferensi', 'waktu_preferensi',
        'tujuan', 'keluhan', 'created_at', 'info_klien',
    ]
    fieldsets = (
        ('📋 Data Klien', {
            'fields': ('info_klien', 'user'),
        }),
        ('📝 Permintaan Klien', {
            'fields': ('tujuan', 'keluhan', 'tanggal_preferensi', 'waktu_preferensi'),
        }),
        ('✅ Keputusan Admin', {
            'fields': (
                'status',
                'tanggal_aktual', 'waktu_aktual',
                'ruangan', 'psikolog',
                'tarif', 'sudah_bayar',
                'catatan_admin',
            ),
        }),
        ('🕒 Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    # ── Custom display columns ─────────────────────────

    @admin.display(description='Klien')
    def nama_klien(self, obj):
        return obj.user.get_full_name() or obj.user.email

    @admin.display(description='Status')
    def status_badge(self, obj):
        warna = {
            'pending':   '#f59e0b',
            'approved':  '#10b981',
            'rejected':  '#ef4444',
            'done':      '#6366f1',
            'cancelled': '#6b7280',
        }
        label = obj.get_status_display()
        color = warna.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color, label,
        )

    @admin.display(description='Dibuat')
    def tanggal_dibuat(self, obj):
        return obj.created_at.strftime('%d %b %Y %H:%M') if obj.created_at else '-'

    @admin.display(description='Info Klien')
    def info_klien(self, obj):
        u = obj.user
        return format_html(
            '<strong>{}</strong><br>'
            'Email: {}<br>'
            'WA: {}<br>'
            'Tipe: {} | NIM/NIP: {}',
            u.get_full_name() or '-',
            u.email,
            u.phone or '-',
            u.get_role_display() if hasattr(u, 'get_role_display') else u.role,
            u.nim_nip or '-',
        )

    @admin.display(description='Aksi')
    def aksi_cepat(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<a href="{}/change/" style="background:#10b981;color:#fff;'
                'padding:3px 10px;border-radius:6px;font-size:11px;'
                'text-decoration:none;margin-right:4px">Review</a>',
                obj.pk,
            )
        return format_html(
            '<span style="color:#9ca3af;font-size:11px">{}</span>',
            obj.get_status_display(),
        )

    def save_model(self, request, obj, form, change):
        """Auto-kirim email saat status berubah."""
        if change:
            try:
                lama = KonselingSession.objects.get(pk=obj.pk)
                if lama.status != obj.status and obj.status in ('approved', 'rejected', 'done'):
                    kirim_notifikasi(obj, obj.status)
            except KonselingSession.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)
