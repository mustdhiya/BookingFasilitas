# research/admin.py
from django.contrib import admin
from .models import Lecturer, ResearchTitle, ResearchRequest, GuidanceSession

@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display  = ('name', 'focus', 'nip', 'active_titles_count', 'is_active')
    list_filter   = ('focus', 'is_active')
    search_fields = ('name', 'nip')

@admin.register(ResearchTitle)
class ResearchTitleAdmin(admin.ModelAdmin):
    list_display  = ('title', 'lecturer', 'focus', 'quota', 'slots_used', 'is_active')
    list_filter   = ('focus', 'is_active', 'lecturer')
    search_fields = ('title', 'lecturer__name')

@admin.register(ResearchRequest)
class ResearchRequestAdmin(admin.ModelAdmin):
    list_display  = ('student', 'lecturer', 'thesis_title', 'request_type', 'status')
    list_filter   = ('status', 'request_type')
    search_fields = ('student__first_name', 'thesis_title')

@admin.register(GuidanceSession)
class GuidanceSessionAdmin(admin.ModelAdmin):
    list_display = ('request', 'date', 'topic')
