from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from .models import InternshipRequest, InternshipLog, InternshipPartner
from research.models import Lecturer

class InternshipListView(LoginRequiredMixin, View):
    def get(self, request):
        # user = request.user
        # ctx = {
        #     'my_requests':       InternshipRequest.objects.filter(student=user).select_related('lecturer','partner'),
        #     'my_active_request': InternshipRequest.objects.filter(
        #                              student=user, status__in=['pending','approved','ongoing']
        #                          ).first(),
        #     'my_approved_request': InternshipRequest.objects.filter(
        #                                student=user, status__in=['approved','ongoing']
        #                            ).first(),
        #     'internship_logs':   InternshipLog.objects.filter(
        #                              request__student=user,
        #                              request__status__in=['approved','ongoing','completed']
        #                          ).select_related('request').order_by('-date'),
        #     'partners':  InternshipPartner.objects.filter(is_active=True),
        #     'lecturers': Lecturer.objects.filter(is_active=True),
        # }
        # return render(request, 'internship/list.html', ctx)
        ctx = self.get_dummy_context()
        return render(request, 'internship/list.html', ctx)
        
    def get_dummy_context(self):
        return {
            'partners': [
                {'id': 1, 'name': 'RSUD Abdul Wahab Sjahranie', 'field': 'Psikologi Klinis', 'contact_person': 'Dr. Siti Rahayu', 'phone': '0541-123456'},
                {'id': 2, 'name': 'BNN Provinsi Kalimantan Timur', 'field': 'Psikologi Forensik', 'contact_person': 'Bpk. Ahmad Fauzi', 'phone': '0541-234567'},
                {'id': 3, 'name': 'Dinas Sosial Kota Samarinda', 'field': 'Psikologi Sosial', 'contact_person': 'Ibu Dewi Lestari', 'phone': '0541-345678'},
                {'id': 4, 'name': 'PT Pupuk Kalimantan Timur', 'field': 'Psikologi Industri & Organisasi', 'contact_person': 'HRD Dept.', 'phone': '0548-41202'},
                {'id': 5, 'name': 'Puskesmas Palaran', 'field': 'Psikologi Kesehatan', 'contact_person': 'dr. Hendra Wijaya', 'phone': '0541-456789'},
                {'id': 6, 'name': 'Sekolah Luar Biasa Negeri Samarinda', 'field': 'Psikologi Pendidikan', 'contact_person': 'Ibu Nurul Hidayah', 'phone': '0541-567890'},
            ],
            'my_requests': [
                {
                    'id': 1,
                    'partner_name': 'RSUD Abdul Wahab Sjahranie',
                    'partner_field': 'Psikologi Klinis',
                    'status': 'approved',
                    'status_display': 'Disetujui',
                    'start_date': '01 Mar 2026',
                    'end_date': '31 Mei 2026',
                    'lecturer_name': 'Dr. Rina Kartika, M.Psi',
                    'logs_count': 3,
                    'admin_notes': '',
                },
            ],
            'my_active_request': {
                'partner_name': 'RSUD Abdul Wahab Sjahranie',
                'start_date': '01 Mar 2026',
                'end_date': '31 Mei 2026',
                'status': 'approved',
                'status_display': 'Disetujui',
            },
            'my_approved_request': True,
            'internship_logs': [
                {'id': 1, 'topic': 'Observasi Pasien Bangsal Jiwa', 'date': '01 Mar 2026', 'notes': 'Mengamati interaksi pasien dengan tenaga medis dan mencatat pola perilaku.'},
                {'id': 2, 'topic': 'Asesmen Psikologis Awal', 'date': '02 Mar 2026', 'notes': 'Membantu pelaksanaan wawancara asesmen pada 2 pasien baru.'},
                {'id': 3, 'topic': 'Diskusi Kasus dengan Supervisor', 'date': '03 Mar 2026', 'notes': 'Pembahasan temuan minggu pertama bersama Dr. Siti Rahayu.'},
            ],
            'lecturers': [],
        }




class InternshipCreateView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user

        # Cek sudah ada request aktif
        if InternshipRequest.objects.filter(
            student=user, status__in=['pending','approved','ongoing']
        ).exists():
            return JsonResponse({'status': 'error', 'message': 'Kamu sudah punya magang aktif.'}, status=400)

        lecturer_id  = request.POST.get('lecturer')
        partner_id   = request.POST.get('partner')
        partner_name = request.POST.get('partner_name', '').strip()
        start_date   = request.POST.get('start_date')
        end_date     = request.POST.get('end_date')

        if not lecturer_id or not start_date or not end_date:
            return JsonResponse({'status': 'error', 'message': 'Field wajib belum lengkap.'}, status=400)

        if not partner_id and not partner_name:
            return JsonResponse({'status': 'error', 'message': 'Pilih mitra atau isi nama instansi.'}, status=400)

        req = InternshipRequest.objects.create(
            student          = user,
            lecturer_id      = lecturer_id,
            partner_id       = partner_id or None,
            partner_name     = partner_name if not partner_id else '',
            partner_address  = request.POST.get('partner_address', ''),
            partner_field    = request.POST.get('partner_field', ''),
            supervisor_name  = request.POST.get('supervisor_name', ''),
            supervisor_phone = request.POST.get('supervisor_phone', ''),
            start_date       = start_date,
            end_date         = end_date,
            intro_letter     = request.FILES.get('intro_letter'),
        )
        return JsonResponse({
            'status': 'ok',
            'id':     req.id,
            'message': 'Pendaftaran magang berhasil dikirim!'
        })


class InternshipLogCreateView(LoginRequiredMixin, View):
    def post(self, request):
        req = InternshipRequest.objects.filter(
            student=request.user,
            status__in=['approved', 'ongoing']
        ).first()
        if not req:
            return JsonResponse({'status': 'error', 'message': 'Tidak ada magang aktif.'}, status=403)

        date  = request.POST.get('date')
        topic = request.POST.get('topic', '').strip()
        if not date or not topic:
            return JsonResponse({'status': 'error', 'message': 'Tanggal dan kegiatan wajib diisi.'}, status=400)

        log = InternshipLog.objects.create(
            request    = req,
            date       = date,
            topic      = topic,
            notes      = request.POST.get('notes', ''),
            attachment = request.FILES.get('attachment'),
        )
        log.refresh_from_db()
        return JsonResponse({
            'status': 'ok',
            'id':     log.id,
            'topic':  log.topic,
            'date':   log.date.strftime('%d %b %Y'),
            'notes':  log.notes,
        })


class InternshipLogDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        log = get_object_or_404(InternshipLog, pk=pk, request__student=request.user)
        log.delete()
        return JsonResponse({'status': 'ok'})
class InternshipUploadView(LoginRequiredMixin, View):
    def post(self, request):
        req_id = request.POST.get('request_id')
        req = get_object_or_404(
            InternshipRequest,
            pk=req_id,
            student=request.user,
            status__in=['approved', 'ongoing']
        )
        if request.FILES.get('final_report'):
            req.final_report = request.FILES['final_report']
        if request.FILES.get('assessment'):
            req.assessment = request.FILES['assessment']
        req.save()
        return JsonResponse({'status': 'ok'})
