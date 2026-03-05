# locustfile.py — versi final dengan URL yang benar
from locust import HttpUser, task, between
import re

class PsylabUser(HttpUser):
    host = "https://psylab-umkt.my.id/"   # ← local dulu, bukan production
    wait_time = between(1, 3)

    def on_start(self):
        # Ambil CSRF token
        res = self.client.get("/login/")
        match = re.search(r'csrfmiddlewaretoken" value="(.+?)"', res.text)
        token = match.group(1) if match else ""

        self.client.post("/login/", data={
            "username": "psikologi21@gmail.com",
            "password": "Umkt21Psikologi",
            "csrfmiddlewaretoken": token,
        }, headers={"Referer": "https://psylab-umkt.my.id/login/"})

    @task(3)
    def dashboard(self):
        self.client.get("/dashboard/")

    @task(2)
    def peminjaman(self):
        self.client.get("/peminjaman/")

    @task(1)
    def penelitian(self):
        self.client.get("/penelitian/")

    @task(1)
    def praktikum(self):
        self.client.get("/praktikum/")
