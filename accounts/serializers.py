from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, LoginHistory

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'nim_nip', 'instansi', 'phone', 'avatar',
            'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RegisterSerializer(serializers.ModelSerializer):
    password         = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    full_name        = serializers.CharField(write_only=True, required=False, allow_blank=True)

    nim_nip  = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    prodi    = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    instansi = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    phone    = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)

    angkatan = serializers.IntegerField(required=False, allow_null=True, default=None)

    class Meta:
        model = User
        fields = [
            'email', 'full_name', 'password', 'password_confirm',
            'user_type', 'role',
            'nim_nip', 'prodi', 'angkatan',
            'instansi', 'phone', 'ktm_photo',
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email sudah terdaftar.')
        return value.lower()

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Password tidak cocok.'})
        if data.get('user_type') == 'umkt':
            if not data.get('nim_nip'):
                raise serializers.ValidationError({'nim_nip': 'NIM wajib diisi untuk mahasiswa UMKT.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        full_name = validated_data.pop('full_name', '')
        password  = validated_data.pop('password')

        parts      = full_name.strip().split(' ', 1)
        first_name = parts[0] if parts else ''
        last_name  = parts[1] if len(parts) > 1 else ''

        # ← TAMBAH INI: set role berdasarkan user_type
        user_type = validated_data.get('user_type', 'umkt')
        if user_type == 'umkt':
            validated_data['role'] = 'mahasiswa'
        else:
            validated_data['role'] = 'eksternal'

        for field in ['nim_nip', 'prodi', 'angkatan', 'instansi', 'phone']:
            if validated_data.get(field) in [None, '', 0]:
                validated_data.pop(field, None)

        base_username = validated_data['email'].split('@')[0]
        username = base_username
        counter  = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{counter}'
            counter += 1

        return User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_active=False,
            **validated_data
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Email atau password salah")
        data['user'] = user
        return data


class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = '__all__'
