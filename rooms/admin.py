from django.contrib import admin
from .models import Room, RoomBooking, RoomBlockSchedule

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'capacity', 'is_active']
    search_fields = ['code', 'name']

@admin.register(RoomBooking)
class RoomBookingAdmin(admin.ModelAdmin):
    list_display = ['room', 'user', 'booking_date', 'start_time', 'status']
    list_filter = ['status', 'booking_date']
    search_fields = ['user__email', 'room__name']

@admin.register(RoomBlockSchedule)
class RoomBlockScheduleAdmin(admin.ModelAdmin):
    list_display = ['room', 'name', 'day_of_week', 'start_time', 'is_active']
