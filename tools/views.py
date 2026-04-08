# tools/views.py
import json
from django.http              import JsonResponse
from django.shortcuts         import get_object_or_404
from django.views             import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils             import timezone
from .models                  import TestTool, ToolRental
from .forms                   import TestToolForm, ToolRentalForm


# ── Mixins ────────────────────────────────────────────────────────────────────

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_json(request):
    try:
        return json.loads(request.body), None
    except (ValueError, json.JSONDecodeError) as e:
        return None, JsonResponse({'status': 'error', 'errors': {'__all__': [str(e)]}}, status=400)


def _rental_to_dict(r):
    return {
        'id':               r.pk,
        'tool_detail': {
            'name': r.tool.name,
            'code': r.tool.code,
        },
        'transaction_type': r.transaction_type,
        'institution':      r.institution,
        'purpose':          r.purpose,
        'quantity':         r.quantity,
        'date_start':       r.date_start.strftime('%d %b %Y') if r.date_start else None,
        'date_end':         r.date_end.strftime('%d %b %Y')   if r.date_end   else None,
        'status':           r.status,
        'total_cost':       r.total_cost,
        'fine_amount':      r.fine_amount,
        'is_paid':          r.is_paid,
        'has_payment_proof': bool(r.payment_proof),  # ← tambah ini
        'created_at':       r.created_at.strftime('%d %b %Y'),
    }

# ── Admin: Master Data ────────────────────────────────────────────────────────

class ToolCreateView(AdminRequiredMixin, View):
    def post(self, request):
        body, err = _parse_json(request)
        if err:
            return err
        form = TestToolForm(body)
        if form.is_valid():
            tool = form.save()
            return JsonResponse({'status': 'ok', 'id': tool.pk, 'name': tool.name})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


class ToolUpdateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        tool = get_object_or_404(TestTool, pk=pk)
        body, err = _parse_json(request)
        if err:
            return err
        body.pop('stock', None)   # stok tidak boleh diubah via form edit
        form = TestToolForm(body, instance=tool)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'ok', 'id': tool.pk})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


class ToolJsonView(AdminRequiredMixin, View):
    def get(self, request, pk):
        tool = get_object_or_404(TestTool, pk=pk)
        return JsonResponse({
            'pk':               tool.pk,
            'code':             tool.code,
            'name':             tool.name,
            'description':      tool.description or '',
            'kategori':         tool.kategori,
            'unit':             tool.unit,
            'stock':            tool.stock,
            'price_per_unit':   tool.price_per_unit,
            'is_active':        tool.is_active,
            'transaction_type': tool.transaction_type, 
            'borrow_count':     tool.rentals.exclude(status='cancelled').count(),
            'created_at':       tool.created_at.strftime('%d %b %Y'),
        })

class ToolToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        tool           = get_object_or_404(TestTool, pk=pk)
        tool.is_active = not tool.is_active
        tool.save()
        return JsonResponse({'status': 'ok', 'is_active': tool.is_active})


class ToolAdjustStockView(AdminRequiredMixin, View):
    def post(self, request, pk):
        tool = get_object_or_404(TestTool, pk=pk)
        body, err = _parse_json(request)
        if err:
            return err
        try:
            adjustment = int(body.get('adjustment', 0))
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Nilai adjustment tidak valid'}, status=400)

        new_stock = tool.stock + adjustment
        if new_stock < 0:
            return JsonResponse({'error': 'Stok tidak boleh negatif'}, status=400)
        tool.stock = new_stock
        tool.save()
        return JsonResponse({'status': 'ok', 'new_stock': tool.stock})


# ── Public: List Alat Tes ────────────────────────────────────────────────────

class ToolListView(LoginRequiredMixin, View):
    def get(self, request):
        tools = TestTool.objects.filter(is_active=True).order_by('code')
        results = [{
            'id':               tool.pk,
            'code':             tool.code,
            'name':             tool.name,
            'description':      tool.description or '',
            'category':         tool.kategori,
            'category_display': tool.get_kategori_display(),
            'unit':             tool.unit,
            'unit_display':     tool.get_unit_display(),
            'stock':            tool.stock,
            'price_per_unit':   tool.price_per_unit,
            'is_available':     tool.is_available,

            # ── FIX: mapping transaction_type → item_type yang dipakai frontend ──
            'item_type': 'consumable' if tool.transaction_type == 'beli' else 'tool',

            # Kirim juga transaction_type asli supaya JS bisa filter pinjam vs sewa
            'transaction_type': tool.transaction_type,
        } for tool in tools]
        return JsonResponse({'status': 'ok', 'results': results})


