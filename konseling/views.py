# konseling/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, View, TemplateView  # ← TemplateView ada di sini
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from .models import KonselingSession


# ══════════════════════════════════════════════════════════════════════════════
# MIXIN
# ══════════════════════════════════════════════════════════════════════════════

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or getattr(self.request.user, 'role', '') == 'admin'


# ══════════════════════════════════════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════════════════════════════════════

def kirim_email_status(sesi):
    pesan = {
        'approved': (
            f"Sesi konseling Anda DISETUJUI.\n"
            f"Tanggal : {sesi.tanggal_aktual}\n"
            f"Pukul   : {sesi.waktu_aktual}\n"
            f"Ruangan : {sesi.ruangan or '-'}\n"
            f"Psikolog: {sesi.psikolog or '-'}\n"
            f"Catatan : {sesi.catatan_admin or '-'}"
        ),
        'rejected': (
            f"Pengajuan konseling Anda DITOLAK.\n"
            f"Alasan: {sesi.catatan_admin or 'Tidak ada keterangan.'}\n"
            f"Silakan ajukan kembali atau hubungi admin."
        ),
        'done': "Sesi konseling Anda telah selesai. Terima kasih.",
    }
    subyek = {
        'approved': '[Lab Psikologi] Sesi Konseling Disetujui',
        'rejected': '[Lab Psikologi] Sesi Konseling Ditolak',
        'done':     '[Lab Psikologi] Sesi Konseling Selesai',
    }
    if sesi.status in pesan:
        send_mail(
            subject=subyek[sesi.status],
            message=pesan[sesi.status],
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[sesi.user.email],
            fail_silently=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# USER VIEWS
# ══════════════════════════════════════════════════════════════════════════════

class KonselingPageView(LoginRequiredMixin, TemplateView):
    template_name = 'konseling/index.html'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['is_umkt']   = getattr(user, 'role', '') == 'umkt'
        ctx['sesi_list'] = KonselingSession.objects.filter(
            user=user
        ).order_by('-created_at')[:5]
        return ctx


class KonselingSubmitView(LoginRequiredMixin, View):

    def post(self, request):
        user = request.user

        if not getattr(user, 'is_verified', False):
            return JsonResponse(
                {'ok': False, 'msg': 'Akun Anda belum diverifikasi.'},
                status=403
            )

        tanggal_pref = request.POST.get('tanggal_preferensi')
        waktu_pref   = request.POST.get('waktu_preferensi')
        tujuan       = request.POST.get('tujuan')
        keluhan      = request.POST.get('keluhan', '').strip()
        consent      = request.POST.get('consent')

        errors = {}
        if not tanggal_pref: errors['tanggal_preferensi'] = 'Tanggal preferensi wajib diisi.'
        if not waktu_pref:   errors['waktu_preferensi']   = 'Waktu preferensi wajib diisi.'
        if not tujuan:       errors['tujuan']              = 'Tujuan konseling wajib dipilih.'
        if not keluhan:      errors['keluhan']             = 'Keluhan wajib diisi.'
        if not consent:      errors['consent']             = 'Anda harus menyetujui informed consent.'

        if errors:
            return JsonResponse({'ok': False, 'errors': errors}, status=400)

        if KonselingSession.objects.filter(user=user, status='pending').exists():
            return JsonResponse({
                'ok':  False,
                'msg': 'Anda masih memiliki sesi yang menunggu persetujuan.'
            }, status=400)

        sesi = KonselingSession.objects.create(
            user               = user,
            tanggal_preferensi = tanggal_pref,
            waktu_preferensi   = waktu_pref,
            tujuan             = tujuan,
            keluhan            = keluhan,
            status             = 'pending',
        )

        try:
            send_mail(
                subject=f'[Konseling] Pengajuan Baru #{sesi.pk} — {user.get_full_name()}',
                message=(
                    f"Pengajuan baru dari {user.get_full_name()} ({user.email})\n"
                    f"Tujuan  : {sesi.get_tujuan_display()}\n"
                    f"Tanggal : {tanggal_pref} pukul {waktu_pref}\n"
                    f"Keluhan : {keluhan[:200]}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=True,
            )
        except Exception:
            pass

        return JsonResponse({
            'ok':  True,
            'msg': 'Pengajuan berhasil dikirim. Admin akan menghubungi Anda.',
            'id':  sesi.pk,
        })

    def get(self, request):
        return redirect('konseling')


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN VIEWS
# ══════════════════════════════════════════════════════════════════════════════
from accounts.models import User

class AdminPanelView(AdminRequiredMixin, TemplateView):
    template_name = 'admin.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # ── Konseling data ────────────────────────────────────────────
        status_k = self.request.GET.get('status')
        q_k      = self.request.GET.get('q', '')

        qs_konseling = KonselingSession.objects.select_related('user').order_by('-created_at')
        if status_k and status_k != 'all':
            qs_konseling = qs_konseling.filter(status=status_k)
        if q_k:
            qs_konseling = qs_konseling.filter(
                Q(user__first_name__icontains=q_k) |
                Q(user__last_name__icontains=q_k)  |
                Q(user__email__icontains=q_k)       |
                Q(keluhan__icontains=q_k)
            )

        ctx['sesi_list']     = qs_konseling[:50]
        ctx['stats']         = {
            'pending':  KonselingSession.objects.filter(status='pending').count(),
            'approved': KonselingSession.objects.filter(status='approved').count(),
            'done':     KonselingSession.objects.filter(status='done').count(),
            'rejected': KonselingSession.objects.filter(status='rejected').count(),
            'total':    KonselingSession.objects.count(),
        }
        ctx['status_filter'] = status_k or 'all'
        ctx['status_tabs']   = [
            ('all',       'Semua'),
            ('pending',   'Menunggu'),
            ('approved',  'Disetujui'),
            ('done',      'Selesai'),
            ('rejected',  'Ditolak'),
            ('cancelled', 'Dibatalkan'),
        ]
        ctx['q'] = q_k

        # ── Akun data ─────────────────────────────────────────────────
        ctx['user_list'] = User.objects.exclude(is_superuser=True).order_by('-created_at')

        ctx['akun_stats'] = {
            'pending':  User.objects.exclude(is_superuser=True).filter(is_active=False, is_verified=False).count(),
            'active':   User.objects.exclude(is_superuser=True).filter(is_active=True, is_verified=True).count(),
            'inactive': User.objects.exclude(is_superuser=True).filter(is_active=False, is_verified=True).count(),
            'total':    User.objects.exclude(is_superuser=True).count(),
        }
        ctx['akun_status_filter'] = 'all'
        ctx['akun_status_tabs'] = [
            ('all',      'Semua'),
            ('pending',  'Menunggu Verifikasi'),
            ('active',   'Aktif & Terverifikasi'),
            ('rejected', 'Nonaktif'),
        ]

        return ctx



class AdminKonselingListView(AdminRequiredMixin, ListView):
    model               = KonselingSession
    template_name       = 'admin/manaKonselingAdmin.html'
    context_object_name = 'sesi_list'
    paginate_by         = 20

    def get_queryset(self):
        qs     = KonselingSession.objects.select_related('user').order_by('-created_at')
        status = self.request.GET.get('status')
        q      = self.request.GET.get('q')
        if status and status != 'all':
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q)  |
                Q(user__email__icontains=q)       |
                Q(keluhan__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stats'] = {
            'pending':  KonselingSession.objects.filter(status='pending').count(),
            'approved': KonselingSession.objects.filter(status='approved').count(),
            'done':     KonselingSession.objects.filter(status='done').count(),
            'rejected': KonselingSession.objects.filter(status='rejected').count(),
            'total':    KonselingSession.objects.count(),
        }
        ctx['status_filter'] = self.request.GET.get('status', 'all')
        ctx['status_tabs']   = [
            ('all',       'Semua'),
            ('pending',   'Menunggu'),
            ('approved',  'Disetujui'),
            ('done',      'Selesai'),
            ('rejected',  'Ditolak'),
            ('cancelled', 'Dibatalkan'),
        ]
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class AdminKonselingDetailView(AdminRequiredMixin, DetailView):
    model               = KonselingSession
    template_name       = 'admin/manaKonselingAdmin.html'
    context_object_name = 'sesi'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['mode'] = 'detail'
        return ctx


class AdminKonselingAksiView(AdminRequiredMixin, View):

    def post(self, request, pk):
        sesi    = get_object_or_404(KonselingSession, pk=pk)
        aksi    = request.POST.get('aksi')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if aksi == 'approve' and sesi.status == 'pending':
            sesi.status         = 'approved'
            sesi.tanggal_aktual = request.POST.get('tanggal_aktual') or sesi.tanggal_preferensi
            sesi.waktu_aktual   = request.POST.get('waktu_aktual')   or sesi.waktu_preferensi
            sesi.ruangan        = request.POST.get('ruangan', '')
            sesi.psikolog       = request.POST.get('psikolog', '')
            sesi.catatan_admin  = request.POST.get('catatan_admin', '')
            sesi.tarif          = request.POST.get('tarif') or getattr(sesi, 'tarif', None)
            sesi.save()
            kirim_email_status(sesi)
            msg = 'Sesi berhasil disetujui dan email notifikasi terkirim.'

        elif aksi == 'reject' and sesi.status == 'pending':
            sesi.status        = 'rejected'
            sesi.catatan_admin = request.POST.get('catatan_admin', '')
            sesi.save()
            kirim_email_status(sesi)
            msg = 'Sesi ditolak dan klien telah diberitahu.'

        elif aksi == 'done' and sesi.status == 'approved':
            sesi.status = 'done'
            sesi.save()
            kirim_email_status(sesi)
            msg = 'Sesi ditandai selesai.'

        elif aksi == 'cancel':
            sesi.status = 'cancelled'
            sesi.save()
            msg = 'Sesi dibatalkan.'

        else:
            msg = 'Aksi tidak valid atau status tidak sesuai.'
            if is_ajax:
                return JsonResponse({'ok': False, 'msg': msg}, status=400)
            messages.error(request, msg)
            return redirect('admin_panel')

        if is_ajax:
            return JsonResponse({
                'ok':     True,
                'msg':    msg,
                'status': sesi.status,
                'label':  sesi.get_status_display(),
            })

        messages.success(request, msg)
        return redirect('admin_panel')
