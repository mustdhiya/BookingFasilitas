from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'rooms',          views.RoomViewSet,             basename='room')
router.register(r'bookings',       views.RoomBookingViewSet,       basename='room-booking')
router.register(r'block-schedule', views.RoomBlockScheduleViewSet, basename='room-block')

urlpatterns = [
    # HTML page
    path('', views.PeminjamRuanganView.as_view(), name='peminjam-ruangan'),

    # User booking
    path('booking/create/', views.RoomBookingCreateView.as_view(), name='room-booking-create'),

    # Admin CRUD Ruangan
    path('admin/ruangan/create/',              views.RoomCreateView.as_view(),  name='room-create'),
    path('admin/ruangan/<int:pk>/edit/',       views.RoomUpdateView.as_view(),  name='room-edit'),
    path('admin/ruangan/<int:pk>/delete/',     views.RoomDeleteView.as_view(),  name='room-delete'),
    path('admin/ruangan/<int:pk>/json/',       views.RoomJsonView.as_view(),    name='room-json'),
    path('admin/ruangan/<int:pk>/toggle/',     views.RoomToggleView.as_view(),  name='room-toggle'),
] + router.urls
