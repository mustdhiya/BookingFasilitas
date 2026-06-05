from django.contrib import admin
from .models import InternshipPartner, InternshipRequest, InternshipLog

@admin.register(InternshipPartner)
class InternshipPartnerAdmin(admin.ModelAdmin):
    list_display  = ['name', 'field', 'quota', 'accepted_count', 'quota_remaining', 'is_active']
    list_filter   = ['field', 'is_active']
    search_fields = ['name', 'contact_person']
    readonly_fields = ['accepted_count', 'quota_remaining']

    fieldsets = (
        (None, {'fields': ('name', 'field', 'address', 'contact_person', 'phone', 'email', 'is_active')}),
        ('Kuota', {'fields': ('quota', 'quota_per_batch', 'accepted_count', 'quota_remaining')}),
    )

    def accepted_count(self, obj):
        return obj.accepted_count
    accepted_count.short_description = 'Diterima'

    def quota_remaining(self, obj):
        r = obj.quota_remaining
        return '∞' if r is None else r
    quota_remaining.short_description = 'Sisa'
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
