from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.utils import timezone
from .models import TestTool, ToolRental
from .serializers import ToolSerializer, ToolRentalSerializer


class ToolViewSet(viewsets.ModelViewSet):
    queryset = TestTool.objects.filter(is_active=True)
    serializer_class = ToolSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def adjust_stock(self, request, pk=None):
        tool = self.get_object()
        adjustment = int(request.data.get('adjustment', 0))
        new_stock = tool.stock + adjustment
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
        if user.is_staff or getattr(user, 'role', None) in ['laboran', 'dosen']:
            return ToolRental.objects.select_related('tool', 'user').all()
        return ToolRental.objects.select_related('tool', 'user').filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_rentals(self, request):
        rentals = ToolRental.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        serializer = self.get_serializer(rentals, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        rental = self.get_object()

        if rental.status != 'pending':
            return Response(
                {'error': f'Rental berstatus {rental.status}, tidak bisa diapprove.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tool = rental.tool
        if tool.stock < rental.quantity:
            return Response(
                {'error': f'Stock tidak mencukupi. Tersedia: {tool.stock} {tool.unit}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Kurangi stok
        tool.stock -= rental.quantity
        tool.save()

        rental.status = 'approved'
        rental.approved_by = request.user
        rental.approved_at = timezone.now()
        rental.save()

        return Response({
            'message': 'Rental berhasil diapprove',
            'rental': self.get_serializer(rental).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def decline(self, request, pk=None):
        rental = self.get_object()

        if rental.status not in ['pending', 'approved']:
            return Response(
                {'error': 'Rental tidak bisa ditolak dari status ini.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rental.status = 'declined'
        rental.admin_notes = request.data.get('notes', '')
        rental.save()

        return Response({
            'message': 'Rental berhasil ditolak',
            'rental': self.get_serializer(rental).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_returned(self, request, pk=None):
        rental = self.get_object()

        if rental.status != 'borrowed':
            return Response(
                {'error': 'Hanya rental berstatus "borrowed" yang bisa dikembalikan.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Kembalikan stok
        tool = rental.tool
        tool.stock += rental.quantity
        tool.save()

        rental.status = 'returned'
        rental.returned_at = timezone.now()
        rental.save()

        return Response({
            'message': 'Alat berhasil ditandai dikembalikan. Stok diperbarui.',
            'rental': self.get_serializer(rental).data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        rental = self.get_object()

        if rental.user != request.user:
            return Response(
                {'error': 'Anda tidak berhak membatalkan rental ini.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if rental.status != 'pending':
            return Response(
                {'error': 'Hanya rental pending yang bisa dibatalkan.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rental.status = 'cancelled'
        rental.save()
        return Response({'message': 'Rental berhasil dibatalkan.'})
