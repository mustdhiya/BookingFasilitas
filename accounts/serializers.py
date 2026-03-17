import re
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User, LoginHistory

# Domain yang diizinkan mendaftar sebagai UMKT
UMKT_EMAIL_DOMAIN = '@umkt.ac.id'

# Pola email bot: nama + 9+ digit angka random
SPAM_EMAIL_PATTERN = re.compile(r'\.\d{9,}[a-z]*@', re.IGNORECASE)

# Domain disposable/tempmail yang umum
BLOCKED_DOMAINS = {
    'mailinator.com', 'guerrillamail.com', 'tempmail.com', 'throwam.com',
    'yopmail.com', 'sharklasers.com', 'guerrillamailblock.com',
    'grr.la', 'spam4.me', 'trashmail.com', 'maildrop.cc', 'dispostable.com',
    'fakeinbox.com', 'mailnull.com', 'spamgourmet.com',
}


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
        value = value.lower().strip()

        # 1. Cek duplikat
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email sudah terdaftar.')

        # 2. Blokir domain disposable / tempmail
        domain = value.split('@')[-1] if '@' in value else ''
        if domain in BLOCKED_DOMAINS:
            raise serializers.ValidationError('Domain email tidak diizinkan.')

        # 3. Blokir pola bot: nama.nama.123456789xxx@domain.com
        if SPAM_EMAIL_PATTERN.search(value):
            raise serializers.ValidationError('Format email tidak valid.')

        return value

    def validate_nim_nip(self, value):
        if not value:
            return value
        # NIM hanya boleh angka, panjang 8–20 karakter
        if not re.fullmatch(r'\d{8,20}', value.strip()):
            raise serializers.ValidationError('NIM harus berupa angka 8-20 digit.')
        # Cek NIM duplikat
        if User.objects.filter(nim_nip=value.strip()).exists():
            raise serializers.ValidationError('NIM sudah terdaftar.')
        return value.strip()

    def validate(self, data):
        # 1. Password match
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Password tidak cocok.'})

        user_type = data.get('user_type', 'umkt')
        email     = data.get('email', '')

        # 2. Validasi UMKT: email WAJIB @umkt.ac.id
        if user_type == 'umkt':
            if not email.endswith(UMKT_EMAIL_DOMAIN):
                raise serializers.ValidationError({
                    'email': f'Mahasiswa/Dosen UMKT wajib menggunakan email {UMKT_EMAIL_DOMAIN}'
                })
            if not data.get('nim_nip'):
                raise serializers.ValidationError({
                    'nim_nip': 'NIM wajib diisi untuk pengguna UMKT.'
                })

        # 3. Validasi non-UMKT: TIDAK boleh pakai @umkt.ac.id
        if user_type == 'non_umkt':
            if email.endswith(UMKT_EMAIL_DOMAIN):
                raise serializers.ValidationError({
                    'email': 'Pengguna eksternal tidak boleh menggunakan email UMKT.'
                })

        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        full_name = validated_data.pop('full_name', '')
        password  = validated_data.pop('password')

        parts      = full_name.strip().split(' ', 1)
        first_name = parts[0] if parts else ''
        last_name  = parts[1] if len(parts) > 1 else ''

        user_type = validated_data.get('user_type', 'umkt')
        validated_data['role'] = 'mahasiswa' if user_type == 'umkt' else 'eksternal'

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
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Email atau password salah')
        data['user'] = user
        return data


class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = LoginHistory
        fields = '__all__'
