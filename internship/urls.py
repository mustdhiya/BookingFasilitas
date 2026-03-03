from django.urls import path
from . import views

app_name = 'internship'

urlpatterns = [
    path('daftar/',              views.InternshipCreateView.as_view(),    name='create'),
    path('log/tambah/',          views.InternshipLogCreateView.as_view(), name='log-create'),
    path('log/<int:pk>/hapus/',  views.InternshipLogDeleteView.as_view(), name='log-delete'),
    path('upload/', views.InternshipUploadView.as_view(), name='upload'),
]
