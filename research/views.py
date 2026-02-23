# research/views.py
from django.views.generic import ListView, DetailView, CreateView
from .models import Lecturer, ResearchTitle, ResearchRequest


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


class ResearchRequestCreateView(CreateView):
    model = ResearchRequest
    template_name = 'research/request_form.html'
    fields = ['lecturer', 'research_title', 'request_type', 'thesis_title', 'proposal']


class ResearchRequestDetailView(DetailView):
    model = ResearchRequest
    template_name = 'research/request_detail.html'


import openpyxl
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from .models import Lecturer, ResearchTitle, ResearchRequest
from practicum.models import Practicum


@staff_member_required
def export_praktikum(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Jadwal Praktikum"

    # Header
    headers = ['No', 'Tipe', 'Nama Sesi', 'Dosen', 'Tanggal',
               'Jam Mulai', 'Jam Selesai', 'Ruangan',
               'Kapasitas', 'Terdaftar', 'Status']
    ws.append(headers)

    for i, p in enumerate(Practicum.objects.select_related('lecturer', 'room'), 1):
        ws.append([
            i,
            p.get_type_display(),
            p.session_name,
            p.lecturer.name,
            p.date.strftime('%d/%m/%Y'),
            p.start_time.strftime('%H:%M'),
            p.end_time.strftime('%H:%M'),
            p.room.name,
            p.capacity,
            p.registered_count,
            'Aktif' if p.is_active else 'Nonaktif',
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
                    i,
                    lec.name,
                    lec.nip or '-',
                    lec.get_focus_display(),
                    lec.email or '-',
                    lec.phone or '-',
                    title.title,
                    title.quota,
                    title.slots_used,
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
        ResearchRequest.objects.select_related(
            'student', 'lecturer', 'research_title'
        ), 1
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

# konseling/views.py (atau research/views.py)
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from .models import Lecturer, ResearchTitle


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


# ── Dosen ──────────────────────────────────────────────────────────────

class DosenCreateView(AdminRequiredMixin, CreateView):
    model = Lecturer
    fields = ['name', 'nip', 'focus', 'email', 'phone', 'bio', 'photo', 'is_active']
    success_url = reverse_lazy('admin-panel')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Kalau request AJAX, kembalikan JSON
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)


class DosenUpdateView(AdminRequiredMixin, UpdateView):
    model = Lecturer
    fields = ['name', 'nip', 'focus', 'email', 'phone', 'bio', 'photo', 'is_active']
    success_url = reverse_lazy('admin-panel')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)


class DosenDeleteView(AdminRequiredMixin, DeleteView):
    model = Lecturer
    success_url = reverse_lazy('admin-panel')

    def post(self, request, *args, **kwargs):
        result = super().post(request, *args, **kwargs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        return result


# ── Judul Payung ────────────────────────────────────────────────────────

class JudulCreateView(AdminRequiredMixin, CreateView):
    model = ResearchTitle
    fields = ['lecturer', 'title', 'focus', 'quota', 'description', 'is_active']
    success_url = reverse_lazy('admin-panel')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)


class JudulUpdateView(AdminRequiredMixin, UpdateView):
    model = ResearchTitle
    fields = ['lecturer', 'title', 'focus', 'quota', 'description', 'is_active']
    success_url = reverse_lazy('admin-panel')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)


class JudulDeleteView(AdminRequiredMixin, DeleteView):
    model = ResearchTitle
    success_url = reverse_lazy('admin-panel')

    def post(self, request, *args, **kwargs):
        result = super().post(request, *args, **kwargs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        return result
