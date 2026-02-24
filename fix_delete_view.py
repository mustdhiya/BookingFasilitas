# fix_delete_view.py — jalankan sekali lalu hapus
import re

filepath = 'research/views.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Class baru yang benar
new_class = '''class LecturerDeleteView(AdminRequiredMixin, View):

    def post(self, request, pk):
        lecturer = get_object_or_404(Lecturer, pk=pk)

        active_requests = ResearchRequest.objects.filter(
            lecturer=lecturer,
            status__in=['pending', 'approved']
        )

        if active_requests.exists():
            return JsonResponse({
                'ok':     False,
                'action': 'suggest_deactivate',
                'msg':    f\'Dosen {lecturer.name} masih punya {active_requests.count()} request aktif. Nonaktifkan saja?\',
            })

        title_count = lecturer.research_titles.count()
        ResearchRequest.objects.filter(lecturer=lecturer).delete()
        lecturer.research_titles.all().delete()
        name = lecturer.name
        lecturer.delete()

        return JsonResponse({
            \'ok\':  True,
            \'msg\': f\'Dosen {name} berhasil dihapus\'
                   + (f\' beserta {title_count} judul payung\' if title_count else \'\') + \'.\',
        })


class LecturerDeactivateView(AdminRequiredMixin, View):

    def post(self, request, pk):
        lecturer = get_object_or_404(Lecturer, pk=pk)
        lecturer.is_active = False
        lecturer.save()
        return JsonResponse({
            \'ok\':  True,
            \'msg\': f\'Dosen {lecturer.name} berhasil dinonaktifkan.\',
        })
'''

# Replace class lama dengan regex
pattern = r'class LecturerDeleteView\(.*?\).*?(?=\nclass |\Z)'
if re.search(pattern, content, re.DOTALL):
    new_content = re.sub(pattern, new_class, content, flags=re.DOTALL)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ LecturerDeleteView berhasil diganti!")
else:
    print("❌ Class tidak ditemukan — cek nama class di views.py")

# Verifikasi hasil
with open(filepath, 'r', encoding='utf-8') as f:
    result = f.read()

if 'super().post' in result and 'LecturerDeleteView' in result:
    print("⚠️  MASIH ADA super().post() — patch gagal, ganti manual")
elif 'LecturerDeactivateView' in result:
    print("✅ Verifikasi OK — LecturerDeactivateView sudah ada")