# ── User: Rental CRUD ────────────────────────────────────────────────────────
class ToolRentalCreateView(LoginRequiredMixin, View):
    def post(self, request):
        post_data = request.POST.copy()

        # Parse components dari JSON string → Python list
        raw_components = post_data.get('components', '[]')
        try:
            parsed_components = json.loads(raw_components)
            if not isinstance(parsed_components, list):
                parsed_components = []
        except (ValueError, TypeError):
            parsed_components = []

        # Hapus dari post_data supaya form tidak bingung validasi JSONField
        post_data.pop('components', None)

        form = ToolRentalForm(post_data, request.FILES)
        if form.is_valid():
            rental = form.save(commit=False)
            rental.user             = request.user
            rental.transaction_type = request.POST.get('transaction_type', 'pinjam')
            rental.components       = parsed_components  # ← set manual setelah form.save()
            rental.save()
            return JsonResponse({'status': 'ok', 'id': rental.pk})

        errors_flat = {k: list(v) for k, v in form.errors.items()}
        return JsonResponse({'status': 'error', 'errors': errors_flat}, status=400)



class MyRentalsView(LoginRequiredMixin, View):
    """
    GET /api/tools/rentals/my/
    Daftar rental milik user yang sedang login.
    """
    def get(self, request):
        rentals = (
            ToolRental.objects
            .filter(user=request.user)
            .select_related('tool')
            .order_by('-created_at')[:50]
        )
        return JsonResponse({
            'status':  'ok',
            'results': [_rental_to_dict(r) for r in rentals],
        })


class ToolRentalCancelView(LoginRequiredMixin, View):
    """POST /api/tools/rentals/<pk>/cancel/"""
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk)
        if rental.user != request.user:
            return JsonResponse({'error': 'Tidak diizinkan'}, status=403)
        if rental.status != 'pending':
            return JsonResponse({'error': 'Hanya rental pending yang bisa dibatalkan'}, status=400)
        rental.status = 'cancelled'
        rental.save()
        return JsonResponse({'status': 'ok'})


class ToolRentalRequestReturnView(LoginRequiredMixin, View):
    """
    POST /api/tools/rentals/<pk>/request-return/
    User mengajukan pengembalian — status jadi 'returning', admin yang konfirmasi fisik.
    """
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk, user=request.user)
        if rental.status not in ('borrowed', 'overdue'):
            return JsonResponse(
                {'error': f'Tidak bisa ajukan kembali dari status: {rental.status}'},
                status=400
            )
        rental.status = 'returning'
        rental.save()
        return JsonResponse({'status': 'ok'})


class ToolRentalUploadPaymentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk, user=request.user)

        # Izinkan sewa dan beli
        if rental.transaction_type not in ('sewa', 'beli'):
            return JsonResponse({'error': 'Tipe transaksi tidak memerlukan bukti bayar'}, status=400)

        if rental.status not in ('approved', 'borrowed'):
            return JsonResponse({'error': f'Status tidak valid: {rental.status}'}, status=400)

        proof = request.FILES.get('payment_proof')
        if not proof:
            return JsonResponse({'error': 'File tidak ditemukan'}, status=400)

        rental.payment_proof = proof
        rental.is_paid       = False
        rental.status        = 'payment_pending'
        rental.save(update_fields=['payment_proof', 'is_paid', 'status'])

        return JsonResponse({'status': 'ok', 'rental_status': rental.status})
class ToolRentalVerifyPaymentView(AdminRequiredMixin, View):
    """POST /api/tools/rentals/<pk>/verify-payment/ — admin terima bukti bayar"""
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk)
        if rental.status != 'payment_pending':
            return JsonResponse(
                {'error': f'Status bukan payment_pending, saat ini: {rental.status}'},
                status=400
            )
        rental.is_paid = True
        rental.status  = 'borrowed'
        rental.save(update_fields=['is_paid', 'status'])
        return JsonResponse({'status': 'ok', 'new_status': rental.status})


