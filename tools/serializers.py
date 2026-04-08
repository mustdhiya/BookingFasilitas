from rest_framework import serializers
from .models import TestTool, ToolRental


class ToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestTool
        fields = '__all__'


class ToolRentalSerializer(serializers.ModelSerializer):
    user_detail = serializers.SerializerMethodField()
    tool_detail = ToolSerializer(source='tool', read_only=True)

    # Tambahkan ini — override field agar tidak required by default
    payment_time = serializers.CharField(
        required=False,
        allow_blank=True,
        default='after'
    )

    class Meta:
        model = ToolRental
        fields = '__all__'
        read_only_fields = [
            'user', 'total_cost',
            'status', 'approved_by', 'approved_at', 'returned_at'
        ]

    def get_user_detail(self, obj):
        return {
            'id': obj.user.id,
            'name': obj.user.get_full_name(),
            'email': obj.user.email,
        }

    def validate(self, data):
        tool     = data.get('tool')
        quantity = data.get('quantity')

        if tool and quantity and tool.stock < quantity:
            raise serializers.ValidationError(
                f'Stock tidak mencukupi. Tersedia: {tool.stock} {tool.unit}.'
            )

        date_start = data.get('date_start')
        date_end   = data.get('date_end')
        if date_start and date_end and date_end < date_start:
            raise serializers.ValidationError(
                'Tanggal kembali tidak boleh sebelum tanggal mulai.'
            )

        # Validasi payment_time hanya wajib untuk sewa
        transaction_type = data.get('transaction_type')
        payment_time     = data.get('payment_time', '').strip()
        if transaction_type == 'sewa' and not payment_time:
            raise serializers.ValidationError({
                'payment_time': 'Waktu pembayaran wajib diisi untuk penyewaan.'
            })

        # Untuk non-sewa, set default supaya model tidak complaint
        if transaction_type != 'sewa':
            data['payment_time'] = 'after'

        return data