from rest_framework import serializers
from .models import Lecturer, ResearchTitle, ResearchRequest, GuidanceSession
from practicum.models import Practicum, Room  # sesuaikan import ini dengan lokasi model Practicum kamu


# ── Lecturer ──────────────────────────────────────────────────────────────
class LecturerSerializer(serializers.ModelSerializer):
    focus_display = serializers.CharField(source='get_focus_display', read_only=True)

    class Meta:
        model  = Lecturer
        fields = ['id', 'name', 'nip', 'focus', 'focus_display',
                  'email', 'phone', 'bio', 'photo', 'is_active']


# ── ResearchTitle ─────────────────────────────────────────────────────────
class ResearchTitleSerializer(serializers.ModelSerializer):
    slots_used      = serializers.IntegerField(read_only=True)
    slots_remaining = serializers.IntegerField(read_only=True)
    is_full         = serializers.BooleanField(read_only=True)
    fill_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model  = ResearchTitle
        fields = ['id', 'lecturer', 'title', 'description', 'focus',
                  'quota', 'is_active', 'slots_used', 'slots_remaining',
                  'is_full', 'fill_percentage']


# ── GuidanceSession ───────────────────────────────────────────────────────
class GuidanceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = GuidanceSession
        fields = '__all__'


# ── ResearchRequest ───────────────────────────────────────────────────────
class ResearchRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ResearchRequest
        fields = '__all__'
        read_only_fields = ['student', 'status', 'approved_by', 'approved_at']
