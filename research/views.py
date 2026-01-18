from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import ResearchVariable, VariableRequest, GuidanceSession
from .serializers import (
    ResearchVariableSerializer,
    VariableRequestSerializer,
    GuidanceSessionSerializer
)

class ResearchVariableViewSet(viewsets.ModelViewSet):
    queryset = ResearchVariable.objects.filter(is_active=True)
    serializer_class = ResearchVariableSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def by_field(self, request):
        """Filter variables by field"""
        field = request.query_params.get('field')
        variables = self.get_queryset()
        
        if field:
            variables = variables.filter(field=field)
        
        serializer = self.get_serializer(variables, many=True)
        return Response(serializer.data)


class VariableRequestViewSet(viewsets.ModelViewSet):
    serializer_class = VariableRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['laboran', 'dosen']:
            return VariableRequest.objects.all()
        return VariableRequest.objects.filter(student=user)
    
    def perform_create(self, serializer):
        variable = serializer.validated_data['variable']
        
        # Check if already requested
        if VariableRequest.objects.filter(
            variable=variable,
            student=self.request.user
        ).exists():
            raise serializers.ValidationError('Anda sudah request variabel ini')
        
        # Check quota
        if variable.is_full:
            raise serializers.ValidationError('Kuota variabel sudah penuh')
        
        serializer.save(student=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """Get current user's requests"""
        requests = VariableRequest.objects.filter(
            student=request.user
        ).order_by('-created_at')
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve variable request"""
        var_request = self.get_object()
        
        if var_request.variable.is_full:
            return Response(
                {'error': 'Kuota variabel sudah penuh'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        var_request.status = 'approved'
        var_request.approved_by = request.user
        var_request.approved_at = timezone.now()
        var_request.save()
        
        return Response({
            'message': 'Request berhasil diapprove',
            'request': self.get_serializer(var_request).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def decline(self, request, pk=None):
        """Decline variable request"""
        var_request = self.get_object()
        var_request.status = 'declined'
        var_request.admin_notes = request.data.get('notes', '')
        var_request.save()
        
        return Response({
            'message': 'Request berhasil ditolak',
            'request': self.get_serializer(var_request).data
        })
    
    @action(detail=False, methods=['get'])
    def check_overdue_guidance(self, request):
        """Check if user has overdue guidance (>1 month)"""
        approved_requests = VariableRequest.objects.filter(
            student=request.user,
            status='approved'
        )
        
        overdue_alerts = []
        one_month_ago = timezone.now() - timedelta(days=30)
        
        for req in approved_requests:
            last_session = req.guidance_sessions.order_by('-date').first()
            
            if not last_session or last_session.date < one_month_ago.date():
                overdue_alerts.append({
                    'variable': req.variable.name,
                    'last_session': last_session.date if last_session else None,
                    'days_overdue': (timezone.now().date() - last_session.date).days if last_session else 'Never'
                })
        
        return Response({
            'has_overdue': len(overdue_alerts) > 0,
            'alerts': overdue_alerts
        })


class GuidanceSessionViewSet(viewsets.ModelViewSet):
    queryset = GuidanceSession.objects.all()
    serializer_class = GuidanceSessionSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['laboran', 'dosen']:
            return GuidanceSession.objects.all()
        
        # Students can only see their own guidance sessions
        return GuidanceSession.objects.filter(
            request__student=user
        )
    
    @action(detail=False, methods=['get'])
    def my_sessions(self, request):
        """Get current user's guidance sessions"""
        sessions = GuidanceSession.objects.filter(
            request__student=request.user
        ).order_by('-date')[:5]
        serializer = self.get_serializer(sessions, many=True)
        return Response(serializer.data)
