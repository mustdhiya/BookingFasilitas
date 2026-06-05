# accounts/middleware.py
from django.utils import timezone
from .models import UserSession

class ActiveSessionTouchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.session.session_key:
            UserSession.objects.filter(
                user=request.user,
                session_key=request.session.session_key
            ).update(last_seen_at=timezone.now())
        return self.get_response(request)