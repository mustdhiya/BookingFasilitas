# konseling/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, View, TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Avg, Count, Q
import json

from internship.models import InternshipPartner, InternshipRequest
from .models import KonselingSession
from accounts.models import User
from practicum.models import Practicum

from research.models import GuidanceSession, Lecturer, ResearchTitle, ResearchRequest  

class ResearchListView(LoginRequiredMixin, TemplateView):
    template_name = 'penelitianMain.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        titles = ResearchTitle.objects.all().order_by('title')

        ctx['research_titles']       = titles
        ctx['available_count']       = sum(1 for t in titles if t.requests.count() < t.max_students)
        ctx['full_count']            = sum(1 for t in titles if t.requests.count() >= t.max_students)
        ctx['focus_areas']           = titles.values_list('focus_area', flat=True).distinct()
        ctx['my_requests']           = ResearchRequest.objects.filter(student=user).select_related('research_title')
        ctx['my_active_request']     = ResearchRequest.objects.filter(student=user, status__in=['pending','approved']).first()
        ctx['guidance_sessions']     = GuidanceSession.objects.filter(request__student=user).select_related('request__research_title').order_by('-session_date')
        ctx['user_requested_ids'] = list(
                                        ResearchRequest.objects.filter(
                                            student=user,
                                            status__in=['pending', 'approved']  
                                        ).values_list('research_title_id', flat=True)
                                    )
        ctx['user_approved_title_ids'] = list(ResearchRequest.objects.filter(student=user, status='approved').values_list('research_title_id', flat=True))
        return ctx


# ══════════════════════════════════════════════════════════════════════════════
# MIXIN
# ══════════════════════════════════════════════════════════════════════════════

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or getattr(self.request.user, 'role', '') == 'admin'

    # ← Tambahkan ini: kalau AJAX, return JSON bukan redirect
    def handle_no_permission(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'msg': 'Akses ditolak. Login sebagai admin.'}, status=403)
        return super().handle_no_permission()

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

from django.utils import timezone

class KonselingPageView(LoginRequiredMixin, TemplateView):
    template_name = 'konseling/index.html'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        user = self.request.user

        ctx['is_umkt']        = getattr(user, 'user_type', '') == 'umkt'
        ctx['sessions']       = KonselingSession.objects.filter(
                                    user=user
                                ).order_by('-created_at')
        ctx['tujuan_choices'] = KonselingSession.TUJUAN_CHOICES
        ctx['min_date']       = (timezone.now().date() + timezone.timedelta(days=1)).isoformat()
        ctx['tarif']          = {
            'umkt':     'Hubungi Admin',
            'non_umkt': 'Rp 200.000',
        }
        return ctx

    # Delegasi POST ke KonselingSubmitView
    def post(self, request, *args, **kwargs):
        return KonselingSubmitView.as_view()(request, *args, **kwargs)



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

from rooms.models import Room
from accounts.views import AdminOnlyMixin
from django.utils import timezone
from rooms.models import Room, RoomBooking
from tools.models import TestTool, ToolRental

