from django.contrib import admin
from .models import InternshipPartner, InternshipRequest, InternshipLog

@admin.register(InternshipPartner)
class InternshipPartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'field', 'is_active']
    list_filter = ['field', 'is_active']
    search_fields = ['name', 'contact_person']

@admin.register(InternshipRequest)
class InternshipRequestAdmin(admin.ModelAdmin):
    list_display = ['student', 'partner_name', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'start_date', 'end_date']
    raw_id_fields = ['student', 'lecturer']
    readonly_fields = ['total_days']

@admin.register(InternshipLog)
class InternshipLogAdmin(admin.ModelAdmin):
    list_display = ['request', 'date', 'topic']
    list_filter = ['date', 'request__status']
    raw_id_fields = ['request']
