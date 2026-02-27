from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.views.generic import TemplateView
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Room, RoomBooking, RoomBlockSchedule
from .serializers import RoomSerializer, RoomBookingSerializer, RoomBlockScheduleSerializer
from django.contrib.auth.mixins import LoginRequiredMixin

# HTML Views
class PeminjamRuanganView(LoginRequiredMixin, TemplateView):
    template_name = 'pemriwMain.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        ctx['room_list'] = Room.objects.filter(is_active=True).order_by('code')

        # ← ganti booking_date → date_start
        ctx['recent_bookings'] = RoomBooking.objects.filter(
            user=user
        ).select_related('room').order_by('-date_start')[:5]

        ctx['stats'] = {
            'pending':  RoomBooking.objects.filter(user=user, status='pending').count(),
            'approved': RoomBooking.objects.filter(user=user, status='approved').count(),
        }

        return ctx

# API ViewSets
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.filter(is_active=True)
    serializer_class = RoomSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]


class RoomBookingViewSet(viewsets.ModelViewSet):
    serializer_class = RoomBookingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['laboran', 'dosen']:
            return RoomBooking.objects.all()
        return RoomBooking.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """Get current user's bookings"""
        bookings = RoomBooking.objects.filter(user=request.user).order_by('-created_at')[:5]
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def check_availability(self, request):
        room_id    = request.data.get('room_id')
        date_start = request.data.get('date_start')
        date_end   = request.data.get('date_end') or date_start  # fallback 1 hari

        if not room_id or not date_start:
            return Response({'error': 'room_id dan date_start wajib diisi'}, status=400)

        conflicts = RoomBooking.objects.filter(
            room_id=room_id,
            status__in=['approved', 'pending'],
            date_start__lte=date_end,
            date_end__gte=date_start,
        )

        if conflicts.exists():
            return Response({
                'available': False,
                'message': 'Ruangan sudah dibooking pada rentang tanggal tersebut'
            })

        # Cek blokir rutin
        from datetime import date as dt, timedelta
        from django.utils.dateparse import parse_date
        blocks = RoomBlockSchedule.objects.filter(room_id=room_id, is_active=True)
        d = parse_date(date_start)
        end = parse_date(date_end)
        while d <= end:
            for b in blocks:
                if b.covers_date(d):
                    return Response({
                        'available': False,
                        'message': f'Tanggal {d.strftime("%d %b %Y")} terblokir: {b.name}'
                    })
            d += timedelta(days=1)

        return Response({'available': True, 'message': 'Ruangan tersedia'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve booking (admin only)"""
        booking = self.get_object()
        booking.status = 'approved'
        booking.approved_by = request.user
        booking.approved_at = datetime.now()
        booking.save()
        
        return Response({
            'message': 'Booking berhasil diapprove',
            'booking': self.get_serializer(booking).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def decline(self, request, pk=None):
        """Decline booking (admin only)"""
        booking = self.get_object()
        booking.status = 'declined'
        booking.admin_notes = request.data.get('notes', '')
        booking.save()
        
        return Response({
            'message': 'Booking berhasil ditolak',
            'booking': self.get_serializer(booking).data
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel own booking"""
        booking = self.get_object()
        
        if booking.user != request.user:
            return Response(
                {'error': 'Anda tidak berhak membatalkan booking ini'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if booking.status != 'pending':
            return Response(
                {'error': 'Hanya booking pending yang bisa dibatalkan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = 'cancelled'
        booking.save()
        
        return Response({'message': 'Booking berhasil dibatalkan'})


class RoomBlockScheduleViewSet(viewsets.ModelViewSet):
    queryset = RoomBlockSchedule.objects.filter(is_active=True)
    serializer_class = RoomBlockScheduleSerializer
    permission_classes = [IsAdminUser]


from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib import messages
from django.shortcuts import redirect


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


# ── CRUD Room (Admin) ──────────────────────────────────────────────────

class RoomCreateView(AdminRequiredMixin, CreateView):
    model  = Room
    fields = ['code', 'name', 'capacity', 'description', 'is_active']

    def get_success_url(self):
        return reverse_lazy('admin_panel') + '?tab=masterdata&sub=ruangan'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk,
                                 'name': self.object.name})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        errors = '; '.join([f"{k}: {v[0]}" for k, v in form.errors.items()])
        messages.error(self.request, f'Gagal simpan ruangan: {errors}')
        return redirect(reverse_lazy('admin_panel') + '?tab=masterdata&sub=ruangan')


class RoomUpdateView(AdminRequiredMixin, UpdateView):
    model  = Room
    fields = ['code', 'name', 'capacity', 'description', 'is_active']

    def get_success_url(self):
        return reverse_lazy('admin_panel') + '?tab=masterdata&sub=ruangan'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'id': self.object.pk})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        messages.error(self.request, 'Gagal update ruangan.')
        return redirect(reverse_lazy('admin_panel') + '?tab=masterdata&sub=ruangan')


class RoomDeleteView(AdminRequiredMixin, DeleteView):
    model = Room

    def get_success_url(self):
        return reverse_lazy('admin_panel') + '?tab=masterdata&sub=ruangan'

    def post(self, request, *args, **kwargs):
        result = super().post(request, *args, **kwargs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        return result


class RoomJsonView(AdminRequiredMixin, View):
    """Prefill data untuk edit modal"""
    def get(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        return JsonResponse({
            'pk':          room.pk,
            'code':        room.code,
            'name':        room.name,
            'capacity':    room.capacity,
            'description': room.description or '',
            'is_active':   room.is_active,
        })


# ── Toggle aktif/nonaktif tanpa delete ────────────────────────────────

class RoomToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        room.is_active = not room.is_active
        room.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'is_active': room.is_active})
        return redirect(reverse_lazy('admin_panel') + '?tab=masterdata&sub=ruangan')


from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from rooms.models import RoomBooking          # bukan Reservation
from tools.models import ToolRental           # bukan TestToolLoan
from practicum.models import PracticumRegistration
from research.models import ResearchRequest   # bukan VariableRequest

class RiwayatView(LoginRequiredMixin, TemplateView):
    template_name = 'riwayat/riwayat.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        ctx['room_bookings']  = RoomBooking.objects.filter(user=user).order_by('-created_at')
        ctx['tool_loans']     = ToolRental.objects.filter(user=user).order_by('-created_at')
        ctx['practicum_regs'] = PracticumRegistration.objects.filter(student=user).order_by('-created_at')  # ← student
        ctx['research_reqs']  = ResearchRequest.objects.filter(student=user).order_by('-created_at')        # ← kemungkinan student juga

        return ctx

# rooms/views.py — endpoint booking
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from .forms import RoomBookingForm
from .models import RoomBooking, RoomBlockSchedule, Room
import calendar


class RoomBookingCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = RoomBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.save()
            return JsonResponse({
                'ok': True,
                'msg': (
                    f'Permohonan peminjaman {booking.room.name} '
                    f'({booking.date_start.strftime("%d %b")} – '
                    f'{booking.date_end.strftime("%d %b %Y")}) '
                    f'berhasil dikirim!'
                ),
                'booking_id': booking.pk,
                'duration': booking.duration_days,
            })
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


class RoomCalendarView(View):
    """
    GET /api/rooms/calendar/?year=2026&month=3&room=1
    Return: { "2026-03-01": "free"|"booked"|"partial"|"blocked" }
    """
    def get(self, request):
        try:
            year    = int(request.GET.get('year',  timezone.localdate().year))
            month   = int(request.GET.get('month', timezone.localdate().month))
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Parameter tidak valid'}, status=400)

        room_id = request.GET.get('room')
        _, days_in_month = calendar.monthrange(year, month)

        # Prefetch semua booking dan blokir untuk bulan ini sekali query
        import datetime
        month_start = datetime.date(year, month, 1)
        month_end   = datetime.date(year, month, days_in_month)

        booking_qs = RoomBooking.objects.filter(
            status__in=['pending', 'approved'],
            date_start__lte=month_end,
            date_end__gte=month_start,
        )
        block_qs = RoomBlockSchedule.objects.filter(is_active=True)

        if room_id:
            booking_qs = booking_qs.filter(room_id=room_id)
            block_qs   = block_qs.filter(room_id=room_id)

        blocks   = list(block_qs)
        bookings = list(booking_qs)

        result = {}
        for day in range(1, days_in_month + 1):
            date = datetime.date(year, month, day)
            iso  = date.isoformat()

            # Cek blokir
            if any(b.covers_date(date) for b in blocks):
                result[iso] = 'blocked'
                continue

            # Hitung booking yang overlap hari ini
            count = sum(
                1 for bk in bookings
                if bk.date_start <= date <= bk.date_end
            )
            if count == 0:
                result[iso] = 'free'
            elif count >= 2:
                result[iso] = 'booked'
            else:
                result[iso] = 'partial'

        return JsonResponse(result)


class RoomDayScheduleView(View):
    """
    GET /api/rooms/day-schedule/?date=2026-03-05&room=1
    Return: { "schedules": [...] }
    """
    def get(self, request):
        from django.utils.dateparse import parse_date
        date    = parse_date(request.GET.get('date', '')) or timezone.localdate()
        room_id = request.GET.get('room')

        schedules = []

        # Blokir
        block_qs = RoomBlockSchedule.objects.filter(is_active=True)
        if room_id:
            block_qs = block_qs.filter(room_id=room_id)
        for b in block_qs:
            if b.covers_date(date):
                schedules.append({
                    'title':  b.name,
                    'time':   'Sepanjang hari',
                    'room':   b.room.name,
                    'reason': b.description or '',
                    'type':   'block',
                    'label':  b.get_block_type_display(),
                    'icon':   'event_busy',
                })

        # Booking
        booking_qs = RoomBooking.objects.filter(
            status__in=['pending', 'approved'],
            date_start__lte=date,
            date_end__gte=date,
        ).select_related('room', 'user')
        if room_id:
            booking_qs = booking_qs.filter(room_id=room_id)
        for bk in booking_qs:
            duration = bk.duration_days
            time_str = (
                f'{bk.date_start.strftime("%d %b")} – {bk.date_end.strftime("%d %b %Y")}'
                if not bk.is_single_day else
                bk.date_start.strftime('%d %b %Y')
            )
            schedules.append({
                'title':  bk.purpose[:60] + ('...' if len(bk.purpose) > 60 else ''),
                'time':   f'{time_str} ({duration} hari)',
                'room':   bk.room.name,
                'reason': (bk.user.get_full_name() or bk.user.email) + ' • ' + bk.get_status_display(),
                'type':   'booking',
                'label':  bk.get_status_display(),
                'icon':   'meeting_room',
            })

        return JsonResponse({'schedules': schedules})
