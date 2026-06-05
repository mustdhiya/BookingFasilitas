from django.contrib import admin
from .models import InternshipPartner, InternshipRequest, InternshipLog
from django.contrib import admin
from .models import InternshipPartner, InternshipRequest, InternshipLog


@admin.register(InternshipPartner)
class InternshipPartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'field', 'quota', 'is_active']
    list_filter = ['field', 'is_active']
    search_fields = ['name', 'contact_person', 'keterangan']
    fieldsets = (
        ('Informasi Mitra', {
            'fields': ('name', 'field', 'address')
        }),
        ('Kontak', {
            'fields': ('contact_person', 'phone', 'email')
        }),
        ('Informasi Tambahan', {
            'fields': ('keterangan', 'quota', 'is_active')
        }),
    )


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

    