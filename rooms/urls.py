from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'rooms'

router = DefaultRouter()
router.register(r'list', views.RoomViewSet, basename='room')
router.register(r'bookings', views.RoomBookingViewSet, basename='booking')
router.register(r'blocks', views.RoomBlockScheduleViewSet, basename='block')

urlpatterns = [
    path('', include(router.urls)),
]
