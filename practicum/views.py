from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.views.generic import TemplateView
from .models import Practicum, PracticumRegistration, Attendance
from .serializers import (
    PracticumSerializer, 
    PracticumRegistrationSerializer,
    AttendanceSerializer
)

# HTML Views
class PracticumPageView(TemplateView):
    template_name = 'DafStat.html'

# API ViewSets
class PracticumViewSet(viewsets.ModelViewSet):
    queryset = Practicum.objects.filter(is_active=True)
    serializer_class = PracticumSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Filter practicum by type"""
        prac_type = request.query_params.get('type')
        practicums = self.get_queryset()
        
        if prac_type:
            practicums = practicums.filter(type=prac_type)
        
        serializer = self.get_serializer(practicums, many=True)
        return Response(serializer.data)


class PracticumRegistrationViewSet(viewsets.ModelViewSet):
    serializer_class = PracticumRegistrationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['laboran', 'dosen']:
            return PracticumRegistration.objects.all()
        return PracticumRegistration.objects.filter(student=user)
    
    def perform_create(self, serializer):
        practicum = serializer.validated_data['practicum']
        
        # Check if already registered
        if PracticumRegistration.objects.filter(
            practicum=practicum,
            student=self.request.user
        ).exists():
            raise serializers.ValidationError('Anda sudah terdaftar di praktikum ini')
        
        # Auto-assign status
        if practicum.is_full:
            status_val = 'waitlist'
        else:
            status_val = 'approved'
        
        serializer.save(student=self.request.user, status=status_val)
    
    @action(detail=False, methods=['get'])
    def my_registrations(self, request):
        """Get current user's registrations"""
        registrations = PracticumRegistration.objects.filter(
            student=request.user
        ).order_by('-created_at')[:3]
        serializer = self.get_serializer(registrations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def promote_from_waitlist(self, request, pk=None):
        """Promote student from waitlist"""
        registration = self.get_object()
        
        if registration.status != 'waitlist':
            return Response(
                {'error': 'Hanya waitlist yang bisa dipromosikan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registration.status = 'approved'
        registration.save()
        
        return Response({
            'message': 'Mahasiswa berhasil dipromosikan',
            'registration': self.get_serializer(registration).data
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel own registration"""
        registration = self.get_object()
        
        if registration.student != request.user:
            return Response(
                {'error': 'Anda tidak berhak membatalkan pendaftaran ini'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        registration.status = 'cancelled'
        registration.save()
        
        return Response({'message': 'Pendaftaran berhasil dibatalkan'})


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['post'])
    def mark_present(self, request):
        """Mark student as present"""
        registration_id = request.data.get('registration_id')
        date = request.data.get('date')
        
        attendance, created = Attendance.objects.get_or_create(
            registration_id=registration_id,
            date=date,
            defaults={'is_present': True}
        )
        
        if not created:
            attendance.is_present = True
            attendance.save()
        
        # Update attendance percentage
        registration = attendance.registration
        total_sessions = registration.attendances.count()
        present_sessions = registration.attendances.filter(is_present=True).count()
        
        if total_sessions > 0:
            registration.attendance_percentage = (present_sessions / total_sessions) * 100
            registration.save()
        
        return Response({
            'message': 'Kehadiran berhasil dicatat',
            'attendance': self.get_serializer(attendance).data
        })
