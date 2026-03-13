from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from .models import Practicum, PracticumRegistration
from research.models import Lecturer, ResearchTitle, ResearchRequest
from django.views import View

# ── Halaman Utama Praktikum (untuk mahasiswa) ──────────────────────────

class PraktikumMainView(LoginRequiredMixin, TemplateView):
    template_name = 'praktikumMain.html'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        user = self.request.user

        # Semua jadwal aktif
        ctx['practicum_list'] = Practicum.objects.filter(
            is_active=True
        ).select_related('lecturer', 'room').order_by('date', 'start_time')

        # Registrasi aktif user (exclude cancelled)
        my_regs = PracticumRegistration.objects.filter(
            student=user,
            status__in=['pending', 'approved', 'waitlist']
        ).select_related('practicum', 'practicum__lecturer', 'practicum__room')

        ctx['my_registrations']    = my_regs
        ctx['registered_ids']      = set(my_regs.values_list('practicum_id', flat=True))
        ctx['has_any_registration'] = my_regs.exists()  # ← lock tombol jadwal lain

        # Stats ringkas
        ctx['stats'] = {
            'total_jadwal': Practicum.objects.filter(is_active=True).count(),
            'my_pending':   my_regs.filter(status='pending').count(),
            'my_approved':  my_regs.filter(status='approved').count(),
        }

        return ctx



# ── Halaman Utama Penelitian (untuk mahasiswa) ─────────────────────────

class PenelitianMainView(LoginRequiredMixin, TemplateView):
    template_name = 'penelitianMain.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Daftar dosen aktif + judul payung aktif
        ctx['lecturer_list'] = Lecturer.objects.filter(
            is_active=True
        ).prefetch_related(
            'research_titles'
        ).order_by('name')

        # Judul payung yang masih tersedia slot
        ctx['available_titles'] = ResearchTitle.objects.filter(
            is_active=True
        ).select_related('lecturer').order_by('lecturer__name')

        # Request penelitian milik user ini
        ctx['my_requests'] = ResearchRequest.objects.filter(
            student=user
        ).select_related('lecturer', 'research_title').order_by('-created_at')

        # Apakah user sudah punya request aktif (pending/approved)
        ctx['has_active_request'] = ResearchRequest.objects.filter(
            student=user,
            status__in=['pending', 'approved']
        ).exists()

        # Stats
        ctx['stats'] = {
            'total_dosen':  Lecturer.objects.filter(is_active=True).count(),
            'total_judul':  ResearchTitle.objects.filter(is_active=True).count(),
            'my_pending':   ResearchRequest.objects.filter(
                                student=user, status='pending').count(),
            'my_approved':  ResearchRequest.objects.filter(
                                student=user, status='approved').count(),
        }

        return ctx


# ── Daftar Praktikum (API-style, bisa dipakai AJAX) ────────────────────

class PracticumListView(LoginRequiredMixin, ListView):
    model = Practicum
    template_name = 'praktikumMain.html'   # fallback jika diakses langsung
    context_object_name = 'practicum_list'

    def get_queryset(self):
        return Practicum.objects.filter(
            is_active=True
        ).select_related('lecturer', 'room').order_by('date', 'start_time')


class PracticumDetailView(LoginRequiredMixin, DetailView):
    model = Practicum
    template_name = 'praktikumMain.html'
    context_object_name = 'practicum'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        p    = self.get_object()
        ctx['already_registered'] = PracticumRegistration.objects.filter(
            practicum=p, student=user
        ).exists()
        ctx['registrations'] = p.registrations.filter(
            status='approved'
        ).select_related('student')
        return ctx


# ── Daftar ke Praktikum ────────────────────────────────────────────────
import json
from django.views import View

class PracticumRegisterView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data         = json.loads(request.body)
            practicum_id = data.get('practicum')
        except (json.JSONDecodeError, ValueError):
            practicum_id = request.POST.get('practicum_id')

        practicum = get_object_or_404(Practicum, pk=practicum_id, is_active=True)

        # ① Cek sudah daftar di jadwal INI
        if PracticumRegistration.objects.filter(
            practicum=practicum, student=request.user
        ).exists():
            return JsonResponse(
                {'status': 'error', 'msg': 'Anda sudah terdaftar di jadwal ini.'},
                status=400
            )

        # ② Cek sudah daftar di jadwal MANAPUN (1x saja boleh)
        if PracticumRegistration.objects.filter(
            student=request.user,
            status__in=['pending', 'approved', 'waitlist']
        ).exists():
            return JsonResponse(
                {'status': 'error', 'msg': 'Anda sudah terdaftar di jadwal lain. Hanya 1 jadwal per periode.'},
                status=400
            )

        status = 'waitlist' if practicum.is_full else 'pending'

        reg = PracticumRegistration.objects.create(
            practicum=practicum,
            student=request.user,
            status=status,
        )

        return JsonResponse({
            'id':     reg.pk,
            'status': reg.status,
            'msg':    'Masuk waitlist.' if status == 'waitlist' else F'Pendaftaran berhasil!',
        })


# ── Batal Daftar ───────────────────────────────────────────────────────

