from rest_framework import serializers
from .models import Room, RoomBooking, RoomBlockSchedule
from accounts.serializers import UserSerializer

class RoomSerializer(serializers.ModelSerializer):
    is_lab = serializers.BooleanField(read_only=True)  

    class Meta:
        model  = Room
        fields = '__all__'


class RoomBookingSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    room_detail = RoomSerializer(source='room', read_only=True)

    class Meta:
        model  = RoomBooking
        fields = '__all__'
        read_only_fields = ['user', 'status', 'approved_by', 'approved_at']

    def validate(self, data):
        room = data.get('room')
        participants = data.get('participants')

        if room and participants and participants > room.capacity:
            raise serializers.ValidationError(
                f'Jumlah peserta ({participants}) melebihi kapasitas ruangan ({room.capacity} orang).'
            )

        date_start = data.get('date_start')
        date_end   = data.get('date_end')
        if date_start and date_end and date_end < date_start:
            raise serializers.ValidationError('Tanggal selesai tidak boleh sebelum tanggal mulai.')

        return data

class RoomBlockScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomBlockSchedule
        fields = '__all__'