class ToolRentalRejectPaymentView(AdminRequiredMixin, View):
    """POST /api/tools/rentals/<pk>/reject-payment/ — admin tolak bukti bayar"""
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk)
        if rental.status != 'payment_pending':
            return JsonResponse(
                {'error': f'Status bukan payment_pending, saat ini: {rental.status}'},
                status=400
            )
        body, _              = _parse_json(request)
        rental.is_paid       = False
        rental.payment_proof = None
        rental.status        = 'approved'   # kembalikan ke approved, user upload ulang
        rental.admin_notes   = (body or {}).get('notes', 'Bukti pembayaran ditolak oleh admin')
        rental.save(update_fields=['is_paid', 'payment_proof', 'status', 'admin_notes'])
        return JsonResponse({'status': 'ok', 'new_status': rental.status})
    
# views.py
class ToolRentalMarkBorrowedView(AdminRequiredMixin, View):
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk)
        if rental.status != 'approved':
            return JsonResponse({'error': f'Status bukan approved: {rental.status}'}, status=400)
        rental.status = 'borrowed'
        rental.save(update_fields=['status'])
        return JsonResponse({'status': 'ok'})
    
from django.core.mail import send_mail
from django.conf import settings

class ToolRentalSendReminderView(AdminRequiredMixin, View):
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk)
        
        user_email = rental.user.email
        if not user_email:
            return JsonResponse({'error': 'User tidak punya email'}, status=400)

        tgl_kembali = rental.date_end.strftime('%d %B %Y') if rental.date_end else '—'
        nama_user   = rental.user.get_full_name() or rental.user.username
        nama_alat   = rental.tool.name

        subject = f'[Lab UMKT] Reminder Pengembalian Alat — {nama_alat}'
        message = f"""
Yth. {nama_user},

Ini adalah pengingat bahwa Anda masih meminjam alat tes berikut:

  Alat   : {nama_alat} ({rental.tool.code})
  Jumlah : {rental.quantity} {rental.tool.unit}
  Batas  : {tgl_kembali}

Mohon segera kembalikan alat ke Lab Psikologi UMKT sesuai jadwal.
Keterlambatan akan dikenakan denda sesuai ketentuan.

Terima kasih,
Admin Lab Psikologi UMKT
        """.strip()

        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])
            return JsonResponse({'status': 'ok', 'sent_to': user_email})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class ToolRentalUploadFineProofView(LoginRequiredMixin, View):
    """
    POST /api/tools/rentals/<pk>/upload-fine-proof/
    User upload bukti bayar denda — multipart, field: fine_proof.
    """
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk, user=request.user)
        if rental.status not in ('borrowed', 'overdue'):
            return JsonResponse({'error': 'Status tidak valid untuk upload bukti denda'}, status=400)
        proof = request.FILES.get('fine_proof')
        if not proof:
            return JsonResponse({'error': 'File tidak ditemukan'}, status=400)
        # Simpan ke field payment_proof (reuse), atau tambah field fine_proof di model
        rental.payment_proof = proof
        rental.save()
        return JsonResponse({'status': 'ok'})


# ── Admin: Rental Actions ────────────────────────────────────────────────────

class ToolRentalApproveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk)
        if rental.status != 'pending':
            return JsonResponse({'error': f'Status saat ini: {rental.status}'}, status=400)
        tool = rental.tool
        if tool.stock < rental.quantity:
            return JsonResponse(
                {'error': f'Stok tidak mencukupi ({tool.stock} tersedia)'},
                status=400
            )
        tool.stock    -= rental.quantity
        tool.save()
        rental.status      = 'approved'
        rental.approved_by = request.user
        rental.approved_at = timezone.now()
        rental.save()
        return JsonResponse({'status': 'ok'})


class ToolRentalDeclineView(AdminRequiredMixin, View):
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk)
        if rental.status not in ('pending', 'approved'):
            return JsonResponse({'error': 'Tidak bisa ditolak dari status ini'}, status=400)
        body, _            = _parse_json(request)
        rental.status      = 'declined'
        rental.admin_notes = (body or {}).get('notes', '')
        rental.save()
        return JsonResponse({'status': 'ok'})


class ToolRentalReturnView(AdminRequiredMixin, View):
    """
    POST /api/tools/rentals/<pk>/return/
    Admin konfirmasi fisik alat sudah diterima — stok dikembalikan.
    """
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk)
        if rental.status not in ('borrowed', 'returning', 'overdue'):
            return JsonResponse(
                {'error': f'Status "{rental.status}" tidak bisa dikembalikan'},
                status=400
            )
        tool        = rental.tool
        tool.stock += rental.quantity
        tool.save()
        rental.status      = 'returned'
        rental.returned_at = timezone.now()
        rental.save()
        return JsonResponse({'status': 'ok', 'new_stock': tool.stock})
