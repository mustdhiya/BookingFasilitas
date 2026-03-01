# tools/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ── Admin: Master Data ────────────────────────────────────────────
    path('admin/alat/create/',                views.ToolCreateView.as_view(),       name='tool-create'),
    path('admin/alat/<int:pk>/edit/',         views.ToolUpdateView.as_view(),       name='tool-edit'),
    path('admin/alat/<int:pk>/json/',         views.ToolJsonView.as_view(),         name='tool-json'),
    path('admin/alat/<int:pk>/toggle/',       views.ToolToggleView.as_view(),       name='tool-toggle'),
    path('admin/alat/<int:pk>/adjust-stock/', views.ToolAdjustStockView.as_view(),  name='tool-adjust-stock'),

    # ── Public: List Alat Tes (untuk card grid di frontend user) ─────
    path('list/',                             views.ToolListView.as_view(),         name='tool-list'),

    # ── Rentals (User) ────────────────────────────────────────────────
    path('rentals/',                          views.ToolRentalCreateView.as_view(), name='tool-rental-create'),
    path('rentals/my/',                       views.MyRentalsView.as_view(),        name='tool-rental-my'),
    path('rentals/<int:pk>/cancel/',          views.ToolRentalCancelView.as_view(), name='tool-rental-cancel'),
    path('rentals/<int:pk>/request-return/',  views.ToolRentalRequestReturnView.as_view(), name='tool-rental-request-return'),
    path('rentals/<int:pk>/upload-payment/',  views.ToolRentalUploadPaymentView.as_view(), name='tool-rental-upload-payment'),
    path('rentals/<int:pk>/upload-fine-proof/', views.ToolRentalUploadFineProofView.as_view(), name='tool-rental-upload-fine-proof'),

    # ── Rentals (Admin) ───────────────────────────────────────────────
    path('rentals/<int:pk>/approve/',         views.ToolRentalApproveView.as_view(), name='tool-rental-approve'),
    path('rentals/<int:pk>/decline/',         views.ToolRentalDeclineView.as_view(), name='tool-rental-decline'),
    path('rentals/<int:pk>/return/',          views.ToolRentalReturnView.as_view(),  name='tool-rental-return'),
]
