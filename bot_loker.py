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
    Mengambil data dari saluran publik penyebar flyer/poster lowongan kerja
    serta portal LinkedIn.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    daftar_gambar = []
    daftar_teks = []

    # 1. Scraping channel penyebar poster gambar loker
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
                daftar_teks.append(html[:3000])
        except Exception as e:
            print(f"Gagal mengambil dari {url}: {e}")

    # 2. Ambil dari LinkedIn
    try:
        url_linkedin = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {
            "keywords": "Internship Junior Auditor Tax Accounting",
            "location": "Greater Jakarta Area, Indonesia",
            "f_TPR": "r86400",
            "start": 0
        }
        resp_li = requests.get(url_linkedin, params=params, headers=headers, timeout=15)
        if resp_li.status_code == 200:
            html_li = resp_li.text
            job_ids = list(dict.fromkeys(re.findall(r'jobPosting:(\d+)', html_li)))
            for jid in job_ids[:5]:
                daftar_teks.append(f"LinkedIn Job ID: {jid} -> https://www.linkedin.com/jobs/view/{jid}")
    except Exception as e:
        print("Gagal LinkedIn:", e)

    daftar_gambar = list(dict.fromkeys(daftar_gambar))[:4]
    return daftar_gambar, "\n".join(daftar_teks)

def baca_poster_dan_kurasi(daftar_gambar_urls, teks_pendukung):
    prompt_instruksi = f"""
    Kamu adalah asisten karir akuntansi & perpajakan tingkat lanjut dengan kemampuan vision.
    Tugas utamamu: BACA TULISAN DI DALAM GAMBAR POSTER / FLYER LOWONGAN yang terlampir di bawah ini!

    ATURAN KURASI KETAT:
    1. Periksa setiap gambar flyer/poster lowongan yang diberikan. Baca semua teks yang tertera di poster (OCR):
       - Posisi yang dibuka (fokus utama: Magang / Internship Junior Auditor, Tax Intern, Accounting Staff di Jabodetabek / Indonesia)
       - Nama Kantor Akuntan Publik (KAP) atau Perusahaan
       - Kualifikasi penting (Jurusan, IPK, syarat keahlian)
       - Kontak Pendaftaran (Email kirim CV, subjek email, atau form link pendaftaran di poster)
       - Batas Akhir / Deadline pendaftaran jika tertulis di poster
    2. Jika poster bukan tentang audit/pajak/akuntansi, lewati poster tersebut.
    3. Sajikan format pesan rapi siap baca di WhatsApp:
       📋 *[NAMA POSISI & PERUSAHAAN/KAP]*
       • *Wilayah*: ...
       • *Kualifikasi Penting*: ...
       • *Cara Lamar / Email*: ...
       • *Batas Waktu*: ...
       • *Sumber*: (Berdasarkan poster / tautan LinkedIn)
    4. Jika pada sesi ini belum ada poster atau loker magang audit/tax baru, tulis:
       "Belum ada update poster atau loker magang Audit & Tax baru untuk wilayah Jabodetabek pada sesi ini."

    Data Teks Tambahan:
    \"\"\"{teks_pendukung[:2500]}\"\"\"
    """

    contents = [prompt_instruksi]

    # Unduh gambar poster dan masukkan ke Gemini Vision
    total_poster = 0
    for img_url in daftar_gambar_urls:
        try:
            res_img = requests.get(img_url, timeout=10)
            if res_img.status_code == 200 and len(res_img.content) > 15000:
                img = Image.open(io.BytesIO(res_img.content))
                contents.append(img)
                total_poster += 1
                print(f"Berhasil mengunduh poster: {img_url}")
        except Exception as e:
            print(f"Gagal memproses gambar: {e}")

    print(f"Total poster yang dikirim ke AI: {total_poster} gambar")

    # Menggunakan Gemini 3.8 Flash sebagai pilihan utama dan 3.5 Flash sebagai cadangan
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
    print("Mencari info lowongan dan memindai poster flyer...")
    daftar_gambar, teks_pendukung = ambil_poster_dan_loker()
    hasil = baca_poster_dan_kurasi(daftar_gambar, teks_pendukung)

    pesan_wa = f"📢 *UPDATE LOKER & HASIL BACA POSTER (AUDIT & TAX)*\n\n{hasil}"

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
                "Title": "📢 Update Hasil Baca Poster Loker".encode("utf-8"),
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
