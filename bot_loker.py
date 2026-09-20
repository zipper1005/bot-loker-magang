import io
import os
import re
import time
import urllib.parse
import requests
from PIL import Image
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN", "").strip()
ID_GRUP_WA = "120363414007391391@g.us"
NTFY_TOPIC = "Pengingat-Tugas"

client = genai.Client(api_key=GEMINI_API_KEY)

def ambil_loker_feed_dan_jobs():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    daftar_teks = []
    daftar_gambar = []

    # 1. Menjaring postingan feed LinkedIn publik (seperti Magang Info, HRD, KAP) lewat Google News/RSS
    query = 'site:linkedin.com/posts ("internship" OR "magang") ("junior auditor" OR "tax" OR "accounting") ("KAP" OR "bdo" OR "pwc" OR "ey" OR "deloitte" OR "kpmg")'
    url_rss = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=id&gl=ID&ceid=ID:id"
    
    try:
        res_rss = requests.get(url_rss, headers=headers, timeout=12)
        if res_rss.status_code == 200:
            titles = re.findall(r"<title>(.*?)</title>", res_rss.text)
            links = re.findall(r"<link>(.*?)</link>", res_rss.text)
            for t, l in zip(titles[1:8], links[1:8]):
                daftar_teks.append(f"Postingan LinkedIn: {t}\nTautan: {l}")
    except Exception as e:
        print("Gagal RSS LinkedIn:", e)

    # 2. LinkedIn Guest Jobs resmi
    try:
        url_linkedin = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {
            "keywords": "Internship KAP Kantor Akuntan Publik Junior Auditor Tax Consultant",
            "location": "Greater Jakarta Area, Indonesia",
            "f_TPR": "r86400",
            "start": 0
        }
        resp_li = requests.get(url_linkedin, params=params, headers=headers, timeout=12)
        if resp_li.status_code == 200:
            job_ids = list(dict.fromkeys(re.findall(r'jobPosting:(\d+)', resp_li.text)))
            for jid in job_ids[:5]:
                daftar_teks.append(f"Tiket Jobs: https://www.linkedin.com/jobs/view/{jid}")
    except Exception as e:
        print("Gagal Jobs API:", e)

    # 3. Saluran publik flyer/poster loker
    sumber_saluran = ["https://t.me/s/disnakerja", "https://t.me/s/lokernastelegram"]
    for url in sumber_saluran:
        try:
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code == 200:
                img_matches = re.findall(r"background-image:url\('(https://[^\'\)]+)'\)", resp.text)
                for img_url in img_matches:
                    if any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', 'cdn4', 'telesco']):
                        daftar_gambar.append(img_url)
                daftar_teks.append(resp.text[:3000])
        except Exception:
            pass

    daftar_gambar = list(dict.fromkeys(daftar_gambar))[:3]
    return daftar_gambar, "\n".join(daftar_teks)

def baca_dan_kurasi(daftar_gambar_urls, teks_pendukung):
    prompt_instruksi = f"""
    Kamu adalah asisten karir akuntansi & perpajakan dengan kemampuan vision.
    Tugasmu menganalisis postingan feed, tiket lowongan, dan poster yang terlampir.

    PRIORITAS UTAMA:
    1. Lowongan MAGANG / INTERNSHIP di:
       - Kantor Akuntan Publik (KAP): Junior Auditor, Audit Intern, Accounting Intern (misal: BDO, Big 4, KAP lokal).
       - Kantor Konsultan Pajak (KKP) atau Divisi Tax: Tax Intern, Tax Compliance.
       - Corporate Finance/Accounting Intern di perusahaan Jabodetabek.
    2. Ekstrak data krusial:
       - Nama KAP / Instansi
       - Posisi
       - Syarat/Kualifikasi (semester/jurusan)
       - Email pengiriman berkas & format subjek email
       - Tautan postingan
    3. FORMAT PESAN WHATSAPP:
       📋 *[NAMA POSISI & KAP / PERUSAHAAN]*
       • *Tipe*: (KAP / Konsultan Pajak / Korporat)
       • *Kualifikasi*: ...
       • *Cara Lamar / Email*: ...
       • *Sumber / Link*: ...
    4. Jika data kosong pada sesi ini, balas singkat:
       "Belum ada update lowongan magang baru di KAP / Konsultan Pajak untuk wilayah Jabodetabek pada sesi ini."

    Data Teks Masuk:
    \"\"\"{teks_pendukung[:4000]}\"\"\"
    """

    contents = [prompt_instruksi]

    for img_url in daftar_gambar_urls:
        try:
            res_img = requests.get(img_url, timeout=10)
            if res_img.status_code == 200 and len(res_img.content) > 15000:
                contents.append(Image.open(io.BytesIO(res_img.content)))
        except Exception:
            pass

    model_list = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
    for model_name in model_list:
        try:
            response = client.models.generate_content(model=model_name, contents=contents)
            if response.text:
                return response.text
        except Exception:
            time.sleep(2)

    return "Belum ada update lowongan magang baru di KAP / Konsultan Pajak untuk wilayah Jabodetabek pada sesi ini."

def main():
    print("Mencari postingan feed dan portal lowongan...")
    daftar_gambar, teks_pendukung = ambil_loker_feed_dan_jobs()
    hasil = baca_dan_kurasi(daftar_gambar, teks_pendukung)

    pesan_wa = f"📢 *UPDATE LOKER MAGANG KAP & PAJAK (FEED & PORTAL)*\n\n{hasil}"

    try:
        requests.post(
            "https://api.fonnte.com/send",
            headers={"Authorization": FONNTE_TOKEN.strip()},
            data={"target": ID_GRUP_WA, "message": pesan_wa},
            timeout=15
        )
    except Exception as e:
        print("Error WA:", e)

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=hasil.encode("utf-8"),
            headers={"Title": "Update Loker Magang KAP & Pajak".encode("utf-8")},
            timeout=15
        )
    except Exception as e:
        print("Error ntfy:", e)

if __name__ == "__main__":
    main()
