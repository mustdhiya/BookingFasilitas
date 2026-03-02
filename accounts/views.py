from django.utils import timezone
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.views.generic import TemplateView
from .models import User, LoginHistory
from .serializers import (
    UserSerializer, RegisterSerializer, 
    LoginSerializer, LoginHistorySerializer
)
# accounts/views.py
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from .serializers import RegisterSerializer
from .models import User
from accounts import models

class LoginPageView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name)

    def post(self, request):
        identifier = request.POST.get('username', '').strip()
        password   = request.POST.get('password', '')
        remember   = request.POST.get('remember')

        # Info untuk LoginHistory
        ip_address = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
        )
        ua_string  = request.META.get('HTTP_USER_AGENT', '')
        ua_parsed  = _parse_user_agent(ua_string)

        if not identifier or not password:
            messages.error(request, 'Email/NIM dan password wajib diisi.')
            return render(request, self.template_name)

        # Authenticate via email
        user = authenticate(request, username=identifier, password=password)

        # Fallback via NIM
        if user is None:
            try:
                found = User.objects.get(nim_nip=identifier)
                user = authenticate(request, username=found.email, password=password)
            except User.DoesNotExist:
                pass

        if user is None:
            # Cek akun pending
            pending = None
            try:
                pending = User.objects.get(email=identifier, is_active=False)
            except User.DoesNotExist:
                try:
                    pending = User.objects.get(nim_nip=identifier, is_active=False)
                except User.DoesNotExist:
                    pass

            if pending:
                # ← Catat login gagal: akun belum aktif
                LoginHistory.objects.create(
                    user=pending,
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
                    'pending_nim':  pending.nim_nip or '—',
                    'pending_date': pending.date_joined.strftime('%d %b %Y'),
                })

            # ← Catat login gagal: email/password salah
            LoginHistory.objects.create(
                user=None,  # user tidak ditemukan
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

        # ← LOGIN BERHASIL — catat riwayat
        LoginHistory.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=ua_string,
            browser=ua_parsed['browser'],
            device_type=ua_parsed['device_type'],
            os=ua_parsed['os'],
            success=True,
        )

        auth_login(request, user)

        if not remember:
            request.session.set_expiry(0)

        return redirect('home')
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

        # Bangun data dict
        data = request.POST.dict()

        # Supaya serializer menerima None, bukan string ""
        fields_to_clean = ['angkatan', 'nim_nip', 'prodi', 'instansi', 'phone']
        for field in fields_to_clean:
            if field in data and data[field].strip() == '':
                del data[field]  # hapus total — serializer akan pakai default=None

        # Gabungkan FILES
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
                'errors': flat_errors,
            }, status=400)

        for field, errs in serializer.errors.items():
            for e in errs:
                messages.error(request, f'{field}: {e}')
        return render(request, self.template_name, {
            'angkatan_choices': range(2026, 2019, -1),
        })


class LogoutView(View):
    def post(self, request):
        auth_logout(request)
        return redirect('login')

    def get(self, request):
        # Support GET juga untuk fallback
        auth_logout(request)
        return redirect('login')
    
# accounts/views.py — ProfilePageView (ganti yang lama)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User, LoginHistory

