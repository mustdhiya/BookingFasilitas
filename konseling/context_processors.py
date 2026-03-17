from rooms.models import RoomBooking
from tools.models import ToolRental
from konseling.models import KonselingSession
from research.models import ResearchRequest
from django.contrib.auth import get_user_model

User = get_user_model()

def admin_stats(request):
    """Inject stats badge ke semua halaman admin."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}
    return {
        'stats': {
            'peminjaman_pending': RoomBooking.objects.filter(status='pending').count(),
            'tool_pending':       ToolRental.objects.filter(status='pending').count(),
            'konseling_pending':  KonselingSession.objects.filter(status='pending').count(),
            'penelitian_pending': ResearchRequest.objects.filter(status='pending').count(),
            'akun_pending':       User.objects.filter(is_active=False, is_verified=False)
                                      .exclude(is_superuser=True).count(),
        }
    }
