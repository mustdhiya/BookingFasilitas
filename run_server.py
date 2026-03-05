# run_server.py — jalankan ini untuk local testing yang optimal
from waitress import serve
from config.wsgi import application

if __name__ == '__main__':
    print("✅ Server berjalan di http://localhost:8000")
    print("   Threads: 6 | Channel capacity: 100")
    serve(
        application,
        host='0.0.0.0',
        port=8000,
        threads=6,              # handle 6 request bersamaan
        channel_timeout=30,     # timeout 30 detik
        connection_limit=300,   # max 300 koneksi
        cleanup_interval=30,
    )