class ProfilePageView(LoginRequiredMixin, View):  # ← LoginRequiredMixin + View, bukan TemplateView
    login_url = '/login/'
    template_name = 'profile.html'

    def get(self, request):
        login_history = LoginHistory.objects.filter(
            user=request.user,
            success=True    
        ).order_by('-login_at')[:5]

        return render(request, self.template_name, {
            'login_history': login_history,
        })


    def post(self, request):
        action = request.POST.get('action')  # bedakan aksi dari form mana

        if action == 'update_profile':
            return self._handle_profile_update(request)
        elif action == 'change_password':
            return self._handle_change_password(request)

        messages.error(request, 'Aksi tidak dikenal.')
        return redirect('profile')

    def _handle_profile_update(self, request):
        user = request.user
        full_name = request.POST.get('full_name', '').strip()
        phone     = request.POST.get('phone', '').strip()
        instansi  = request.POST.get('instansi', '').strip()

        if full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name  = parts[1] if len(parts) > 1 else ''

        if phone:
            user.phone = phone
        if instansi:
            user.instansi = instansi

        # ← TAMBAH INI: handle upload avatar
        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']

            # Validasi ukuran: max 2MB
            if avatar_file.size > 2 * 1024 * 1024:
                messages.error(request, 'Ukuran foto maksimal 2MB.')
                return redirect('profile')

            # Validasi format
            allowed = ['image/jpeg', 'image/png', 'image/webp']
            if avatar_file.content_type not in allowed:
                messages.error(request, 'Format foto harus JPG, PNG, atau WebP.')
                return redirect('profile')

            # Hapus foto lama jika ada (opsional, mencegah file numpuk)
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

        # Re-login agar session tidak invalid setelah ganti password
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)

        messages.success(request, 'Password berhasil diubah.')
        return redirect('profile')
def _parse_user_agent(user_agent_string):
    """Parse user agent string → dict {browser, device_type, os}"""
    ua = user_agent_string.lower()

    # Deteksi Browser
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

    # Deteksi Device Type
    if any(x in ua for x in ['iphone', 'android', 'mobile', 'blackberry']):
        device_type = 'Mobile'
    elif any(x in ua for x in ['ipad', 'tablet']):
        device_type = 'Tablet'
    else:
        device_type = 'Desktop'

    # Deteksi OS
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

    return {
        'browser':     browser,
        'device_type': device_type,
        'os':          os_name,
    }


