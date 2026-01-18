from rest_framework import serializers
from .models import Tool, ToolRental, ToolBlockSchedule

class ToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tool
        fields = '__all__'


class ToolRentalSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    tool_detail = ToolSerializer(source='tool', read_only=True)
    
    class Meta:
        model = ToolRental
        fields = '__all__'
        read_only_fields = [
            'user', 'total_amount', 'duration_days', 
            'status', 'approved_by', 'approved_at', 'returned_at'
        ]
    
    def get_user_detail(self, obj):
        return {
            'id': obj.user.id,
            'name': obj.user.get_full_name(),
            'email': obj.user.email
        }
    
    def validate(self, data):
        # Check stock availability
        tool = data.get('tool')
        quantity = data.get('quantity')
        
        if tool.stock < quantity:
            raise serializers.ValidationError(
                f"Stock tidak mencukupi. Tersedia: {tool.stock}"
            )
        
        # Validate date range
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError(
                "Tanggal mulai harus lebih awal dari tanggal selesai"
            )
        
        return data


class ToolBlockScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToolBlockSchedule
        fields = '__all__'
