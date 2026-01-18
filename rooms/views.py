from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.views.generic import TemplateView
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Room, RoomBooking, RoomBlockSchedule
from .serializers import RoomSerializer, RoomBookingSerializer, RoomBlockScheduleSerializer

# HTML Views
class RoomBookingPageView(TemplateView):
    template_name = 'pemriwMain.html'

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