class AdminBadgeMixin:
    """Inject badge count ke semua halaman admin."""
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['admin_badge_peminjaman'] = (
            RoomBooking.objects.filter(status='pending').count() +
            ToolRental.objects.filter(status='pending').count()
        ) or None
        ctx['admin_badge_konseling'] = KonselingSession.objects.filter(status='pending').count() or None
        ctx['admin_badge_akun'] = User.objects.filter(
            is_active=False, is_verified=False
        ).exclude(is_superuser=True).count() or None
        return ctx

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — DASHBOARD KPI (ringan, gantikan AdminPanelView sebagai homepage admin)
# ─────────────────────────────────────────────────────────────────────────────
class AdminDashboardView(AdminOnlyMixin, TemplateView):
    template_name = 'admin/dashAdmin.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect('/login/')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        today = timezone.localdate()

        ctx['stats'] = {
            'peminjaman_pending': RoomBooking.objects.filter(status='pending').count(),
            'tool_pending':       ToolRental.objects.filter(status='pending').count(),
            'konseling_pending':  KonselingSession.objects.filter(status='pending').count(),
            'akun_pending':       User.objects.exclude(is_superuser=True)
                                      .filter(is_active=False, is_verified=False).count(),
            'penelitian_pending': ResearchRequest.objects.filter(status='pending').count(),
        }
        # Preview 5 terbaru — query ringan
        ctx['recent_bookings']  = RoomBooking.objects.select_related('room', 'user')\
                                      .order_by('-created_at')[:5]
        ctx['recent_tools']     = ToolRental.objects.select_related('tool', 'user')\
                                      .order_by('-created_at')[:5]
        ctx['recent_konseling'] = KonselingSession.objects.select_related('user')\
                                      .filter(status='pending').order_by('-created_at')[:5]
        ctx['pending_akun']     = User.objects.exclude(is_superuser=True)\
                                      .filter(is_active=False, is_verified=False)\
                                      .order_by('-created_at')[:5]
        ctx['recent_penelitian'] = ResearchRequest.objects.select_related('student', 'lecturer')\
                                       .filter(status='pending').order_by('-created_at')[:5]
        return ctx


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — PEMINJAMAN (full data, halaman terpisah)
# ─────────────────────────────────────────────────────────────────────────────
class AdminPeminjamanView(AdminOnlyMixin, TemplateView):
    template_name = 'admin/manapemAdmin.html'

    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        today = timezone.localdate()

        room_status    = self.request.GET.get('room_status', 'all')
        room_filter    = self.request.GET.get('room_filter', '')
        room_date      = self.request.GET.get('room_date', '')
        room_search    = self.request.GET.get('room_search', '')
        room_page      = int(self.request.GET.get('room_page', 1))
        tool_status    = self.request.GET.get('tool_status', 'all')
        tool_search    = self.request.GET.get('tool_search', '')
        tool_page      = int(self.request.GET.get('tool_page', 1))
        tool_filter_id = self.request.GET.get('tool_filter_id', '')
        PER_PAGE = 20

        room_qs = RoomBooking.objects.select_related('room', 'user', 'approved_by')\
                             .order_by('-date_start', '-created_at')
        if room_status == 'ongoing':
            room_qs = room_qs.filter(status='approved', date_start__lte=today, date_end__gte=today)
        elif room_status != 'all':
            room_qs = room_qs.filter(status=room_status)
        if room_filter:  room_qs = room_qs.filter(room_id=room_filter)
        if room_date:    room_qs = room_qs.filter(date_start__lte=room_date, date_end__gte=room_date)
        if room_search:
            room_qs = room_qs.filter(
                Q(user__first_name__icontains=room_search) | Q(user__last_name__icontains=room_search) |
                Q(user__email__icontains=room_search)      | Q(room__name__icontains=room_search)
            )

        tool_qs = ToolRental.objects.select_related('tool', 'user', 'approved_by')\
                            .order_by('-date_start', '-created_at')
        if tool_status != 'all':    tool_qs = tool_qs.filter(status=tool_status)
        if tool_filter_id:          tool_qs = tool_qs.filter(tool_id=tool_filter_id)
        if tool_search:
            tool_qs = tool_qs.filter(
                Q(user__first_name__icontains=tool_search) | Q(user__last_name__icontains=tool_search) |
                Q(user__email__icontains=tool_search)      | Q(tool__name__icontains=tool_search)
            )

        from django.core.paginator import Paginator
        room_pag = Paginator(room_qs, PER_PAGE)
        tool_pag = Paginator(tool_qs, PER_PAGE)

        ctx['room_bookings_page'] = room_pag.get_page(room_page)
        ctx['tool_rentals_page']  = tool_pag.get_page(tool_page)
        ctx['room_list']          = Room.objects.filter(is_active=True).order_by('code')
        ctx['tool_list']          = TestTool.objects.filter(is_active=True).order_by('code')
        ctx['peminjaman_stats']   = {
            'pending':     RoomBooking.objects.filter(status='pending').count(),
            'approved':    RoomBooking.objects.filter(status='approved').count(),
            'ongoing':     RoomBooking.objects.filter(status='approved', date_start__lte=today, date_end__gte=today).count(),
            'total_month': RoomBooking.objects.filter(date_start__year=today.year, date_start__month=today.month).count(),
        }
        ctx['tool_stats'] = {
            'pending':  ToolRental.objects.filter(status='pending').count(),
            'approved': ToolRental.objects.filter(status='approved').count(),
            'borrowed': ToolRental.objects.filter(status='borrowed').count(),
            'overdue':  ToolRental.objects.filter(status='borrowed', date_end__lt=today).count(),
        }
        ctx['room_filter_active'] = {'status': room_status, 'room': room_filter, 'date': room_date, 'search': room_search}
        ctx['tool_filter_active'] = {'status': tool_status, 'search': tool_search, 'tool_id': tool_filter_id}
        return ctx


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — PRAKTIKUM & PENELITIAN
# ─────────────────────────────────────────────────────────────────────────────
class AdminPraktikumView(AdminOnlyMixin, TemplateView):
    template_name = 'admin/manaJadwalPraktikumAdmin.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['practicum_list']        = Practicum.objects.select_related('lecturer', 'room').order_by('-date')
        ctx['lecturer_list']         = Lecturer.objects.prefetch_related('research_titles').order_by('name')
        ctx['lecturerlist']          = ctx['lecturer_list']
        ctx['roomlist']              = Room.objects.filter(is_active=True).order_by('name')
        ctx['dosen_list']            = Lecturer.objects.filter(is_active=True).order_by('name')
        ctx['research_request_list'] = ResearchRequest.objects.select_related(
            'student', 'lecturer', 'research_title'
        ).order_by('-created_at')
        ctx['penelitian_stats']      = {'pending': ResearchRequest.objects.filter(status='pending').count()}
        ctx['request_status_tabs']   = [
            ('all', 'Semua'), ('pending', 'Pending'),
            ('approved', 'Disetujui'), ('rejected', 'Ditolak'),
        ]
        return ctx


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — MASTER DATA
# ─────────────────────────────────────────────────────────────────────────────
class AdminMasterView(AdminOnlyMixin, TemplateView):
    template_name = 'admin/MasterDataAdmin.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['room_list']         = Room.objects.order_by('code')
        ctx['active_room_count'] = Room.objects.filter(is_active=True).count()
        ctx['alat_list']         = TestTool.objects.annotate(
            borrow_count=Count('rentals', filter=~Q(rentals__status='cancelled'))
        ).order_by('code')
        ctx['low_stock_count']   = TestTool.objects.filter(stock__lte=10, is_active=True).count()
        ctx['internship_stats'] = {
            'pending':   InternshipRequest.objects.filter(status='pending').count(),
            'ongoing':   InternshipRequest.objects.filter(status__in=['approved', 'ongoing']).count(),
            'completed': InternshipRequest.objects.filter(status='completed').count(),
            'partners':  InternshipPartner.objects.filter(is_active=True).count(),
        }
        return ctx


