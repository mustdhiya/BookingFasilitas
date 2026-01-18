from rest_framework import serializers
from .models import Room, RoomBooking, RoomBlockSchedule
from accounts.serializers import UserSerializer

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'


class RoomBookingSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    room_detail = RoomSerializer(source='room', read_only=True)
    
    class Meta:
        model = RoomBooking
        fields = '__all__'
        read_only_fields = ['user', 'status', 'approved_by', 'approved_at']
    
    def validate(self, data):
        # Check capacity
        if data['participants'] > data['room'].capacity:
            raise serializers.ValidationError(
                f"Jumlah peserta melebihi kapasitas ({data['room'].capacity})"
            )
        
        # Check time logic
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError(
                "Jam mulai harus lebih awal dari jam selesai"
            )
        
        return data


class RoomBlockScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomBlockSchedule
        fields = '__all__'
