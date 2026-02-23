from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from .models import Practicum, PracticumRegistration
from research.models import Lecturer, ResearchTitle, ResearchRequest


# ── Halaman Utama Praktikum (untuk mahasiswa) ──────────────────────────

class PraktikumMainView(LoginRequiredMixin, TemplateView):
    template_name = 'praktikumMain.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Semua jadwal aktif
        ctx['practicum_list'] = Practicum.objects.filter(
            is_active=True
        ).select_related('lecturer', 'room').order_by('date', 'start_time')

        # Jadwal yang sudah didaftarkan user ini
        ctx['my_registrations'] = PracticumRegistration.objects.filter(
            student=user
        ).select_related('practicum', 'practicum__lecturer', 'practicum__room')

        # PK praktikum yang sudah didaftar (untuk cek status di template)
        ctx['registered_ids'] = set(
            PracticumRegistration.objects.filter(
                student=user
            ).values_list('practicum_id', flat=True)
        )

        # Stats ringkas
        ctx['stats'] = {
            'total_jadwal': Practicum.objects.filter(is_active=True).count(),
            'my_pending':   PracticumRegistration.objects.filter(
                                student=user, status='pending').count(),
            'my_approved':  PracticumRegistration.objects.filter(
                                student=user, status='approved').count(),
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

class PracticumRegisterView(LoginRequiredMixin, CreateView):
    model   = PracticumRegistration
    fields  = []   # diisi manual di form_valid
    success_url = reverse_lazy('praktikum-main')

    def post(self, request, *args, **kwargs):
        practicum_id = request.POST.get('practicum_id') or kwargs.get('pk')
        practicum    = get_object_or_404(Practicum, pk=practicum_id, is_active=True)
        is_ajax      = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # Cek sudah daftar
        if PracticumRegistration.objects.filter(
            practicum=practicum, student=request.user
        ).exists():
            if is_ajax:
                return JsonResponse({'status': 'error',
                                     'msg': 'Anda sudah terdaftar.'}, status=400)
            messages.warning(request, 'Anda sudah terdaftar di praktikum ini.')
            return redirect('praktikum-main')

        # Cek penuh
        if practicum.is_full:
            if is_ajax:
                return JsonResponse({'status': 'error',
                                     'msg': 'Praktikum sudah penuh.'}, status=400)
            messages.error(request, 'Praktikum sudah penuh.')
            return redirect('praktikum-main')

        reg = PracticumRegistration.objects.create(
            practicum=practicum,
            student=request.user,
            status='pending'
        )

        if is_ajax:
            return JsonResponse({
                'status': 'ok',
                'msg':    'Pendaftaran berhasil, menunggu persetujuan.',
                'reg_id': reg.pk,
            })

        messages.success(request, 'Pendaftaran berhasil! Menunggu persetujuan.')
        return redirect('praktikum-main')


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
