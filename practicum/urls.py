# practicum/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('',              views.PracticumListView.as_view(),     name='practicum-list'),
    path('<int:pk>/',     views.PracticumDetailView.as_view(),   name='practicum-detail'),
    path('<int:pk>/register/', views.PracticumRegisterView.as_view(), name='practicum-register'),
]
