import re, os

with open('research/views.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Cek class mana yang di-map ke URL delete
print("=== Semua class Delete/Deactivate di views.py ===")
for i, line in enumerate(src.split('\n'), 1):
    if 'class Dosen' in line or 'class Lecturer' in line:
        print(f"  baris {i}: {line.strip()}")

print()
print("=== Baris yang mengandung super().post ===")
for i, line in enumerate(src.split('\n'), 1):
    if 'super().post' in line:
        print(f"  baris {i}: {line.strip()}")

print()
print("=== URL delete di research/urls.py ===")
for root, dirs, files in os.walk('research'):
    for fname in files:
        if fname == 'urls.py':
            path = os.path.join(root, fname)
            with open(path, 'r', encoding='utf-8') as f:
                urls = f.read()
            for i, line in enumerate(urls.split('\n'), 1):
                if 'delete' in line.lower() or 'deactivate' in line.lower() or 'dosen' in line.lower():
                    print(f"  [{path}] baris {i}: {line.strip()}")
