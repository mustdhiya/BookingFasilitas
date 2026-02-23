# research/views.py
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

import openpyxl

from .models import Lecturer, ResearchTitle, ResearchRequest, GuidanceSession
from practicum.models import Practicum


# ══════════════════════════════════════════════════════════
# MIXIN
# ══════════════════════════════════════════════════════════

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


# ══════════════════════════════════════════════════════════
# PUBLIC VIEWS (User-facing)
# ══════════════════════════════════════════════════════════

class LecturerListView(ListView):
    model = Lecturer
    template_name = 'research/lecturer_list.html'
    context_object_name = 'lecturers'

    def get_queryset(self):
        return Lecturer.objects.filter(is_active=True)


class LecturerDetailView(DetailView):
    model = Lecturer
    template_name = 'research/lecturer_detail.html'


class ResearchTitleListView(ListView):
    model = ResearchTitle
    template_name = 'research/title_list.html'
    context_object_name = 'titles'

    def get_queryset(self):
        return ResearchTitle.objects.filter(
            lecturer_id=self.kwargs['pk'],
            is_active=True
        )

class ResearchRequestCreateView(LoginRequiredMixin, CreateView):
    model = ResearchRequest
    fields = ['lecturer', 'research_title', 'request_type', 'thesis_title', 'proposal']
    login_url = '/login/'

    def form_valid(self, form):
        # Auto-assign student dari user yang login
        form.instance.student = self.request.user
        response = super().form_valid(form)

        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           or self.request.content_type == 'application/json' \
           or 'multipart' in self.request.content_type:
            return JsonResponse({'id': self.object.pk, 'status': 'ok'})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
           or 'multipart' in self.request.content_type:
            return JsonResponse({'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return '/penelitian/#request-saya'


class ResearchRequestDetailView(DetailView):
    model = ResearchRequest
    template_name = 'research/request_detail.html'


# ══════════════════════════════════════════════════════════
# PENELITIAN MAIN PAGE (Module 4 - student view)
# ══════════════════════════════════════════════════════════

class ResearchListView(LoginRequiredMixin, TemplateView):
    template_name = 'penelitianMain.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        ctx  = super().get_context_data(**kwargs)
        user = self.request.user

        lecturers = Lecturer.objects.filter(is_active=True).prefetch_related(
            'research_titles'
        ).order_by('focus', 'name')

        titles = ResearchTitle.objects.filter(is_active=True)

        ctx['lecturers']             = lecturers
        ctx['total_titles']          = titles.count()
        ctx['available_count']       = sum(1 for t in titles if not t.is_full)
        ctx['full_count']            = sum(1 for t in titles if t.is_full)
        ctx['focus_areas']           = Lecturer.objects.filter(is_active=True).values_list('focus', flat=True).distinct()
        ctx['my_requests']           = ResearchRequest.objects.filter(
                                           student=user
                                       ).select_related('research_title', 'lecturer').order_by('-created_at')
        ctx['my_active_request']     = ResearchRequest.objects.filter(
                                           student=user, status__in=['pending', 'approved']
                                       ).first()
        ctx['guidance_sessions']     = GuidanceSession.objects.filter(
                                           request__student=user
                                       ).select_related('request').order_by('-date')
        ctx['user_requested_ids']    = list(
                                           ResearchRequest.objects.filter(student=user)
                                           .values_list('research_title_id', flat=True)
                                       )
        # Dosen yang nama-nya sudah boleh terlihat (sudah ada request approved)
        ctx['visible_lecturer_ids']  = list(
                                           ResearchRequest.objects.filter(student=user, status='approved')
                                           .values_list('lecturer_id', flat=True)
                                       )
        return ctx


# ══════════════════════════════════════════════════════════
# EXPORT EXCEL
# ══════════════════════════════════════════════════════════

@staff_member_required
def export_praktikum(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Jadwal Praktikum"

    headers = ['No', 'Tipe', 'Nama Sesi', 'Dosen', 'Tanggal',
               'Jam Mulai', 'Jam Selesai', 'Ruangan',
               'Kapasitas', 'Terdaftar', 'Status']
    ws.append(headers)

    for i, p in enumerate(Practicum.objects.select_related('lecturer', 'room'), 1):
        ws.append([
            i,
            p.get_type_display() if hasattr(p, 'get_type_display') else '-',
            getattr(p, 'session_name', p.title),
            p.lecturer.name if hasattr(p, 'lecturer') and p.lecturer else '-',
            p.date.strftime('%d/%m/%Y'),
            p.start_time.strftime('%H:%M') if p.start_time else '-',
            p.end_time.strftime('%H:%M') if p.end_time else '-',
            p.room.name if hasattr(p, 'room') and p.room else '-',
            getattr(p, 'capacity', getattr(p, 'max_participants', '-')),
            p.registrations.count() if hasattr(p, 'registrations') else '-',
            'Aktif' if getattr(p, 'is_active', True) else 'Nonaktif',
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="jadwal_praktikum.xlsx"'
    wb.save(response)
    return response


@staff_member_required
def export_dosen(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dosen & Judul Payung"

    headers = ['No', 'Nama Dosen', 'NIP', 'Bidang Fokus',
               'Email', 'No HP', 'Judul Payung', 'Kuota', 'Terpakai', 'Status']
    ws.append(headers)

    i = 1
    for lec in Lecturer.objects.prefetch_related('research_titles'):
        titles = lec.research_titles.all()
        if titles.exists():
            for title in titles:
                ws.append([
                    i, lec.name, lec.nip or '-',
                    lec.get_focus_display(),
                    lec.email or '-', lec.phone or '-',
                    title.title, title.quota, title.slots_used,
                    'Aktif' if title.is_active else 'Nonaktif',
                ])
                i += 1
        else:
            ws.append([
                i, lec.name, lec.nip or '-',
                lec.get_focus_display(),
                lec.email or '-', lec.phone or '-',
                '(belum ada judul payung)', '-', '-',
                'Aktif' if lec.is_active else 'Nonaktif',
            ])
            i += 1

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="dosen_judul_payung.xlsx"'
    wb.save(response)
    return response


@staff_member_required
def export_penelitian(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Request Penelitian"

    headers = ['No', 'Nama Mahasiswa', 'NIM', 'Judul Skripsi',
               'Dosen', 'Judul Payung', 'Tipe', 'Status',
               'Tanggal Request', 'Tanggal Disetujui']
    ws.append(headers)

    for i, req in enumerate(
        ResearchRequest.objects.select_related('student', 'lecturer', 'research_title'), 1
    ):
        ws.append([
            i,
            req.student.get_full_name(),
            getattr(req.student, 'nim_nip', '-') or '-',
            req.thesis_title,
            req.lecturer.name,
            req.research_title.title if req.research_title else 'Individu',
            req.get_request_type_display(),
            req.get_status_display(),
            req.created_at.strftime('%d/%m/%Y'),
            req.approved_at.strftime('%d/%m/%Y') if req.approved_at else '-',
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="request_penelitian.xlsx"'
    wb.save(response)
    return response


# ══════════════════════════════════════════════════════════
# ADMIN CRUD — DOSEN
# ══════════════════════════════════════════════════════════

class DosenCreateView(AdminRequiredMixin, CreateView):
    model = Lecturer
    fields = ['name', 'nip', 'focus', 'email', 'phone', 'bio', 'photo', 'is_active']
    success_url = reverse_lazy('admin_panel')

    def get_success_url(self):
        return reverse_lazy('admin_panel') + '?tab=dosen'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk, 'name': self.object.name})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        errors = '; '.join([f"{k}: {v[0]}" for k, v in form.errors.items()])
        messages.error(self.request, f'Gagal menyimpan dosen: {errors}')
        return redirect(str(reverse_lazy('admin_panel')) + '?tab=dosen')


class DosenUpdateView(AdminRequiredMixin, UpdateView):
    model = Lecturer
    fields = ['name', 'nip', 'focus', 'email', 'phone', 'bio', 'photo', 'is_active']

    def get_success_url(self):
        return reverse_lazy('admin_panel') + '?tab=dosen'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        errors = '; '.join([f"{k}: {v[0]}" for k, v in form.errors.items()])
        messages.error(self.request, f'Gagal update dosen: {errors}')
        return redirect(str(reverse_lazy('admin_panel')) + '?tab=dosen')


class DosenDeleteView(AdminRequiredMixin, DeleteView):
    model = Lecturer

    def get_success_url(self):
        return reverse_lazy('admin_panel') + '?tab=dosen'

    def post(self, request, *args, **kwargs):
        result = super().post(request, *args, **kwargs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        return result


class DosenJsonView(AdminRequiredMixin, View):
    def get(self, request, pk):
        lec = get_object_or_404(Lecturer, pk=pk)
        return JsonResponse({
            'pk':        lec.pk,
            'name':      lec.name,
            'nip':       lec.nip or '',
            'focus':     lec.focus,
            'email':     lec.email or '',
            'phone':     lec.phone or '',
            'bio':       lec.bio or '',
            'is_active': lec.is_active,
            'photo_url': lec.photo.url if lec.photo else '',
        })


# ══════════════════════════════════════════════════════════
# ADMIN CRUD — JUDUL PAYUNG
# ══════════════════════════════════════════════════════════

class JudulCreateView(AdminRequiredMixin, CreateView):
    model = ResearchTitle
    fields = ['lecturer', 'title', 'focus', 'quota', 'description', 'is_active']

    def get_success_url(self):
        return reverse_lazy('admin_panel') + '?tab=dosen'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        errors = '; '.join([f"{k}: {v[0]}" for k, v in form.errors.items()])
        messages.error(self.request, f'Gagal menyimpan judul payung: {errors}')
        return redirect(str(reverse_lazy('admin_panel')) + '?tab=dosen')


class JudulUpdateView(AdminRequiredMixin, UpdateView):
    model = ResearchTitle
    fields = ['lecturer', 'title', 'focus', 'quota', 'description', 'is_active']

    def get_success_url(self):
        return reverse_lazy('admin_panel') + '?tab=dosen'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        errors = '; '.join([f"{k}: {v[0]}" for k, v in form.errors.items()])
        messages.error(self.request, f'Gagal update judul: {errors}')
        return redirect(str(reverse_lazy('admin_panel')) + '?tab=dosen')


class JudulDeleteView(AdminRequiredMixin, DeleteView):
    model = ResearchTitle

    def get_success_url(self):
        return reverse_lazy('admin_panel') + '?tab=dosen'

    def post(self, request, *args, **kwargs):
        result = super().post(request, *args, **kwargs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        return result


class JudulJsonView(AdminRequiredMixin, View):
    def get(self, request, pk):
        t = get_object_or_404(ResearchTitle, pk=pk)
        return JsonResponse({
            'pk':          t.pk,
            'lecturer_id': t.lecturer_id,
            'title':       t.title,
            'focus':       t.focus,
            'quota':       t.quota,
            'description': t.description or '',
            'is_active':   t.is_active,
        })