class PracticumCancelView(LoginRequiredMixin, DetailView):
    model = PracticumRegistration

    def post(self, request, pk):
        reg     = get_object_or_404(PracticumRegistration, pk=pk, student=request.user)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if reg.status not in ('pending',):
            if is_ajax:
                return JsonResponse({'status': 'error',
                                     'msg': 'Tidak bisa dibatalkan.'}, status=400)
            messages.error(request, 'Pendaftaran tidak bisa dibatalkan.')
            return redirect('praktikum-main')

        reg.status = 'cancelled'
        reg.save()

        if is_ajax:
            return JsonResponse({'status': 'ok', 'msg': 'Pendaftaran dibatalkan.'})

        messages.info(request, 'Pendaftaran dibatalkan.')
        return redirect('praktikum-main')


# ── Request Penelitian ─────────────────────────────────────────────────

class PenelitianRequestView(LoginRequiredMixin, CreateView):
    model   = ResearchRequest
    fields  = []
    success_url = reverse_lazy('penelitian-main')

    def post(self, request, *args, **kwargs):
        is_ajax    = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        lecturer   = get_object_or_404(Lecturer, pk=request.POST.get('lecturer_id'))
        title_id   = request.POST.get('research_title_id')
        res_title  = get_object_or_404(ResearchTitle, pk=title_id) if title_id else None
        thesis     = request.POST.get('thesis_title', '').strip()

        # Cek sudah punya request aktif
        if ResearchRequest.objects.filter(
            student=request.user,
            status__in=['pending', 'approved']
        ).exists():
            msg = 'Anda sudah memiliki request penelitian aktif.'
            if is_ajax:
                return JsonResponse({'status': 'error', 'msg': msg}, status=400)
            messages.warning(request, msg)
            return redirect('penelitian-main')

        # Cek kuota judul payung
        if res_title and res_title.is_full:
            msg = 'Kuota judul payung ini sudah penuh.'
            if is_ajax:
                return JsonResponse({'status': 'error', 'msg': msg}, status=400)
            messages.error(request, msg)
            return redirect('penelitian-main')

        req = ResearchRequest.objects.create(
            student=request.user,
            lecturer=lecturer,
            research_title=res_title,
            thesis_title=thesis,
            status='pending',
        )

        if is_ajax:
            return JsonResponse({
                'status': 'ok',
                'msg':    'Request penelitian berhasil dikirim.',
                'req_id': req.pk,
            })

        messages.success(request, 'Request penelitian berhasil dikirim!')
        return redirect('penelitian-main')
    
# ── Live Slot Data (AJAX polling) ──────────────────────────────────────

class PracticumSlotView(LoginRequiredMixin, View):
    """Return live slot data untuk semua/satu jadwal + status registrasi user"""

    def get(self, request, pk=None):
        user = request.user
        registered_ids = set(
            PracticumRegistration.objects.filter(
                student=user,
                status__in=['pending', 'approved', 'waitlist']
            ).values_list('practicum_id', flat=True)
        )
        has_any = bool(registered_ids)

        if pk:
            p = get_object_or_404(Practicum, pk=pk)
            return JsonResponse({
                'id':               p.pk,
                'registered_count': p.registered_count,
                'capacity':         p.capacity,
                'fill_percentage':  p.fill_percentage,
                'is_full':          p.is_full,
                'is_almost_full':   p.is_almost_full,
                'user_registered':  p.pk in registered_ids,
                'user_has_any':     has_any,
            })

        data = []
        for p in Practicum.objects.filter(is_active=True):
            data.append({
                'id':               p.pk,
                'registered_count': p.registered_count,
                'capacity':         p.capacity,
                'fill_percentage':  p.fill_percentage,
                'is_full':          p.is_full,
                'is_almost_full':   p.is_almost_full,
                'user_registered':  p.pk in registered_ids,
                'user_has_any':     has_any,
            })
        return JsonResponse({'slots': data})

class PracticumPesertaView(LoginRequiredMixin, View):
    def get(self, request, pk):
        practicum = get_object_or_404(Practicum, pk=pk)
        registrations = PracticumRegistration.objects.filter(
            practicum=practicum,
            status__in=['pending', 'approved', 'waitlist']
        ).select_related('student')

        peserta = []
        for reg in registrations:
            peserta.append({
                'id':            reg.pk,
                'name':          reg.student.get_full_name() or reg.student.username,
                'nim':           getattr(reg.student, 'nim', '') or '',
                'email':         reg.student.email,
                'prodi':         getattr(reg.student, 'prodi', '') or '-',
                'status':        reg.status,
                'registered_at': reg.created_at.strftime('%d %b %Y'),
                'attendance':    float(reg.attendance_percentage),
            })

        return JsonResponse({
            'practicum': str(practicum),
            'peserta':   peserta,
            'total':     len(peserta),
        })
class PracticumApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        reg    = get_object_or_404(PracticumRegistration, pk=pk)
        action = request.POST.get('action') or json.loads(request.body).get('action')

        if action == 'approve':
            reg.status = 'approved'
            reg.save()
            return JsonResponse({'status': 'ok', 'msg': f'{reg.student.username} disetujui.'})
        elif action == 'reject':
            reg.status = 'cancelled'
            reg.save()
            return JsonResponse({'status': 'ok', 'msg': f'{reg.student.username} ditolak.'})

        return JsonResponse({'status': 'error', 'msg': 'Aksi tidak valid.'}, status=400)
