from django.urls import path
from . import admin_views

urlpatterns = [
    path('',                            admin_views.InternshipAdminListView.as_view(),   name='admin-internship-list'),
    path('<int:pk>/detail/',            admin_views.InternshipDetailView.as_view(),      name='admin-internship-detail'),
    path('<int:pk>/approve/',           admin_views.InternshipApproveView.as_view(),     name='admin-internship-approve'),
    path('<int:pk>/reject/',            admin_views.InternshipRejectView.as_view(),      name='admin-internship-reject'),
    path('partners/',                   admin_views.PartnerAdminListView.as_view(),      name='admin-partner-list'),
    path('partners/create/',            admin_views.PartnerCreateView.as_view(),         name='admin-partner-create'),
    path('partners/<int:pk>/edit/',     admin_views.PartnerEditView.as_view(),           name='admin-partner-edit'),
    path('partners/<int:pk>/toggle/',   admin_views.PartnerToggleView.as_view(),         name='admin-partner-toggle'),
]