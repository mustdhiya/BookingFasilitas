# ─────────────────────────────────────────────────────────────────────────────
# accounts/views.py
# ─────────────────────────────────────────────────────────────────────────────
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, logout
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import View
from django.http import JsonResponse
from django.db.models import Q

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from accounts import models
from .models import User, LoginHistory
from .serializers import (
    UserSerializer, RegisterSerializer,
    LoginSerializer, LoginHistorySerializer
)
from research.models import ResearchTitle


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _parse_user_agent(user_agent_string):
    ua = user_agent_string.lower()

    if 'edg/' in ua or 'edge/' in ua:
        browser = 'Microsoft Edge'
    elif 'opr/' in ua or 'opera' in ua:
        browser = 'Opera'
    elif 'chrome/' in ua and 'chromium' not in ua:
        browser = 'Google Chrome'
    elif 'firefox/' in ua:
        browser = 'Mozilla Firefox'
    elif 'safari/' in ua and 'chrome' not in ua:
        browser = 'Safari'
    else:
        browser = 'Browser Lain'

    if any(x in ua for x in ['iphone', 'android', 'mobile', 'blackberry']):
        device_type = 'Mobile'
    elif any(x in ua for x in ['ipad', 'tablet']):
        device_type = 'Tablet'
    else:
        device_type = 'Desktop'

    if 'windows' in ua:
        os_name = 'Windows'
    elif 'macintosh' in ua or 'mac os' in ua:
        os_name = 'macOS'
    elif 'iphone' in ua or 'ipad' in ua:
        os_name = 'iOS'
    elif 'android' in ua:
        os_name = 'Android'
    elif 'linux' in ua:
        os_name = 'Linux'
    else:
        os_name = 'Unknown OS'

    return {'browser': browser, 'device_type': device_type, 'os': os_name}


# ─────────────────────────────────────────────────────────────────────────────
# AUTH — LOGIN
# ─────────────────────────────────────────────────────────────────────────────
class LoginPageView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        return render(request, self.template_name)

    def post(self, request):
        identifier = request.POST.get('username', '').strip()
        password   = request.POST.get('password', '')
        remember   = request.POST.get('remember')
        next_url   = request.POST.get('next') or request.GET.get('next') or '/'

        ip_address = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
        )
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        ua_parsed = _parse_user_agent(ua_string)

        if not identifier or not password:
            messages.error(request, 'Email/NIM dan password wajib diisi.')
            return render(request, self.template_name)

        # ── FIX: 1 query untuk cari user (email ATAU nim) ─────────────────
        try:
            user_obj = User.objects.get(
                Q(email=identifier) | Q(nim_nip=identifier)
            )
        except User.DoesNotExist:
            LoginHistory.objects.create(
                user=None,
                ip_address=ip_address,
                user_agent=ua_string,
                browser=ua_parsed['browser'],
                device_type=ua_parsed['device_type'],
                os=ua_parsed['os'],
                success=False,
                fail_reason='not_found',
            )
            messages.error(request, 'Email/NIM atau password salah.')
            return render(request, self.template_name)
        except User.MultipleObjectsReturned:
            # Sangat jarang — fallback ke email
            user_obj = User.objects.filter(email=identifier).first()
            if not user_obj:
                messages.error(request, 'Email/NIM atau password salah.')
                return render(request, self.template_name)

        # ── Cek akun belum aktif ──────────────────────────────────────────
        if not user_obj.is_active:
            LoginHistory.objects.create(
                user=user_obj,
                ip_address=ip_address,
                user_agent=ua_string,
                browser=ua_parsed['browser'],
                device_type=ua_parsed['device_type'],
                os=ua_parsed['os'],
                success=False,
                fail_reason='not_verified',
            )
            return render(request, self.template_name, {
                'account_pending': True,
                'pending_nim':     user_obj.nim_nip or '—',
                'pending_date':    user_obj.date_joined.strftime('%d %b %Y'),
            })

        # ── Verifikasi password ───────────────────────────────────────────
        user = authenticate(request, username=user_obj.email, password=password)
        if user is None:
            LoginHistory.objects.create(
                user=user_obj,
                ip_address=ip_address,
                user_agent=ua_string,
                browser=ua_parsed['browser'],
                device_type=ua_parsed['device_type'],
                os=ua_parsed['os'],
                success=False,
                fail_reason='wrong_password',
            )
            messages.error(request, 'Email/NIM atau password salah.')
            return render(request, self.template_name)

        # ── Login berhasil ────────────────────────────────────────────────
        LoginHistory.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=ua_string,
            browser=ua_parsed['browser'],
            device_type=ua_parsed['device_type'],
            os=ua_parsed['os'],
            success=True,
        )

        auth_login(request, user)               # ← hanya 1x, duplikat dihapus

        if not remember:
            request.session.set_expiry(0)

        from django.utils.http import url_has_allowed_host_and_scheme
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = '/'

        return redirect(next_url)


