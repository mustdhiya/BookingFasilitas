# research/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('lecturers/',                   views.LecturerListView.as_view(),          name='lecturer-list'),
    path('lecturers/<int:pk>/',          views.LecturerDetailView.as_view(),        name='lecturer-detail'),
    path('lecturers/<int:pk>/titles/',   views.ResearchTitleListView.as_view(),     name='title-list'),
    path('requests/',                    views.ResearchRequestCreateView.as_view(), name='research-request'),
    path('requests/<int:pk>/',           views.ResearchRequestDetailView.as_view(), name='research-request-detail'),

    # Export
    path('export/praktikum/',  views.export_praktikum,  name='export-praktikum'),
    path('export/dosen/',      views.export_dosen,       name='export-dosen'),
    path('export/penelitian/', views.export_penelitian,  name='export-penelitian'),

    # CRUD Dosen
    path('research/dosen/create/',        views.DosenCreateView.as_view(),  name='dosen-create'),
    path('research/dosen/<int:pk>/edit/', views.DosenUpdateView.as_view(),  name='dosen-edit'),
    path('research/dosen/<int:pk>/delete/', views.DosenDeleteView.as_view(), name='dosen-delete'),

    # CRUD Judul Payung
    path('research/judul/create/',         views.JudulCreateView.as_view(), name='judul-create'),
    path('research/judul/<int:pk>/edit/',  views.JudulUpdateView.as_view(), name='judul-edit'),
    path('research/judul/<int:pk>/delete/', views.JudulDeleteView.as_view(), name='judul-delete'),
]
