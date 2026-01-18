from rest_framework import serializers
from .models import Practicum, PracticumRegistration, Attendance
from accounts.serializers import UserSerializer

class PracticumSerializer(serializers.ModelSerializer):
    instructor_detail = UserSerializer(source='instructor', read_only=True)
    registered_count = serializers.IntegerField(read_only=True)
    waitlist_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Practicum
        fields = '__all__'


class PracticumRegistrationSerializer(serializers.ModelSerializer):
    student_detail = UserSerializer(source='student', read_only=True)
    practicum_detail = PracticumSerializer(source='practicum', read_only=True)
    
    class Meta:
        model = PracticumRegistration
        fields = '__all__'
        read_only_fields = ['student', 'status', 'attendance_percentage']


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
