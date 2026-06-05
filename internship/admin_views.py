import json
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from .models import InternshipRequest, InternshipPartner
from django.utils.dateformat import format

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

class InternshipDetailView(AdminRequiredMixin, View):
    def get(self, request, pk):
        req = get_object_or_404(
            InternshipRequest.objects.select_related(
                'student', 'lecturer', 'partner', 'approved_by'
            ).prefetch_related('logs'),
            pk=pk
        )

        logs = [
            {
                'id': log.id,
                'date': format(log.date, 'd M Y'),
                'topic': log.topic,
                'notes': log.notes or '',
                'attachment_url': log.attachment.url if log.attachment else '',
            }
            for log in req.logs.all().order_by('-date', '-created_at')
        ]

        data = {
            'id': req.id,
            'student_name': req.student.get_full_name() or req.student.email,
            'student_email': req.student.email,
            'partner_name': req.partner.name if req.partner else req.partner_name,
            'partner_field': req.partner.field if req.partner else req.partner_field,
            'partner_address': req.partner.address if req.partner else req.partner_address,
            'supervisor_name': req.supervisor_name,
            'supervisor_phone': req.supervisor_phone,
            'lecturer_name': req.lecturer.name if req.lecturer else '-',
            'start_date': format(req.start_date, 'd M Y'),
            'end_date': format(req.end_date, 'd M Y'),
            'status': req.status,
            'status_display': req.get_status_display(),
            'intro_letter_url': req.intro_letter.url if req.intro_letter else '',
            'final_report_url': req.final_report.url if req.final_report else '',
            'assessment_url': req.assessment.url if req.assessment else '',
            'approved_by': req.approved_by.get_full_name() if req.approved_by else '',
            'approved_at': format(req.approved_at, 'd M Y H:i') if req.approved_at else '',
            'created_at': format(req.created_at, 'd M Y H:i'),
            'logs': logs,
        }
        return JsonResponse({'status': 'ok', 'data': data})
    
class InternshipAdminListView(AdminRequiredMixin, View):
    def get(self, request):
        status_filter = request.GET.get('status', 'all')
        qs = InternshipRequest.objects.select_related(
            'student', 'lecturer', 'partner'
        ).order_by('-created_at')

        if status_filter != 'all':
            qs = qs.filter(status=status_filter)

        ctx = {
            'internship_list': qs,
            'status_filter':   status_filter,
            'status_tabs': [
                ('all', 'Semua'), ('pending', 'Menunggu'),
                ('approved', 'Disetujui'), ('ongoing', 'Berjalan'),
                ('completed', 'Selesai'), ('rejected', 'Ditolak'),
            ],
            'internship_stats': {
                'pending':   InternshipRequest.objects.filter(status='pending').count(),
                'ongoing':   InternshipRequest.objects.filter(status__in=['approved','ongoing']).count(),
                'completed': InternshipRequest.objects.filter(status='completed').count(),
                'partners':  InternshipPartner.objects.filter(is_active=True).count(),
            },
        }
        return render(request, 'admin/internship_list.html', ctx)


class InternshipApproveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        req = get_object_or_404(InternshipRequest, pk=pk)

        if req.status != 'pending':
            return JsonResponse({'status': 'error', 'message': 'Hanya request pending yang bisa disetujui.'}, status=400)

        if req.partner and req.partner.quota > 0 and req.partner.quota_remaining == 0:
            return JsonResponse({'status': 'error', 'message': 'Kuota mitra sudah penuh.'}, status=400)

        req.status = 'approved'
        req.approved_by = request.user
        req.approved_at = timezone.now()
        req.save()

        return JsonResponse({'status': 'ok', 'message': 'Pendaftaran disetujui.'})

class InternshipRejectView(AdminRequiredMixin, View):
    def post(self, request, pk):
        req = get_object_or_404(InternshipRequest, pk=pk)

        if req.status != 'pending':
            return JsonResponse({'status': 'error', 'message': 'Hanya request pending yang bisa ditolak.'}, status=400)

        req.status = 'rejected'
        req.approved_by = request.user
        req.approved_at = timezone.now()
        req.save()

        return JsonResponse({'status': 'ok'})


class PartnerAdminListView(AdminRequiredMixin, View):
    def get(self, request):
        ctx = {
            'partner_list': InternshipPartner.objects.order_by('name'),
        }
        return render(request, 'admin/partner_list.html', ctx)


class PartnerCreateView(AdminRequiredMixin, View):
    def post(self, request):
        try:
            body = json.loads(request.body)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)

        name = body.get('name', '').strip()
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Nama instansi wajib diisi.'}, status=400)

        partner = InternshipPartner.objects.create(
            name           = name,
            field          = body.get('field', ''),
            address        = body.get('address', ''),
            contact_person = body.get('contact_person', ''),
            phone          = body.get('phone', ''),
            email          = body.get('email', ''),
            keterangan     = body.get('keterangan', ''),
            quota          = int(body.get('quota', 0)),
        )
        return JsonResponse({
            'status': 'ok',
            'id':     partner.pk,
            'name':   partner.name,
        })


class PartnerEditView(AdminRequiredMixin, View):
    def get(self, request, pk):
        p = get_object_or_404(InternshipPartner, pk=pk)
        return JsonResponse({
            'id': p.pk,
            'name': p.name,
            'field': p.field,
            'address': p.address,
            'contact_person': p.contact_person,
            'phone': p.phone,
            'email': p.email,
            'keterangan': p.keterangan,
            'quota': p.quota,
            'is_active': p.is_active,
        })


    def post(self, request, pk):
        partner = get_object_or_404(InternshipPartner, pk=pk)
        try:
            body = json.loads(request.body)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)

        partner.name           = body.get('name', partner.name).strip()
        partner.field          = body.get('field', partner.field)
        partner.address        = body.get('address', partner.address)
        partner.contact_person = body.get('contact_person', partner.contact_person)
        partner.phone          = body.get('phone', partner.phone)
        partner.email          = body.get('email', partner.email)
        partner.quota          = int(body.get('quota', partner.quota))
        partner.keterangan     = body.get('keterangan', partner.keterangan)
        partner.save()
        return JsonResponse({'status': 'ok'})


class PartnerToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        partner           = get_object_or_404(InternshipPartner, pk=pk)
        partner.is_active = not partner.is_active
        partner.save()
        return JsonResponse({'status': 'ok', 'is_active': partner.is_active})