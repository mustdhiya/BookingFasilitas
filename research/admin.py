from django.contrib import admin
from .models import ResearchVariable, VariableRequest, GuidanceSession

@admin.register(ResearchVariable)
class ResearchVariableAdmin(admin.ModelAdmin):
    list_display = ['name', 'field', 'supervisor', 'quota', 'is_active']
    list_filter = ['field', 'is_active']

@admin.register(VariableRequest)
class VariableRequestAdmin(admin.ModelAdmin):
    list_display = ['variable', 'student', 'status', 'created_at']
    list_filter = ['status', 'created_at']

@admin.register(GuidanceSession)
class GuidanceSessionAdmin(admin.ModelAdmin):
    list_display = ['request', 'date', 'topic']
    list_filter = ['date']
