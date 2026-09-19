import io
import os
import re
import time
import requests
from PIL import Image
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN", "").strip()
ID_GRUP_WA = "120363414007391391@g.us"
NTFY_TOPIC = "Pengingat-Tugas"

client = genai.Client(api_key=GEMINI_API_KEY)

def ambil_poster_dan_loker():
    """
    Mengambil data flyer/poster lowongan kerja dan data LinkedIn 
    dengan fokus utama KAP dan Kantor Konsultan Pajak (KKP).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    daftar_gambar = []
    daftar_teks = []

    # 1. Saluran publik penyebar poster loker
    sumber_saluran = [
        "https://t.me/s/disnakerja",
        "https://t.me/s/lokernastelegram"
    ]

    for url in sumber_saluran:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                html = resp.text
                img_matches = re.findall(r"background-image:url\('(https://[^\'\)]+)'\)", html)
                for img_url in img_matches:
                    if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', 'cdn4', 'telesco']):
                        daftar_gambar.append(img_url)
                daftar_teks.append(html[:3500])
        except Exception as e:
            print(f"Gagal mengambil dari {url}: {e}")

    # 2. Ambil dari LinkedIn dengan kata kunci fokus KAP & Konsultan Pajak
    try:
        url_linkedin = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {
            "keywords": "Internship KAP Kantor Akuntan Publik Junior Auditor Tax Consultant",
            "location": "Greater Jakarta Area, Indonesia",
            "f_TPR": "r86400",
            "start": 0
        }
        resp_li = requests.get(url_linkedin, params=params, headers=headers, timeout=15)
        if resp_li.status_code == 200:
            html_li = resp_li.text
            job_ids = list(dict.fromkeys(re.findall(r'jobPosting:(\d+)', html_li)))
            for jid in job_ids[:6]:
                daftar_teks.append(f"LinkedIn Job ID: {jid} -> https://www.linkedin.com/jobs/view/{jid}")
    except Exception as e:
        print("Gagal LinkedIn:", e)

    daftar_gambar = list(dict.fromkeys(daftar_gambar))[:4]
    return daftar_gambar, "\n".join(daftar_teks)

def baca_poster_dan_kurasi(daftar_gambar_urls, teks_pendukung):
    prompt_instruksi = f"""
    Kamu adalah asisten karir akuntansi & perpajakan tingkat lanjut dengan kemampuan vision.
    Tugas utamamu: BACA DAN ANALISIS POSTER/FLYER LOWONGAN serta data lowongan yang terlampir.

    PRIORITAS UTAMA & ATURAN FILTERING:
    1. UTAMAKAN lowongan magang / internship dari:
       - Kantor Akuntan Publik (KAP) -> Posisi: Junior Auditor Intern / Audit Assistant / Audit Intern.
       - Kantor Konsultan Pajak (KKP) atau Divisi Tax Consulting -> Posisi: Tax Intern / Tax Consultant Assistant / Tax Compliance Intern.
       - Jika tidak ada KAP/KKP, baru tampilkan lowongan magang internal audit / corporate tax / accounting di perusahaan/BUMN.
    2. WILAYAH: Khusus INDONESIA, diprioritaskan JABODETABEK (Jakarta, Bogor, Depok, Tangerang, Bekasi, atau Remote).
    3. PEMBACAAN POSTER GAMBAR:
       - Baca seluruh teks di gambar flyer/poster (OCR).
       - Ekstrak: Nama KAP/KKP/Perusahaan, Posisi, Kualifikasi utama (IPK/semester/jurusan/software), Kontak pendaftaran (Email kirim CV, subjek email resmi, atau link form pendaftaran), dan Batas Akhir (Deadline).
    4. FORMAT PESAN WHATSAPP:
       📋 *[NAMA POSISI & KAP / KKP / PERUSAHAAN]*
       • *Tipe*: (KAP / Konsultan Pajak / Korporat)
       • *Wilayah*: ...
       • *Kualifikasi Penting*: ...
       • *Cara Lamar / Email CV*: ...
       • *Batas Waktu*: ...
       • *Sumber*: (Poster Flyer / LinkedIn: cantumkan tautan terkait)
    5. Jika belum ada yang cocok pada sesi pengecekan ini, cukup jawab:
       "Belum ada update lowongan magang baru di KAP / Konsultan Pajak untuk wilayah Jabodetabek pada sesi ini."

    Data Teks Tambahan:
    \"\"\"{teks_pendukung[:2500]}\"\"\"
    """

    contents = [prompt_instruksi]

    total_poster = 0
    for img_url in daftar_gambar_urls:
        try:
            res_img = requests.get(img_url, timeout=10)
            if res_img.status_code == 200 and len(res_img.content) > 15000:
                img = Image.open(io.BytesIO(res_img.content))
                contents.append(img)
                total_poster += 1
                print(f"Berhasil memproses poster: {img_url}")
        except Exception as e:
            print(f"Gagal memproses gambar: {e}")

    print(f"Total poster yang dianalisis vision: {total_poster}")

    model_list = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.6-flash"]
    for model_name in model_list:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents
            )
            return response.text
        except Exception as e:
            print(f"Model {model_name} kendala ({e}), mencoba model cadangan...")
            time.sleep(2)

    return "Server AI sedang sibuk sementara. Pengecekan akan diulang otomatis pada jadwal berikutnya."

def main():
    print("Mencari lowongan magang KAP & Konsultan Pajak serta memindai poster...")
    daftar_gambar, teks_pendukung = ambil_poster_dan_loker()
    hasil = baca_poster_dan_kurasi(daftar_gambar, teks_pendukung)

    pesan_wa = f"📢 *UPDATE LOKER MAGANG KAP & KONSULTAN PAJAK (JABODETABEK)*\n\n{hasil}"

    # 1. Kirim ke WhatsApp
    try:
        clean_token = FONNTE_TOKEN.strip()
        res_wa = requests.post(
            "https://api.fonnte.com/send",
            headers={"Authorization": clean_token},
            data={"target": ID_GRUP_WA, "message": pesan_wa},
            timeout=15
        )
        print("Respon Fonnte WA:", res_wa.text)
    except Exception as e:
        print("Error WA:", e)

    # 2. Kirim ke ntfy HP
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=hasil.encode("utf-8"),
            headers={
                "Title": "📢 Update Loker Magang KAP & Pajak".encode("utf-8"),
                "Priority": "default",
                "Tags": "briefcase"
            },
            timeout=15
        )
        print("Terkirim ke ntfy!")
    except Exception as e:
        print("Error ntfy:", e)

if __name__ == "__main__":
    main()