# ─────────────────────────────────────────────────────────────────────────────
# AUTH — REGISTER
# ─────────────────────────────────────────────────────────────────────────────
class RegisterPageView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name, {
            'angkatan_choices': range(2026, 2019, -1),
        })

    def post(self, request):
        from django.http import JsonResponse

        is_ajax = request.POST.get('_ajax') == '1'
        data    = request.POST.dict()

        fields_to_clean = ['angkatan', 'nim_nip', 'prodi', 'instansi', 'phone']
        for field in fields_to_clean:
            if field in data and data[field].strip() == '':
                del data[field]

        for key, file in request.FILES.items():
            data[key] = file

        serializer = RegisterSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Registrasi berhasil! Akun sedang diverifikasi admin.'
                })
            messages.success(request, 'Registrasi berhasil!')
            return redirect('login')

        if is_ajax:
            flat_errors = {
                field: str(errs[0] if isinstance(errs, list) else errs)
                for field, errs in serializer.errors.items()
            }
            return JsonResponse({
                'success': False,
                'message': next(iter(flat_errors.values()), 'Periksa kembali data Anda.'),
                'errors':  flat_errors,
            }, status=400)

        for field, errs in serializer.errors.items():
            for e in errs:
                messages.error(request, f'{field}: {e}')
        return render(request, self.template_name, {
            'angkatan_choices': range(2026, 2019, -1),
        })


