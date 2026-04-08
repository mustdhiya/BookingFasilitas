# tools/forms.py
from django import forms
from .models import TestTool, ToolRental


class TestToolForm(forms.ModelForm):
    class Meta:
        model  = TestTool
        fields = ['code', 'name', 'description', 'kategori', 'unit',
                  'stock', 'price_per_unit', 'is_active', 'transaction_type'] 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['stock'].required = False

    def clean_code(self):
        code = self.cleaned_data['code'].upper().strip()
        qs   = TestTool.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Kode alat sudah digunakan.')
        return code

class ToolRentalForm(forms.ModelForm):
    class Meta:
        model  = ToolRental
        fields = [
            'tool', 'institution', 'purpose',
            'quantity',
            # 'components',  ← HAPUS dari sini, diset manual di view
            'date_start', 'date_end',
            'payment_time',
            'transaction_type',
            'activity_letter', 'agreement_file',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['activity_letter'].required = False
        self.fields['agreement_file'].required  = False
        self.fields['payment_time'].required    = False

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('date_start')
        end   = cleaned.get('date_end')
        tool  = cleaned.get('tool')
        qty   = cleaned.get('quantity')

        if start and end and end < start:
            raise forms.ValidationError('Tanggal selesai tidak boleh sebelum tanggal mulai.')

        if tool and qty and qty > tool.stock:
            raise forms.ValidationError(
                f'Stok tidak cukup. Stok tersedia: {tool.stock} {tool.unit}.'
            )

        if not cleaned.get('payment_time'):
            cleaned['payment_time'] = 'after'

        return cleaned