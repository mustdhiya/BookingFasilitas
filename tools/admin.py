from django.contrib import admin
from .models import Tool, ToolRental, ToolBlockSchedule

@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'price_per_sheet', 'stock', 'is_active']
    search_fields = ['code', 'name']

@admin.register(ToolRental)
class ToolRentalAdmin(admin.ModelAdmin):
    list_display = ['tool', 'user', 'start_date', 'end_date', 'status', 'payment_status']
    list_filter = ['status', 'payment_status', 'instansi']
    search_fields = ['user__email', 'tool__name']

@admin.register(ToolBlockSchedule)
class ToolBlockScheduleAdmin(admin.ModelAdmin):
    list_display = ['tool', 'name', 'start_date', 'end_date', 'is_active']
