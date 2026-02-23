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

from accounts.views import (
    LoginPageView, ProfilePageView,
    RegisterPageView, LogoutView, DashboardPageView, 
    AdminAkunView, AdminAkunAksiView
)
from rooms.views import RoomBookingPageView
from konseling.views import AdminPanelView   
from practicum.views import PracticumListView as PracticumPageView

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── HTML Pages ──────────────────────────────────────────────────────
    path('',            TemplateView.as_view(template_name='index.html'), name='home'),
    path('dashboard/',  DashboardPageView.as_view(),                      name='dashboard'),
    path('logout/',     LogoutView.as_view(),                             name='logout'),
    path('login/',      LoginPageView.as_view(),                          name='login'),
    path('register/',   RegisterPageView.as_view(),                       name='register'),
    path('profile/',    ProfilePageView.as_view(),                        name='profile'),
    path('peminjaman/', RoomBookingPageView.as_view(),                    name='peminjaman'),
    path('praktikum/',  PracticumPageView.as_view(),                      name='praktikum'),

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
]

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$',  serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
