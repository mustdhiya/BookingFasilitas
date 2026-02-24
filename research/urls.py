from django.urls import path
from . import views

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────
    path('lecturers/',                   views.LecturerListView.as_view(),          name='lecturer-list'),
    path('lecturers/<int:pk>/',          views.LecturerDetailView.as_view(),        name='lecturer-detail'),
    path('lecturers/<int:pk>/titles/',   views.ResearchTitleListView.as_view(),     name='title-list'),
    path('requests/',                    views.ResearchRequestCreateView.as_view(), name='research-request'),
    path('requests/<int:pk>/',           views.ResearchRequestDetailView.as_view(), name='research-request-detail'),

    # ── Export ────────────────────────────────────────────────────────
    path('export/praktikum/',            views.export_praktikum,                    name='export-praktikum'),
    path('export/dosen/',                views.export_dosen,                        name='export-dosen'),
    path('export/penelitian/',           views.export_penelitian,                   name='export-penelitian'),

    # ── CRUD Dosen ────────────────────────────────────────────────────
    path('dosen/create/',                views.DosenCreateView.as_view(),           name='dosen-create'),
    path('dosen/<int:pk>/edit/',         views.DosenUpdateView.as_view(),           name='dosen-edit'),
    path('dosen/<int:pk>/delete/',       views.DosenDeleteView.as_view(),           name='dosen-delete'),
    path('dosen/<int:pk>/deactivate/',   views.DosenDeactivateView.as_view(),       name='dosen-deactivate'),
    path('dosen/<int:pk>/json/',         views.DosenJsonView.as_view(),             name='dosen-json'),

    # ── CRUD Judul Payung ─────────────────────────────────────────────
    path('judul/create/',                views.JudulCreateView.as_view(),           name='judul-create'),
    path('judul/<int:pk>/edit/',         views.JudulUpdateView.as_view(),           name='judul-edit'),
    path('judul/<int:pk>/delete/',       views.JudulDeleteView.as_view(),           name='judul-delete'),
    path('judul/<int:pk>/json/',         views.JudulJsonView.as_view(),             name='judul-json'),

    # ── CRUD Jadwal Praktikum ─────────────────────────────────────────
    path('jadwal/create/',               views.JadwalCreateView.as_view(),          name='jadwal-create'),
    path('jadwal/<int:pk>/update/',      views.JadwalUpdateView.as_view(),          name='jadwal-update'),
    path('jadwal/<int:pk>/delete/',      views.JadwalDeleteView.as_view(),          name='jadwal-delete'),
]
