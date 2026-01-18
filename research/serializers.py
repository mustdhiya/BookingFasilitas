from rest_framework import serializers
from .models import ResearchVariable, VariableRequest, GuidanceSession
from accounts.serializers import UserSerializer

class ResearchVariableSerializer(serializers.ModelSerializer):
    supervisor_detail = UserSerializer(source='supervisor', read_only=True)
    slots_used = serializers.IntegerField(read_only=True)
    slots_remaining = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ResearchVariable
        fields = '__all__'
    
    def to_representation(self, instance):
        """Hide supervisor detail for students"""
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if request and request.user.role == 'mahasiswa':
            data.pop('supervisor_detail', None)
            data.pop('supervisor', None)
        
        return data


class VariableRequestSerializer(serializers.ModelSerializer):
    student_detail = UserSerializer(source='student', read_only=True)
    variable_detail = ResearchVariableSerializer(source='variable', read_only=True)
    
    class Meta:
        model = VariableRequest
        fields = '__all__'
        read_only_fields = ['student', 'status', 'approved_by', 'approved_at']


class GuidanceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuidanceSession
        fields = '__all__'
