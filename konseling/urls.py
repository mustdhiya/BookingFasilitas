# konseling/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ── User-facing ──────────────────────────────────────────────────────
    path('',        views.KonselingPageView.as_view(),   name='konseling'),
    path('submit/', views.KonselingSubmitView.as_view(), name='konseling-submit'),

    # ── Admin dashboard konseling ────────────────────────────────────────
    path('admin/',              views.AdminKonselingListView.as_view(),   name='admin-konseling-list'),
    path('admin/<int:pk>/',     views.AdminKonselingDetailView.as_view(), name='admin-konseling-detail'),
    path('admin/<int:pk>/aksi/', views.AdminKonselingAksiView.as_view(),  name='admin-konseling-aksi'),
]