class AdminPanelView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'admin.html'

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        if not request.GET.get('section'):
            return redirect('/admin-panel/?section=dashboard')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        PER_PAGE = 10

        room_status = self.request.GET.get('room_status', 'all')
        room_filter = self.request.GET.get('room_filter', '')
        room_date   = self.request.GET.get('room_date', '')
        room_search = self.request.GET.get('room_search', '')
        room_page   = int(self.request.GET.get('room_page', 1))

        tool_status    = self.request.GET.get('tool_status', 'all')
        tool_search    = self.request.GET.get('tool_search', '')
        tool_page      = int(self.request.GET.get('tool_page', 1))
        tool_filter_id = self.request.GET.get('tool_filter_id', '')

        internship_status = self.request.GET.get('internship_status', 'all')
        internship_search = self.request.GET.get('internship_search', '')
        internship_page   = int(self.request.GET.get('internship_page', 1))

        room_qs = RoomBooking.objects.select_related('room', 'user', 'approved_by').order_by('-date_start', '-created_at')

        if room_status == 'ongoing':
            room_qs = room_qs.filter(status='approved', date_start__lte=today, date_end__gte=today)
        elif room_status != 'all':
            room_qs = room_qs.filter(status=room_status)

        if room_filter:
            room_qs = room_qs.filter(room_id=room_filter)
        if room_date:
            room_qs = room_qs.filter(date_start__lte=room_date, date_end__gte=room_date)
        if room_search:
            room_qs = room_qs.filter(
                Q(user__first_name__icontains=room_search) |
                Q(user__last_name__icontains=room_search) |
                Q(user__email__icontains=room_search) |
                Q(room__name__icontains=room_search)
            )

        ctx['peminjaman_stats'] = {
            'pending': RoomBooking.objects.filter(status='pending').count(),
            'approved': RoomBooking.objects.filter(status='approved').count(),
            'ongoing': RoomBooking.objects.filter(
                status='approved',
                date_start__lte=today,
                date_end__gte=today,
            ).count(),
            'total_month': RoomBooking.objects.filter(
                date_start__year=today.year,
                date_start__month=today.month,
            ).count(),
        }
        
        from django.core.paginator import Paginator
        from internship.models import InternshipPartner, InternshipRequest, InternshipLog

        room_paginator = Paginator(room_qs, PER_PAGE)
        ctx['room_bookings_page'] = room_paginator.get_page(room_page)
        ctx['room_paginator'] = room_paginator

        tool_qs = ToolRental.objects.select_related('tool', 'user', 'approved_by').order_by('-date_start', '-created_at')

        if tool_status != 'all':
            tool_qs = tool_qs.filter(status=tool_status)
        if tool_search:
            tool_qs = tool_qs.filter(
                Q(user__first_name__icontains=tool_search) |
                Q(user__last_name__icontains=tool_search) |
                Q(user__email__icontains=tool_search) |
                Q(tool__name__icontains=tool_search)
            )
        if tool_filter_id:
            tool_qs = tool_qs.filter(tool_id=tool_filter_id)

        ctx['tool_stats'] = {
            'pending': ToolRental.objects.filter(status='pending').count(),
            'approved': ToolRental.objects.filter(status='approved').count(),
            'borrowed': ToolRental.objects.filter(status='borrowed').count(),
            'overdue': ToolRental.objects.filter(status='borrowed', date_end__lt=today).count(),
        }

        tool_paginator = Paginator(tool_qs, PER_PAGE)
        ctx['tool_rentals_page'] = tool_paginator.get_page(tool_page)
        ctx['tool_paginator'] = tool_paginator

        internship_partner_qs = InternshipPartner.objects.annotate(
            active_interns=Count(
                'internshiprequest',
                filter=Q(internshiprequest__status__in=['approved', 'ongoing'])
            ),
            total_requests=Count('internshiprequest')
        ).order_by('name')

        internship_request_qs = InternshipRequest.objects.select_related(
            'student', 'partner', 'lecturer', 'approved_by'
        ).order_by('-created_at')

        if internship_status != 'all':
            internship_request_qs = internship_request_qs.filter(status=internship_status)

        if internship_search:
            internship_request_qs = internship_request_qs.filter(
                Q(student__first_name__icontains=internship_search) |
                Q(student__last_name__icontains=internship_search) |
                Q(student__email__icontains=internship_search) |
                Q(partner__name__icontains=internship_search) |
                Q(partner_name__icontains=internship_search)
            )

        internship_paginator = Paginator(internship_request_qs, PER_PAGE)
        ctx['internship_requests_page'] = internship_paginator.get_page(internship_page)
        ctx['internship_paginator'] = internship_paginator

        ctx['internship_partners'] = internship_partner_qs
        ctx['internship_stats'] = {
            'partners': InternshipPartner.objects.filter(is_active=True).count(),
            'pending': InternshipRequest.objects.filter(status='pending').count(),
            'approved': InternshipRequest.objects.filter(status='approved').count(),
            'ongoing': InternshipRequest.objects.filter(status='ongoing').count(),
            'completed': InternshipRequest.objects.filter(status='completed').count(),
        }
        ctx['internship_status_tabs'] = [
            ('all', 'Semua'),
            ('pending', 'Pending'),
            ('approved', 'Disetujui'),
            ('ongoing', 'Berjalan'),
            ('completed', 'Selesai'),
            ('rejected', 'Ditolak'),
        ]
        ctx['internship_filter_active'] = {
            'status': internship_status,
            'search': internship_search,
        }

        ctx['room_list'] = Room.objects.filter(is_active=True).order_by('code')
        ctx['tool_list'] = TestTool.objects.filter(is_active=True).order_by('code')

        ctx['room_filter_active'] = {
            'status': room_status,
            'room': room_filter,
            'date': room_date,
            'search': room_search,
        }
        ctx['tool_filter_active'] = {
            'status': tool_status,
            'search': tool_search,
            'tool_id': tool_filter_id,
        }

        ctx['lecturer_list'] = Lecturer.objects.prefetch_related('research_titles').order_by('name')
        ctx['practicum_list'] = Practicum.objects.select_related('lecturer', 'room').order_by('-date')
        ctx['research_request_list'] = ResearchRequest.objects.select_related(
            'student', 'lecturer', 'research_title'
        ).order_by('-created_at')

        ctx['penelitian_stats'] = {
            'pending': ResearchRequest.objects.filter(status='pending').count()
        }
        ctx['request_status_tabs'] = [
            ('all', 'Semua'),
            ('pending', 'Pending'),
            ('approved', 'Disetujui'),
            ('rejected', 'Ditolak'),
        ]

        ctx['active_room_count'] = Room.objects.filter(is_active=True).count()

        ctx['sesi_list'] = KonselingSession.objects.select_related('user').order_by('-created_at')
        ctx['stats'] = {
            'pending': KonselingSession.objects.filter(status='pending').count(),
            'approved': KonselingSession.objects.filter(status='approved').count(),
            'done': KonselingSession.objects.filter(status='done').count(),
            'rejected': KonselingSession.objects.filter(status='rejected').count(),
            'total': KonselingSession.objects.count(),
        }
        ctx['status_tabs'] = [
            ('all', 'Semua'),
            ('pending', 'Menunggu'),
            ('approved', 'Disetujui'),
            ('done', 'Selesai'),
            ('rejected', 'Ditolak'),
            ('cancelled', 'Dibatalkan'),
        ]
        ctx['status_filter'] = 'all'
        ctx['dosen_list'] = Lecturer.objects.filter(is_active=True).order_by('name')

        ctx['akun_stats'] = {
            'pending': User.objects.exclude(is_superuser=True).filter(is_active=False, is_verified=False).count(),
            'active': User.objects.exclude(is_superuser=True).filter(is_active=True, is_verified=True).count(),
            'inactive': User.objects.exclude(is_superuser=True).filter(is_active=False, is_verified=True).count(),
            'total': User.objects.exclude(is_superuser=True).count(),
        }
        ctx['akun_status_filter'] = 'all'
        ctx['akun_status_tabs'] = [
            ('all', 'Semua'),
            ('pending', 'Menunggu Verifikasi'),
            ('active', 'Aktif & Terverifikasi'),
            ('rejected', 'Nonaktif'),
        ]
        ctx['user_list'] = User.objects.exclude(is_superuser=True).select_related('verified_by').order_by('-created_at')

        ctx['alat_list'] = TestTool.objects.annotate(
            borrow_count=Count('rentals', filter=~Q(rentals__status='cancelled'))
        ).order_by('code')
        ctx['internship_stats'] = {
            'pending':   InternshipRequest.objects.filter(status='pending').count(),
            'ongoing':   InternshipRequest.objects.filter(status__in=['approved', 'ongoing']).count(),
            'completed': InternshipRequest.objects.filter(status='completed').count(),
            'partners':  InternshipPartner.objects.filter(is_active=True).count(),
        }
        ctx['low_stock_count'] = TestTool.objects.filter(stock__lte=10, is_active=True).count()
        ctx['lecturerlist'] = ctx['lecturer_list']
        ctx['roomlist'] = Room.objects.filter(is_active=True).order_by('name')

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
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # ── Baca payload: JSON atau form-data ────────────────────────────
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            try:
                data = json.loads(request.body)
            except (ValueError, KeyError):
                return JsonResponse({'ok': False, 'msg': 'Payload JSON tidak valid.'}, status=400)
            # Helper agar akses sama seperti POST
            def get(key, default=''):
                return data.get(key, default)
            files = {}
        else:
            # multipart/form-data (kSubmitSelesai pakai FormData)
            def get(key, default=''):
                return request.POST.get(key, default)
            files = request.FILES

        aksi = get('aksi')

        # ── Approve ──────────────────────────────────────────────────────
        if aksi == 'approve':
            tanggal  = get('tanggal_aktual')
            waktu    = get('waktu_aktual')
            psikolog = get('psikolog').strip()
            ruangan  = get('ruangan').strip()
            tarif    = get('tarif').strip()
            catatan  = get('catatan_admin').strip()

            if not tanggal or not psikolog:
                return JsonResponse({'ok': False, 'msg': 'Tanggal aktual dan psikolog wajib diisi.'})

            sesi.status         = 'approved'
            sesi.tanggal_aktual = tanggal
            sesi.waktu_aktual   = waktu or None
            sesi.psikolog       = psikolog
            sesi.ruangan        = ruangan
            sesi.catatan_admin  = catatan
            if tarif:
                sesi.tarif = tarif
            sesi.save()
            kirim_email_status(sesi)
            return JsonResponse({'ok': True, 'msg': 'Sesi disetujui.', 'status': 'approved', 'label': 'Disetujui'})

        # ── Reject ───────────────────────────────────────────────────────
        elif aksi == 'reject':
            catatan = get('catatan_admin').strip()
            if not catatan:
                return JsonResponse({'ok': False, 'msg': 'Catatan wajib diisi saat menolak.'})
            sesi.status        = 'rejected'
            sesi.alasan_tolak  = catatan
            sesi.catatan_admin = catatan
            sesi.save()
            kirim_email_status(sesi)
            return JsonResponse({'ok': True, 'msg': 'Sesi ditolak.', 'status': 'rejected', 'label': 'Ditolak'})

        # ── Konfirmasi Bayar ─────────────────────────────────────────────
        elif aksi == 'konfirmasi_bayar':
            if not sesi.bukti_bayar:
                return JsonResponse({'ok': False, 'msg': 'Bukti bayar belum ada.'})
            sesi.sudah_bayar       = True
            sesi.bayar_verified_at = timezone.now()
            sesi.bayar_verified_by = request.user
            sesi.save()
            return JsonResponse({'ok': True, 'msg': 'Pembayaran dikonfirmasi lunas.'})

        # ── Selesai ──────────────────────────────────────────────────────
        elif aksi == 'done':
            laporan       = files.get('laporan_pdf')
            dirujuk       = get('dirujuk') == '1'
            cat_rujukan   = get('catatan_rujukan', '').strip()
            catatan_admin = get('catatan_admin', '').strip()

            sesi.status     = 'done'
            sesi.dirujuk    = dirujuk
            sesi.selesai_at = timezone.now()
            if laporan:
                sesi.laporan_pdf = laporan
            if cat_rujukan:
                sesi.catatan_rujukan = cat_rujukan
            if catatan_admin:
                sesi.catatan_admin = catatan_admin
            sesi.save()
            kirim_email_status(sesi)
            return JsonResponse({'ok': True, 'msg': 'Sesi ditandai selesai.', 'status': 'done', 'label': 'Selesai'})

        # ── Upload Bukti ─────────────────────────────────────────────────
        elif aksi == 'upload_bukti':
            if 'bukti_bayar' not in files:
                return JsonResponse({'ok': False, 'msg': 'File bukti bayar wajib diupload.'})
            sesi.bukti_bayar = files['bukti_bayar']
            sesi.save()
            return JsonResponse({'ok': True, 'msg': 'Bukti bayar berhasil diupload.',
                                 'bukti_url': sesi.bukti_bayar.url})

        return JsonResponse({'ok': False, 'msg': f'Aksi tidak dikenali: {aksi}'})
