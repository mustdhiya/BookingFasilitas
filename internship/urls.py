from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.InternshipListView.as_view(),      name='internship-list'),
    path('requests/',               views.InternshipCreateView.as_view(),    name='internship-create'),
    path('logs/create/',            views.InternshipLogCreateView.as_view(), name='internship-log-create'),
    path('logs/<int:pk>/delete/',   views.InternshipLogDeleteView.as_view(), name='internship-log-delete'),
    path('upload/',                 views.InternshipUploadView.as_view(),    name='internship-upload'),
    # ── Realtime quota polling ──
    path('partners/quota/',         views.PartnerQuotaView.as_view(),        name='internship-quota'),
]