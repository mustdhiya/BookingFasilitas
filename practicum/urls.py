from django.urls import path
from . import views

urlpatterns = [
    path('',                                    views.PraktikumMainView.as_view(),       name='practicum-list'),
    path('<int:pk>/',                           views.PracticumDetailView.as_view(),     name='practicum-detail'),
    path('registrations/',                      views.PracticumRegisterView.as_view(),   name='practicum-register'),
    path('registrations/<int:pk>/cancel/',      views.PracticumCancelView.as_view(),     name='practicum-cancel'),
    path('slots/',                              views.PracticumSlotView.as_view(),        name='practicum-slots'),
    path('<int:pk>/slots/',                     views.PracticumSlotView.as_view(),        name='practicum-slot-detail'),
    path('<int:pk>/peserta/',                   views.PracticumPesertaView.as_view(),     name='practicum-peserta'), 
    path('registrations/<int:pk>/approve/', views.PracticumApproveView.as_view(), name='practicum-approve'),

]