# ─────────────────────────────────────────────────────────────────────────────
# AUTH — LOGOUT
# ─────────────────────────────────────────────────────────────────────────────
class LogoutView(View):
    def post(self, request):
        auth_logout(request)
        return redirect('login')

    def get(self, request):
        auth_logout(request)
        return redirect('login')


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────────────────
class ProfilePageView(LoginRequiredMixin, View):
    login_url     = '/login/'
    template_name = 'profile.html'

    def get(self, request):
        login_history = LoginHistory.objects.filter(
            user=request.user,
            success=True
        ).order_by('-login_at')[:5]
        return render(request, self.template_name, {'login_history': login_history})

    def post(self, request):
        action = request.POST.get('action')
        if action == 'update_profile':
            return self._handle_profile_update(request)
        elif action == 'change_password':
            return self._handle_change_password(request)
        messages.error(request, 'Aksi tidak dikenal.')
        return redirect('profile')

    def _handle_profile_update(self, request):
        user      = request.user
        full_name = request.POST.get('full_name', '').strip()
        phone     = request.POST.get('phone', '').strip()
        instansi  = request.POST.get('instansi', '').strip()

        if full_name:
            parts           = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name  = parts[1] if len(parts) > 1 else ''
        if phone:
            user.phone = phone
        if instansi:
            user.instansi = instansi

        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            if avatar_file.size > 2 * 1024 * 1024:
                messages.error(request, 'Ukuran foto maksimal 2MB.')
                return redirect('profile')
            if avatar_file.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
                messages.error(request, 'Format foto harus JPG, PNG, atau WebP.')
                return redirect('profile')
            if user.avatar:
                import os
                if os.path.isfile(user.avatar.path):
                    os.remove(user.avatar.path)
            user.avatar = avatar_file

        user.save()
        messages.success(request, 'Profil berhasil diperbarui.')
        return redirect('profile')

    def _handle_change_password(self, request):
        old_password     = request.POST.get('old_password', '')
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not request.user.check_password(old_password):
            messages.error(request, 'Password lama salah.')
            return redirect('profile')
        if len(new_password) < 8:
            messages.error(request, 'Password baru minimal 8 karakter.')
            return redirect('profile')
        if new_password != confirm_password:
            messages.error(request, 'Konfirmasi password tidak cocok.')
            return redirect('profile')

        request.user.set_password(new_password)
        request.user.save()

        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password berhasil diubah.')
        return redirect('profile')


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
class DashboardPageView(LoginRequiredMixin, View):
    login_url     = '/login/'
    template_name = 'dashboard.html'

    def get(self, request):
        user    = request.user
        is_umkt = user.user_type == 'umkt'

        stats = {
            'rooms_count':          user.room_bookings.filter(created_at__month=timezone.now().month).count() if hasattr(user, 'room_bookings') else 0,
            'tools_active':         user.tool_bookings.filter(status='approved').count()                      if hasattr(user, 'tool_bookings') else 0,
            'practicum_registered': user.practicum_registrations.count()                                      if hasattr(user, 'practicum_registrations') else 0,
            'research_active':      user.research_requests.filter(status='active').count()                    if hasattr(user, 'research_requests') else 0,
        }

        # ── FIX: room_bookings dan tool_bookings dipisah dengan benar ─────
        activities = []
        if hasattr(user, 'room_bookings'):
            for b in user.room_bookings.select_related('room').order_by('-created_at')[:3]:
                activities.append({
                    'title':        f'Ruangan · {b.room.name}',
                    'subtitle':     b.created_at.strftime('%d %b %Y'),
                    'status':       b.status,
                    'status_label': b.get_status_display(),
                })
        if hasattr(user, 'tool_bookings'):
            for b in user.tool_bookings.select_related('tool').order_by('-created_at')[:3]:
                activities.append({
                    'title':        f'Alat Tes · {b.tool.name}',
                    'subtitle':     b.created_at.strftime('%d %b %Y'),
                    'status':       b.status,
                    'status_label': b.get_status_display(),
                })
        activities = sorted(activities, key=lambda x: x['subtitle'], reverse=True)[:6]

        return render(request, self.template_name, {
            'stats':      stats,
            'activities': activities,
            'is_umkt':    is_umkt,
        })


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN MIXIN
# ─────────────────────────────────────────────────────────────────────────────
class AdminOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/login/'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.role == 'laboran'


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — MANAJEMEN AKUN
# ─────────────────────────────────────────────────────────────────────────────
class AdminAkunView(AdminOnlyMixin, View):
    template_name = 'admin/ManaAdmin.html'

    def get(self, request):
        status_filter = request.GET.get('status', 'all')
        q             = request.GET.get('q', '')

        qs = User.objects.exclude(is_superuser=True)\
                 .select_related('verified_by', 'rejected_by')\
                 .order_by('-created_at')

        if status_filter == 'pending':
            qs = qs.filter(is_active=False, is_verified=False)
        elif status_filter == 'active':
            qs = qs.filter(is_active=True, is_verified=True)
        elif status_filter == 'rejected':
            qs = qs.filter(is_active=False, is_verified=True, rejection_reason__isnull=False)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False, is_verified=True, rejection_reason__isnull=True)

        if q:
            qs = qs.filter(
                models.Q(first_name__icontains=q) |
                models.Q(last_name__icontains=q)  |
                models.Q(email__icontains=q)       |
                models.Q(nim_nip__icontains=q)
            )

        base_qs = User.objects.exclude(is_superuser=True)
        stats = {
            'pending':  base_qs.filter(is_active=False, is_verified=False).count(),
            'active':   base_qs.filter(is_active=True,  is_verified=True).count(),
            'inactive': base_qs.filter(is_active=False, is_verified=True).count(),
            'total':    base_qs.count(),
        }

        return render(request, self.template_name, {
            'user_list':     qs,
            'stats':         stats,
            'status_filter': status_filter,
            'q':             q,
            'status_tabs': [
                ('all',      'Semua'),
                ('pending',  'Menunggu Verifikasi'),
                ('active',   'Aktif & Terverifikasi'),
                ('rejected', 'Nonaktif'),
            ],
        })


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — AKSI AKUN
# ─────────────────────────────────────────────────────────────────────────────
class AdminAkunAksiView(AdminOnlyMixin, View):

    def post(self, request, pk):
        try:
            target = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return JsonResponse({'ok': False, 'msg': 'User tidak ditemukan.'}, status=404)

        aksi = request.POST.get('aksi')

        if aksi == 'approve':
            target.is_active        = True
            target.is_verified      = True
            target.verified_at      = timezone.now()
            target.verified_by      = request.user
            target.rejection_reason = None
            target.rejected_at      = None
            target.rejected_by      = None
            target.save()
            msg = f'Akun {target.get_full_name()} berhasil diverifikasi.'

        elif aksi == 'reject':
            reason                  = request.POST.get('reason', '').strip()
            target.is_active        = False
            target.is_verified      = True
            target.rejection_reason = reason or None
            target.rejected_at      = timezone.now()
            target.rejected_by      = request.user
            target.save()
            msg = f'Akun {target.get_full_name()} ditolak.'

        elif aksi == 'deactivate':
            target.is_active   = False
            target.is_verified = True
            target.save()
            msg = f'Akun {target.get_full_name()} dinonaktifkan.'

        elif aksi == 'reactivate':
            target.is_active        = True
            target.is_verified      = True
            target.rejection_reason = None
            target.rejected_at      = None
            target.save()
            msg = f'Akun {target.get_full_name()} diaktifkan kembali.'

        else:
            return JsonResponse({'ok': False, 'msg': 'Aksi tidak dikenal.'}, status=400)

        return JsonResponse({
            'ok':          True,
            'msg':         msg,
            'is_active':   target.is_active,
            'is_verified': target.is_verified,
        })


