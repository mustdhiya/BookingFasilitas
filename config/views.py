from django.shortcuts import render


def panduan_info_view(request):
    context = {
        'sections': [
            {'slug': 'panduan-peminjaman', 'title': 'Panduan Peminjaman', 'icon': 'inventory_2'},
            {'slug': 'sop-konseling',      'title': 'SOP Konseling',      'icon': 'psychology'},
            {'slug': 'faq',                'title': 'FAQ',                 'icon': 'quiz'},
            {'slug': 'tentang',            'title': 'Tentang Lab',         'icon': 'apartment'},
            {'slug': 'kebijakan-privasi',  'title': 'Kebijakan Privasi',   'icon': 'shield'},
        ],
        'peminjaman_steps': [
            {'title': 'Login ke sistem',         'desc': 'Pastikan akun sudah terverifikasi oleh admin.'},
            {'title': 'Pilih jenis peminjaman',  'desc': 'Ruangan atau Alat Test tersedia di menu Peminjaman.'},
            {'title': 'Isi form & tanggal',      'desc': 'Pilih tanggal, jam, dan kebutuhan yang sesuai.'},
            {'title': 'Tunggu konfirmasi',        'desc': 'Admin akan menyetujui atau menolak dalam 1x24 jam.'},
            {'title': 'Cetak surat peminjaman',  'desc': 'Unduh dokumen dari menu Riwayat & Dokumen.'},
        ],
        'peminjaman_rules': [
            'Peminjaman hanya untuk keperluan akademik dan penelitian.',
            'Alat test wajib dikembalikan dalam kondisi lengkap dan bersih.',
            'Pembatalan minimal H-1 sebelum jadwal peminjaman.',
            'Kerusakan akibat kelalaian menjadi tanggung jawab peminjam.',
            'Satu pengguna hanya bisa memiliki 1 peminjaman aktif pada waktu bersamaan.',
        ],
        'konseling_steps': [
            {'title': 'Ajukan permintaan konseling', 'desc': 'Isi form di menu Konseling dengan keluhan atau topik yang ingin dibahas.'},
            {'title': 'Penjadwalan sesi',            'desc': 'Konselor akan menghubungi untuk konfirmasi waktu sesi.'},
            {'title': 'Pelaksanaan sesi',            'desc': 'Sesi berlangsung 60–90 menit secara tatap muka atau online.'},
            {'title': 'Tindak lanjut',               'desc': 'Konselor memberikan rekomendasi dan jadwal sesi berikutnya bila diperlukan.'},
        ],
        'faqs': [
            {'q': 'Siapa saja yang bisa menggunakan layanan Lab Psikologi?',
             'a': 'Mahasiswa, dosen, dan masyarakat umum dapat menggunakan layanan. Beberapa layanan khusus hanya untuk civitas akademika UMKT.'},
            {'q': 'Apakah peminjaman alat test dikenakan biaya?',
             'a': 'Peminjaman untuk keperluan akademik internal (tugas/skripsi) tidak dikenakan biaya. Untuk keperluan eksternal/penelitian berbayar, silakan hubungi admin.'},
            {'q': 'Berapa lama proses verifikasi akun?',
             'a': 'Verifikasi akun dilakukan dalam 1×24 jam hari kerja setelah dokumen KTM/KTP diunggah.'},
            {'q': 'Bagaimana jika jadwal peminjaman saya bentrok?',
             'a': 'Sistem akan otomatis menolak peminjaman yang bentrok dengan jadwal lain. Pilih waktu lain yang tersedia.'},
            {'q': 'Apakah layanan konseling bersifat rahasia?',
             'a': 'Ya. Seluruh informasi dalam sesi konseling dijaga kerahasiaannya sesuai kode etik psikologi dan tidak dibagikan tanpa persetujuan klien.'},
            {'q': 'Bagaimana cara mendaftar magang di Lab Psikologi?',
             'a': 'Login ke sistem, buka menu Akademik → Internship, pilih mitra, lalu isi form pendaftaran. Fitur ini hanya tersedia untuk mahasiswa.'},
        ],
        'privacy_policies': [
            {'icon': 'data_usage',  'title': 'Data yang Dikumpulkan',
             'desc': 'Kami mengumpulkan nama, email, NIM/NIP, foto profil, dan KTM/KTP hanya untuk keperluan verifikasi identitas dan penggunaan layanan Lab.'},
            {'icon': 'lock',        'title': 'Penggunaan Data',
             'desc': 'Data tidak dijual atau dibagikan kepada pihak ketiga. Data hanya digunakan untuk pengelolaan layanan Lab Psikologi UMKT secara internal.'},
            {'icon': 'security',    'title': 'Keamanan Data',
             'desc': 'Sistem menggunakan enkripsi HTTPS dan password hashing. Akses data dibatasi hanya untuk admin yang berwenang.'},
            {'icon': 'delete_forever', 'title': 'Penghapusan Data',
             'desc': 'Pengguna dapat mengajukan penghapusan akun dengan menghubungi admin. Data akan dihapus dalam 30 hari kerja setelah permintaan diterima.'},
        ],
    }
    return render(request, 'panduan_info.html', context)