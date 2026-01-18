from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'practicum'

router = DefaultRouter()
router.register(r'schedules', views.PracticumViewSet, basename='practicum')
router.register(r'registrations', views.PracticumRegistrationViewSet, basename='registration')
router.register(r'attendance', views.AttendanceViewSet, basename='attendance')

urlpatterns = [
    path('', include(router.urls)),
]
