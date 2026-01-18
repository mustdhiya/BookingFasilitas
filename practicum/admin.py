from django.contrib import admin
from .models import Practicum, PracticumRegistration, Attendance

@admin.register(Practicum)
class PracticumAdmin(admin.ModelAdmin):
    list_display = ['type', 'session_name', 'instructor', 'date', 'capacity', 'is_active']
    list_filter = ['type', 'is_active', 'date']

@admin.register(PracticumRegistration)
class PracticumRegistrationAdmin(admin.ModelAdmin):
    list_display = ['practicum', 'student', 'status', 'attendance_percentage']
    list_filter = ['status', 'certificate_issued']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['registration', 'date', 'is_present']
    list_filter = ['is_present', 'date']
