# rooms/admin.py
from django.contrib import admin
from .models import Room, RoomBooking, RoomBlockSchedule


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display  = ['code', 'name', 'capacity', 'is_active']
    search_fields = ['code', 'name']
    list_filter   = ['is_active']


@admin.register(RoomBooking)
class RoomBookingAdmin(admin.ModelAdmin):
    list_display  = ['room', 'user', 'date_start', 'date_end', 'duration_days', 'participants', 'status']
    list_filter   = ['status', 'date_start', 'room']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'room__name', 'purpose']
    readonly_fields = ['approved_by', 'approved_at', 'duration_days']
    ordering      = ['-date_start']

    fieldsets = (
        ('Informasi Peminjam', {
            'fields': ('user', 'room', 'participants', 'purpose')
        }),
        ('Rentang Tanggal', {
            'fields': ('date_start', 'date_end')
        }),
        ('Status & Catatan Admin', {
            'fields': ('status', 'admin_notes', 'approved_by', 'approved_at')
        }),
    )

    @admin.display(description='Durasi')
    def duration_days(self, obj):
        return f'{obj.duration_days} hari'


@admin.register(RoomBlockSchedule)
class RoomBlockScheduleAdmin(admin.ModelAdmin):
    list_display  = ['room', 'name', 'block_type', 'day_of_week', 'date_start', 'date_end', 'is_active']
    list_filter   = ['block_type', 'is_active', 'room', 'day_of_week']
    search_fields = ['name', 'room__name', 'description']

    fieldsets = (
        ('Informasi Blokir', {
            'fields': ('room', 'name', 'description', 'block_type', 'is_active')
        }),
        ('Jadwal Berulang (Mingguan)', {
            'fields': ('day_of_week',),
            'description': 'Isi jika blokir berulang tiap minggu. Kosongkan jika pakai rentang tanggal.',
        }),
        ('Rentang Tanggal Spesifik', {
            'fields': ('date_start', 'date_end'),
            'description': 'Isi jika blokir hanya untuk periode tertentu. Kosongkan jika pakai hari berulang.',
        }),
    )
