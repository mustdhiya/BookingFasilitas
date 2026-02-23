# practicum/views.py
from django.views.generic import ListView, DetailView, CreateView
from .models import Practicum, PracticumRegistration


class PracticumListView(ListView):
    model = Practicum
    template_name = 'practicum/list.html'
    context_object_name = 'practicums'

    def get_queryset(self):
        return Practicum.objects.filter(is_active=True)


class PracticumDetailView(DetailView):
    model = Practicum
    template_name = 'practicum/detail.html'


class PracticumRegisterView(CreateView):
    model = PracticumRegistration
    template_name = 'practicum/register.html'
    fields = ['practicum', 'student']
