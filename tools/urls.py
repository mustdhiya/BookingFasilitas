from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'tools'

router = DefaultRouter()
router.register(r'list',    views.ToolViewSet,       basename='tool')
router.register(r'rentals', views.ToolRentalViewSet, basename='rental')

urlpatterns = [
    path('', include(router.urls)),
]
