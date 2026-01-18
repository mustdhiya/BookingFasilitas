from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'research'

router = DefaultRouter()
router.register(r'variables', views.ResearchVariableViewSet, basename='variable')
router.register(r'requests', views.VariableRequestViewSet, basename='request')
router.register(r'guidance', views.GuidanceSessionViewSet, basename='guidance')

urlpatterns = [
    path('', include(router.urls)),
]
