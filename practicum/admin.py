# practicum/admin.py
from django.contrib import admin
from .models import Practicum, PracticumRegistration, Attendance

@admin.register(PracticumRegistration)
class PracticumRegistrationAdmin(admin.ModelAdmin):
    list_display  = ['student', 'practicum', 'status', 'created_at']
    list_filter   = ['status']
    search_fields = ['student__username', 'practicum__session_name']
    ordering      = ['-created_at']

@admin.register(Practicum)
class PracticumAdmin(admin.ModelAdmin):
    list_display  = ['session_name', 'type', 'date', 'start_time', 'capacity', 'registered_count', 'is_active']
    list_filter   = ['type', 'is_active']
    search_fields = ['session_name']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('registration', 'date', 'is_present')
    list_filter  = ('is_present',)
