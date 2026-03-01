from django import forms
from django.utils import timezone
from .models import RoomBooking, Room


class RoomBookingForm(forms.ModelForm):
    class Meta:
        model  = RoomBooking
        fields = ['room', 'date_start', 'date_end', 'participants', 'purpose']  # ← hapus start_time, end_time
        widgets = {
            'date_start': forms.DateInput(attrs={'type': 'date'}),
            'date_end':   forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned      = super().clean()
        date_start   = cleaned.get('date_start')
        date_end     = cleaned.get('date_end')
        room         = cleaned.get('room')
        participants = cleaned.get('participants')

        today = timezone.localdate()

        if date_start and date_start < today:
            self.add_error('date_start', 'Tanggal mulai tidak boleh di masa lalu.')

        if date_start and date_end:
            if date_end < date_start:
                self.add_error('date_end', 'Tanggal selesai tidak boleh sebelum tanggal mulai.')

        if room and participants and participants > room.capacity:
            self.add_error(
                'participants',
                f'Jumlah peserta melebihi kapasitas ruangan ({room.capacity} orang).'
            )

        if room and date_start and date_end:
            conflict = RoomBooking.objects.filter(
                room=room,
                status__in=['pending', 'approved'],
                date_start__lte=date_end,
                date_end__gte=date_start,
            )
            if self.instance.pk:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise forms.ValidationError(
                    'Ruangan sudah dipesan pada rentang tanggal tersebut. '
                    'Silakan pilih tanggal lain atau cek kalender ketersediaan.'
                )

        if room and date_start and date_end:
            from .models import RoomBlockSchedule
            from datetime import timedelta
            blocks = RoomBlockSchedule.objects.filter(room=room, is_active=True)
            d = date_start
            while d <= date_end:
                for b in blocks:
                    if b.covers_date(d):
                        raise forms.ValidationError(
                            f'Tanggal {d.strftime("%d %b %Y")} terblokir: {b.name}.'
                        )
                d += timedelta(days=1)

        return cleaned
