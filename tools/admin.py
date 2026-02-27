from django.contrib import admin
from .models import TestTool, ToolRental


@admin.register(TestTool)
class TestToolAdmin(admin.ModelAdmin):
    list_display  = ['code', 'name', 'stock', 'unit', 'price_per_unit', 'is_active']
    list_filter   = ['is_active', 'unit']
    search_fields = ['code', 'name']


@admin.register(ToolRental)
class ToolRentalAdmin(admin.ModelAdmin):
    list_display  = ['tool', 'user', 'quantity', 'date_start', 'date_end',
                     'status', 'is_paid', 'total_cost']
    list_filter   = ['status', 'is_paid', 'institution', 'date_start']
    search_fields = ['user__email', 'user__first_name', 'tool__name']
    readonly_fields = ['total_cost', 'approved_by', 'approved_at', 'returned_at']

    fieldsets = (
        ('Peminjam', {
            'fields': ('user', 'institution', 'purpose', 'activity_letter')
        }),
        ('Alat Tes', {
            'fields': ('tool', 'quantity', 'components')
        }),
        ('Tanggal', {
            'fields': ('date_start', 'date_end')
        }),
        ('Pembayaran', {
            'fields': ('payment_time', 'total_cost', 'is_paid',
                       'payment_proof', 'agreement_file')
        }),
        ('Status Admin', {
            'fields': ('status', 'admin_notes', 'approved_by',
                       'approved_at', 'returned_at')
        }),
    )
