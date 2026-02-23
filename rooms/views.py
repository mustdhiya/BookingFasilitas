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

        ctx['my_bookings'] = RoomBooking.objects.filter(
            user=user
        ).select_related('room').order_by('-booking_date')[:10]

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
        """Check room availability"""
        room_id = request.data.get('room_id')
        date = request.data.get('date')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        
        # Check overlapping bookings
        conflicts = RoomBooking.objects.filter(
            room_id=room_id,
            booking_date=date,
            status__in=['approved', 'pending']
        ).filter(
            Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
        )
        
        if conflicts.exists():
            return Response({
                'available': False,
                'message': 'Ruangan sudah dibooking pada waktu tersebut'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'available': True,
            'message': 'Ruangan tersedia'
        })
    
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
