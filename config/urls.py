"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# config/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.views.generic import TemplateView
from django.shortcuts import render

from accounts.views import (
    LoginPageView, ProfilePageView,
    RegisterPageView, LogoutView, DashboardPageView, 
    AdminAkunView, AdminAkunAksiView
)
from rooms.views import PeminjamRuanganView, RiwayatView, RoomCalendarView, RoomDayScheduleView
from konseling.views import AdminPanelView   
from practicum.views import PracticumListView as PracticumPageView
from research.views import ResearchListView
from internship.views import InternshipListView


def panduan_info_view(request):
    return render(request, 'panduan_info.html')

def panduan_info_view(request):
    context = {
        'sections': [
            {'slug': 'panduan-peminjaman', 'title': 'Panduan Peminjaman', 'icon': 'inventory_2'},
            {'slug': 'sop-konseling',      'title': 'SOP Konseling',      'icon': 'psychology'},
            {'slug': 'faq',                'title': 'FAQ',                 'icon': 'quiz'},
            {'slug': 'tentang',            'title': 'Tentang Lab',         'icon': 'apartment'},
            {'slug': 'kebijakan-privasi',  'title': 'Kebijakan Privasi',   'icon': 'shield'},
        ],
        'peminjaman_steps': [
            {'title': 'Login ke sistem',         'desc': 'Pastikan akun sudah terverifikasi oleh admin.'},
            {'title': 'Pilih jenis peminjaman',  'desc': 'Ruangan atau Alat Test tersedia di menu Peminjaman.'},
            {'title': 'Isi form & tanggal',      'desc': 'Pilih tanggal, jam, dan kebutuhan yang sesuai.'},
            {'title': 'Tunggu konfirmasi',        'desc': 'Admin akan menyetujui atau menolak dalam 1x24 jam.'},
            {'title': 'Cetak surat peminjaman',  'desc': 'Unduh dokumen dari menu Riwayat & Dokumen.'},
        ],
        'peminjaman_rules': [
            'Peminjaman hanya untuk keperluan akademik dan penelitian.',
            'Alat test wajib dikembalikan dalam kondisi lengkap dan bersih.',
            'Pembatalan minimal H-1 sebelum jadwal peminjaman.',
            'Kerusakan akibat kelalaian menjadi tanggung jawab peminjam.',
            'Satu pengguna hanya bisa memiliki 1 peminjaman aktif pada waktu bersamaan.',
        ],
        'konseling_steps': [
            {'title': 'Ajukan permintaan konseling', 'desc': 'Isi form di menu Konseling dengan keluhan atau topik yang ingin dibahas.'},
            {'title': 'Penjadwalan sesi',            'desc': 'Konselor akan menghubungi untuk konfirmasi waktu sesi.'},
            {'title': 'Pelaksanaan sesi',            'desc': 'Sesi berlangsung 60–90 menit secara tatap muka atau online.'},
            {'title': 'Tindak lanjut',               'desc': 'Konselor memberikan rekomendasi dan jadwal sesi berikutnya bila diperlukan.'},
        ],
        'faqs': [
            {'q': 'Siapa saja yang bisa menggunakan layanan Lab Psikologi?',
             'a': 'Mahasiswa, dosen, dan masyarakat umum dapat menggunakan layanan. Beberapa layanan khusus hanya untuk civitas akademika UMKT.'},
            {'q': 'Apakah peminjaman alat test dikenakan biaya?',
             'a': 'Peminjaman untuk keperluan akademik internal (tugas/skripsi) tidak dikenakan biaya. Untuk keperluan eksternal/penelitian berbayar, silakan hubungi admin.'},
            {'q': 'Berapa lama proses verifikasi akun?',
             'a': 'Verifikasi akun dilakukan dalam 1×24 jam hari kerja setelah dokumen KTM/KTP diunggah.'},
            {'q': 'Bagaimana jika jadwal peminjaman saya bentrok?',
             'a': 'Sistem akan otomatis menolak peminjaman yang bentrok dengan jadwal lain. Pilih waktu lain yang tersedia.'},
            {'q': 'Apakah layanan konseling bersifat rahasia?',
             'a': 'Ya. Seluruh informasi dalam sesi konseling dijaga kerahasiaannya sesuai kode etik psikologi dan tidak dibagikan tanpa persetujuan klien.'},
            {'q': 'Bagaimana cara mendaftar magang di Lab Psikologi?',
             'a': 'Login ke sistem, buka menu Akademik → Internship, pilih mitra, lalu isi form pendaftaran. Fitur ini hanya tersedia untuk mahasiswa.'},
        ],
        'privacy_policies': [
            {'icon': 'data_usage',  'title': 'Data yang Dikumpulkan',
             'desc': 'Kami mengumpulkan nama, email, NIM/NIP, foto profil, dan KTM/KTP hanya untuk keperluan verifikasi identitas dan penggunaan layanan Lab.'},
            {'icon': 'lock',        'title': 'Penggunaan Data',
             'desc': 'Data tidak dijual atau dibagikan kepada pihak ketiga. Data hanya digunakan untuk pengelolaan layanan Lab Psikologi UMKT secara internal.'},
            {'icon': 'security',    'title': 'Keamanan Data',
             'desc': 'Sistem menggunakan enkripsi HTTPS dan password hashing. Akses data dibatasi hanya untuk admin yang berwenang.'},
            {'icon': 'delete_forever', 'title': 'Penghapusan Data',
             'desc': 'Pengguna dapat mengajukan penghapusan akun dengan menghubungi admin. Data akan dihapus dalam 30 hari kerja setelah permintaan diterima.'},
        ],
    }
    return render(request, 'panduan_info.html', context)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('panduan-info/', panduan_info_view, name='panduan_info'),

    # ── HTML Pages ──────────────────────────────────────────────────────
    path('',            TemplateView.as_view(template_name='index.html'), name='home'),
    path('dashboard/',  DashboardPageView.as_view(),                      name='dashboard'),
    path('logout/',     LogoutView.as_view(),                             name='logout'),
    path('login/',      LoginPageView.as_view(),                          name='login'),
    path('register/',   RegisterPageView.as_view(),                       name='register'),
    path('profile/',    ProfilePageView.as_view(),                        name='profile'),
    path('peminjaman/', PeminjamRuanganView.as_view(),                    name='peminjaman'),
    path('praktikum/',  PracticumPageView.as_view(),                      name='praktikum'),
    path('penelitian/', ResearchListView.as_view(), name='penelitian'),
    path('riwayat/', RiwayatView.as_view(), name='riwayat'),
    path('magang/', InternshipListView.as_view(), name='magang'),


    # ── Admin Panel (satu halaman, semua modul) ──────────────────────────
    path('admin-panel/', AdminPanelView.as_view(), name='admin_panel'),  
    path('admin-panel/akun/',            AdminAkunView.as_view(),            name='admin-akun'),
    path('admin-panel/akun/<int:pk>/aksi/', AdminAkunAksiView.as_view(),     name='admin-akun-aksi'),

    # ── API + user-facing konseling ──────────────────────────────────────
    path('konseling/',    include('konseling.urls')),
    path('api/accounts/', include('accounts.urls', namespace='accounts')),
    path('api/rooms/',    include('rooms.urls')),
    path('api/tools/',    include('tools.urls')),
    path('api/practicum/', include('practicum.urls')),
    path('api/research/',  include('research.urls')),
    path('api/internship/', include('internship.urls')),                 

    path('api/rooms/calendar/',     RoomCalendarView.as_view(),     name='api-room-calendar'),
    path('api/rooms/day-schedule/', RoomDayScheduleView.as_view(),  name='api-room-day-schedule'),

]

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$',  serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
