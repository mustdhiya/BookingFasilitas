# practicum/admin.py
from django.contrib import admin
from .models import Practicum, PracticumRegistration, Attendance


@admin.register(Practicum)
class PracticumAdmin(admin.ModelAdmin):
    list_display  = ('session_name', 'type', 'lecturer', 'date', 'room', 'registered_count', 'capacity')
    list_filter   = ('type', 'is_active', 'lecturer')
    search_fields = ('session_name', 'lecturer__name')


@admin.register(PracticumRegistration)
class PracticumRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'practicum', 'status', 'attendance_percentage')
    list_filter  = ('status',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('registration', 'date', 'is_present')
    list_filter  = ('is_present',)
