import json
from django.utils import timezone
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from .models import InternshipRequest, InternshipLog, InternshipPartner
from research.models import Lecturer


class InternshipListView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        partners_qs = InternshipPartner.objects.filter(is_active=True)

        # Sertakan info kuota di setiap partner
        partners_data = []
        for p in partners_qs:
            partners_data.append({
                'id':             p.id,
                'name':           p.name,
                'field':          p.field,
                'contact_person': p.contact_person,
                'phone':          p.phone,
                'quota':          p.quota,
                'quota_remaining': p.quota_remaining,   # None = unlimited
                'quota_status':   p.quota_status,       # full/limited/available/unlimited
                'accepted_count': p.accepted_count,
                'quota_percentage': p.quota_percentage,
            })

        ctx = {
            'partners':            partners_data,
            'my_requests':         InternshipRequest.objects.filter(student=user).select_related('lecturer', 'partner'),
            'my_active_request':   InternshipRequest.objects.filter(
                                       student=user, status__in=['pending', 'approved', 'ongoing']
                                   ).first(),
            'internship_logs':     InternshipLog.objects.filter(
                                       request__student=user,
                                       request__status__in=['approved', 'ongoing', 'completed']
                                   ).select_related('request').order_by('-date'),
            'lecturers':           Lecturer.objects.filter(is_active=True),
        }
        ctx['my_requests'] = InternshipRequest.objects.filter(
            student=request.user
        ).select_related('lecturer', 'partner').order_by('-created_at')
        return render(request, 'internship/list.html', ctx)


class PartnerQuotaView(LoginRequiredMixin, View):
    """Endpoint polling kuota realtime — dipanggil JS setiap 30 detik."""
    def get(self, request):
        partners = InternshipPartner.objects.filter(is_active=True).values(
            'id', 'quota', 'quota_per_batch'
        )
        data = []
        for p in partners:
            obj = InternshipPartner.objects.get(id=p['id'])
            data.append({
                'id':               obj.id,
                'quota_remaining':  obj.quota_remaining,
                'quota_status':     obj.quota_status,
                'accepted_count':   obj.accepted_count,
                'quota_percentage': obj.quota_percentage,
            })
        return JsonResponse({'partners': data, 'ts': timezone.now().isoformat()})


class InternshipCreateView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user

        if InternshipRequest.objects.filter(
            student=user, status__in=['pending', 'approved', 'ongoing']
        ).exists():
            return JsonResponse({'status': 'error', 'message': 'Kamu sudah punya magang aktif.'}, status=400)

        partner_id = request.POST.get('partner')
        if partner_id:
            partner = get_object_or_404(InternshipPartner, id=partner_id, is_active=True)
            # Cek kuota saat submit (double-check server-side)
            if partner.quota > 0 and partner.quota_remaining == 0:
                return JsonResponse({'status': 'error', 'message': 'Kuota mitra ini sudah penuh.'}, status=400)

        lecturer_id  = request.POST.get('lecturer')
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
        return JsonResponse({'status': 'ok', 'id': req.id, 'message': 'Pendaftaran berhasil dikirim!'})


class InternshipLogCreateView(LoginRequiredMixin, View):
    def post(self, request):
        req = InternshipRequest.objects.filter(
            student=request.user, status__in=['approved', 'ongoing']
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
        return JsonResponse({
            'status': 'ok', 'id': log.id,
            'topic': log.topic,
            'date':  log.date.strftime('%d %b %Y'),
            'notes': log.notes,
        })


class InternshipLogDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        log = get_object_or_404(InternshipLog, pk=pk, request__student=request.user)
        log.delete()
        return JsonResponse({'status': 'ok'})


class InternshipUploadView(LoginRequiredMixin, View):
    def post(self, request):
        req_id = request.POST.get('request_id')
        req = get_object_or_404(InternshipRequest, id=req_id, student=request.user)
        if request.FILES.get('final_report'):
            req.final_report = request.FILES['final_report']
        if request.FILES.get('assessment'):
            req.assessment = request.FILES['assessment']
        req.save()
        return JsonResponse({'status': 'ok'})