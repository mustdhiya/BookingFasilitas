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
    """Serialisasi ToolRental untuk JSON response frontend."""
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
    """
    GET /api/tools/list/
    Mengembalikan semua alat aktif untuk card grid di halaman user.
    """
    def get(self, request):
        tools = TestTool.objects.filter(is_active=True).order_by('code')
        results = [{
            'id':                tool.pk,
            'code':              tool.code,
            'name':              tool.name,
            'description':       tool.description or '',
            'category':          tool.kategori,
            'category_display':  tool.get_kategori_display(),
            'unit':              tool.unit,
            'unit_display':      tool.get_unit_display(),
            'stock':             tool.stock,
            'price_per_unit':    tool.price_per_unit,
            'is_available':      tool.is_available,
            # item_type: semua model TestTool dianggap 'tool' untuk sekarang
            # jika kelak ada model Consumable terpisah, bisa diubah
            'item_type':         'tool',
        } for tool in tools]
        return JsonResponse({'status': 'ok', 'results': results})


# ── User: Rental CRUD ────────────────────────────────────────────────────────

class ToolRentalCreateView(LoginRequiredMixin, View):
    """
    POST /api/tools/rentals/
    Menerima multipart/form-data (ada file upload: activity_letter, agreement_file).
    """
    def post(self, request):
        form = ToolRentalForm(request.POST, request.FILES)
        if form.is_valid():
            rental = form.save(commit=False)
            rental.user             = request.user
            rental.transaction_type = request.POST.get('transaction_type', 'pinjam')
            # Hitung total_cost sebelum save (override save() sudah ada, tapi pastikan)
            rental.save()
            return JsonResponse({'status': 'ok', 'id': rental.pk})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


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
    """
    POST /api/tools/rentals/<pk>/upload-payment/
    User upload bukti bayar sewa — multipart, field: payment_proof.
    """
    def post(self, request, pk):
        rental = get_object_or_404(ToolRental, pk=pk, user=request.user)
        if rental.status != 'approved':
            return JsonResponse({'error': 'Rental belum disetujui'}, status=400)
        proof = request.FILES.get('payment_proof')
        if not proof:
            return JsonResponse({'error': 'File bukti bayar tidak ditemukan'}, status=400)
        rental.payment_proof = proof
        rental.save()
        return JsonResponse({'status': 'ok'})


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
