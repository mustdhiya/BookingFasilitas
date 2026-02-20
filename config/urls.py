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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# HTML page views
from accounts.views import LoginPageView, ProfilePageView
from rooms.views import RoomBookingPageView
from practicum.views import PracticumPageView

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # HTML Pages
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='home'),
    path('login/', LoginPageView.as_view(), name='login'),
    path('profile/', ProfilePageView.as_view(), name='profile'),
    path('peminjaman/', RoomBookingPageView.as_view(), name='peminjaman'),
    path('praktikum/', PracticumPageView.as_view(), name='praktikum'),
    path('admin-panel/', TemplateView.as_view(template_name='admin.html'), name='admin_panel'),
    
    # API endpoints
    path('api/accounts/', include('accounts.urls')),
    path('api/rooms/', include('rooms.urls')),
    path('api/tools/', include('tools.urls')),
    path('api/practicum/', include('practicum.urls')),
    path('api/research/', include('research.urls')),
]

# Serve media files in development
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