# API Views
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Register new user"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': 'Registrasi berhasil! Silakan login.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# accounts/views.py
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """REST API login — untuk Postman / mobile"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']

        token, created = Token.objects.get_or_create(user=user)

        LoginHistory.objects.create(
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            device_type='API',
            os='Unknown',
            success=True
        )

        # login(request, user)  ← hapus baris ini

        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """User logout — support session & token auth"""
    # Hapus token jika ada (untuk API client)
    try:
        request.user.auth_token.delete()
    except Exception:
        pass  # User login via session, tidak punya token — tidak apa-apa

    logout(request)
    return Response({'message': 'Logout berhasil'}, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Get current user profile"""
    return Response(UserSerializer(request.user).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def profile_update_view(request):
    """Update user profile"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Profil berhasil diperbarui',
            'user': serializer.data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Change user password"""
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not request.user.check_password(old_password):
        return Response(
            {'error': 'Password lama salah'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    request.user.set_password(new_password)
    request.user.save()
    
    return Response({'message': 'Password berhasil diubah'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def login_history_view(request):
    """Get user login history (last 5)"""
    history = LoginHistory.objects.filter(user=request.user)[:5]
    serializer = LoginHistorySerializer(history, many=True)
    return Response(serializer.data)


# accounts/views.py (atau core/views.py)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render

class DashboardPageView(LoginRequiredMixin, View):
    login_url = '/login/'
    template_name = 'dashboard.html'

    def get(self, request):
        user = request.user
        is_umkt = user.user_type == 'umkt'

        stats = {
            'rooms_count':          user.room_bookings.filter(created_at__month=timezone.now().month).count() if hasattr(user, 'room_bookings') else 0,
            'tools_active':         user.tool_bookings.filter(status='approved').count() if hasattr(user, 'tool_bookings') else 0,
            'practicum_registered': user.practicum_registrations.count() if hasattr(user, 'practicum_registrations') else 0,
            'research_active':      user.research_requests.filter(status='active').count() if hasattr(user, 'research_requests') else 0,
        }

        activities = []
        if hasattr(user, 'room_bookings'):
            for b in user.room_bookings.order_by('-created_at')[:3]:
                activities.append({
                    'title':        f'Ruangan · {b.room.name}',
                    'subtitle':     b.created_at.strftime('%d %b %Y'),
                    'status':       b.status,
                    'status_label': b.get_status_display(),
                })
        if hasattr(user, 'tool_bookings'):
            for b in user.tool_bookings.order_by('-created_at')[:3]:
                activities.append({
                    'title':        f'Alat Tes · {b.tool.name}',
                    'subtitle':     b.created_at.strftime('%d %b %Y'),
                    'status':       b.status,
                    'status_label': b.get_status_display(),
                })
        activities = sorted(activities, key=lambda x: x['subtitle'], reverse=True)[:6]

        notifications = []
        if not user.is_verified:
            notifications.append({
                'type':    'warning',
                'title':   'Akun Belum Diverifikasi',
                'message': 'Akun Anda sedang menunggu verifikasi admin (1–3 hari kerja).',
            })
        if hasattr(user, 'room_bookings'):
            pending = user.room_bookings.filter(status='pending').count()
            if pending:
                notifications.append({
                    'type':    'info',
                    'title':   'Peminjaman Menunggu Persetujuan',
                    'message': f'{pending} peminjaman ruangan sedang diproses admin.',
                })

        return render(request, self.template_name, {
            'stats':         stats,
            'activities':    activities,
            'notifications': notifications,
            'is_umkt':       is_umkt,  
        })
    

# ── Tambahkan import ini di atas file jika belum ada ──────────────────
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import View
from django.http import JsonResponse
from django.utils import timezone


# ── Mixin admin ───────────────────────────────────────────────────────
class AdminOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/login/'
    def test_func(self):
        return self.request.user.is_staff or self.request.user.role == 'laboran'


# ── Halaman manajemen akun ─────────────────────────────────────────────
class AdminAkunView(AdminOnlyMixin, View):
    template_name = 'admin/ManaAdmin.html'  # sudah ada di tree

    def get(self, request):
        status_filter = request.GET.get('status', 'all')  # ← default 'all', bukan 'pending'
        q             = request.GET.get('q', '')

        # Exclude hanya superuser, tampilkan semua user biasa termasuk staff laboran
        qs = User.objects.exclude(is_superuser=True).order_by('-created_at')

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

        stats = {
            'pending':  User.objects.exclude(is_superuser=True).filter(is_active=False, is_verified=False).count(),
            'active':   User.objects.exclude(is_superuser=True).filter(is_active=True, is_verified=True).count(),
            'inactive': User.objects.exclude(is_superuser=True).filter(is_active=False, is_verified=True).count(),
            'total':    User.objects.exclude(is_superuser=True).count(),
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


# ── Aksi approve / reject / toggle per user ───────────────────────────
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
            # Reset rejection jika sebelumnya pernah ditolak
            target.rejection_reason = None
            target.rejected_at      = None
            target.rejected_by      = None
            target.save()
            msg = f'Akun {target.get_full_name()} berhasil diverifikasi.'

        elif aksi == 'reject':
            reason = request.POST.get('reason', '').strip()
            target.is_active        = False
            target.is_verified      = True   # ← TRUE bukan False, supaya beda dari pending
            target.rejection_reason = reason or None
            target.rejected_at      = timezone.now()
            target.rejected_by      = request.user
            target.save()
            msg = f'Akun {target.get_full_name()} ditolak.'

        elif aksi == 'deactivate':
            target.is_active = False
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
from django.views import View
from django.http import JsonResponse
from research.models import ResearchTitle

class TitleSlotsView(View):
    def get(self, request):
        titles = ResearchTitle.objects.filter(is_active=True)
        data = [
            {
                'id':         t.pk,
                'slots_used': t.slots_used,
                'quota':      t.quota,
                'is_full':    t.is_full,
            }
            for t in titles
        ]
        return JsonResponse(data, safe=False)


