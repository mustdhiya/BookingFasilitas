from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from datetime import datetime
from .models import Tool, ToolRental, ToolBlockSchedule
from .serializers import ToolSerializer, ToolRentalSerializer, ToolBlockScheduleSerializer

class ToolViewSet(viewsets.ModelViewSet):
    queryset = Tool.objects.filter(is_active=True, stock__gt=0)
    serializer_class = ToolSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def adjust_stock(self, request, pk=None):
        """Adjust tool stock"""
        tool = self.get_object()
        adjustment = request.data.get('adjustment', 0)
        
        new_stock = tool.stock + int(adjustment)
        if new_stock < 0:
            return Response(
                {'error': 'Stock tidak boleh negatif'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tool.stock = new_stock
        tool.save()
        
        return Response({
            'message': 'Stock berhasil diupdate',
            'tool': self.get_serializer(tool).data
        })


class ToolRentalViewSet(viewsets.ModelViewSet):
    serializer_class = ToolRentalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['laboran']:
            return ToolRental.objects.all()
        return ToolRental.objects.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_rentals(self, request):
        """Get current user's rentals"""
        rentals = ToolRental.objects.filter(user=request.user).order_by('-created_at')[:5]
        serializer = self.get_serializer(rentals, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve rental (admin only)"""
        rental = self.get_object()
        
        # Check stock again
        if rental.tool.stock < rental.quantity:
            return Response(
                {'error': 'Stock tidak mencukupi'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reduce stock
        rental.tool.stock -= rental.quantity
        rental.tool.save()
        
        rental.status = 'approved'
        rental.approved_by = request.user
        rental.approved_at = datetime.now()
        rental.save()
        
        return Response({
            'message': 'Rental berhasil diapprove',
            'rental': self.get_serializer(rental).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def decline(self, request, pk=None):
        """Decline rental"""
        rental = self.get_object()
        rental.status = 'declined'
        rental.admin_notes = request.data.get('notes', '')
        rental.save()
        
        return Response({
            'message': 'Rental berhasil ditolak',
            'rental': self.get_serializer(rental).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_returned(self, request, pk=None):
        """Mark rental as returned"""
        rental = self.get_object()
        
        # Add stock back
        rental.tool.stock += rental.quantity
        rental.tool.save()
        
        rental.status = 'returned'
        rental.returned_at = datetime.now()
        rental.save()
        
        return Response({
            'message': 'Alat telah dikembalikan',
            'rental': self.get_serializer(rental).data
        })


class ToolBlockScheduleViewSet(viewsets.ModelViewSet):
    queryset = ToolBlockSchedule.objects.filter(is_active=True)
    serializer_class = ToolBlockScheduleSerializer
    permission_classes = [IsAdminUser]
