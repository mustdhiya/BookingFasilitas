from rest_framework import serializers
from .models import Practicum, PracticumRegistration, Attendance


class PracticumSerializer(serializers.ModelSerializer):
    lecturer_name = serializers.CharField(source='lecturer.name', read_only=True)
    room_name     = serializers.CharField(source='room.name', read_only=True)
    registered_count  = serializers.IntegerField(read_only=True)
    is_full           = serializers.BooleanField(read_only=True)
    is_almost_full    = serializers.BooleanField(read_only=True)
    fill_percentage   = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Practicum
        fields = [
            'id', 'type', 'session_name',
            'lecturer', 'lecturer_name',
            'room', 'room_name',
            'date', 'start_time', 'end_time',
            'capacity', 'description', 'is_active',
            'registered_count', 'is_full', 'is_almost_full', 'fill_percentage',
        ]


class PracticumCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Practicum
        fields = [
            'type', 'session_name',
            'lecturer', 'room',
            'date', 'start_time', 'end_time',
            'capacity', 'description', 'is_active',
        ]


class PracticumRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PracticumRegistration
        fields = '__all__'
        read_only_fields = ['student', 'status', 'attendance_percentage']


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Attendance
        fields = '__all__'