# ─────────────────────────────────────────────────────────────────────────────
# RESEARCH — TITLE SLOTS
# ─────────────────────────────────────────────────────────────────────────────
class TitleSlotsView(View):
    def get(self, request):
        titles = ResearchTitle.objects.filter(is_active=True)
        data   = [
            {
                'id':         t.pk,
                'slots_used': t.slots_used,
                'quota':      t.quota,
                'is_full':    t.is_full,
            }
            for t in titles
        ]
        return JsonResponse(data, safe=False)


# ─────────────────────────────────────────────────────────────────────────────
# API VIEWS (REST Framework)
# ─────────────────────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': 'Registrasi berhasil! Silakan login.',
            'user':    UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user        = serializer.validated_data['user']
        token, _    = Token.objects.get_or_create(user=user)
        LoginHistory.objects.create(
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            device_type='API',
            os='Unknown',
            success=True,
        )
        return Response({
            'token': token.key,
            'user':  UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    logout(request)
    return Response({'message': 'Logout berhasil'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    return Response(UserSerializer(request.user).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def profile_update_view(request):
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Profil berhasil diperbarui', 'user': serializer.data})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    if not request.user.check_password(old_password):
        return Response({'error': 'Password lama salah'}, status=status.HTTP_400_BAD_REQUEST)
    request.user.set_password(new_password)
    request.user.save()
    return Response({'message': 'Password berhasil diubah'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def login_history_view(request):
    history    = LoginHistory.objects.filter(user=request.user)[:5]
    serializer = LoginHistorySerializer(history, many=True)
    return Response(serializer.data)
