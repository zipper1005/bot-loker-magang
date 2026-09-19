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

def cari_loker_linkedin():
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": "Internship Junior Auditor Tax Accounting",
        "location": "Greater Jakarta Area, Indonesia",
        "f_TPR": "r86400",
        "start": 0
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        html = resp.text
        
        # Ambil link postingan
        pattern_id = r'jobPosting:(\d+)'
        job_ids = list(dict.fromkeys(re.findall(pattern_id, html)))
        
        daftar_loker = []
        for jid in job_ids[:8]:
            link = f"https://www.linkedin.com/jobs/view/{jid}"
            daftar_loker.append(f"- ID: {jid} | Link: {link}")
            
        # Ambil tautan gambar/poster yang ada di hasil pencarian
        pattern_img = r'https://media\.licdn\.com/dms/image/[^"\s]+'
        image_urls = list(dict.fromkeys(re.findall(pattern_img, html)))
        
        return html, "\n".join(daftar_loker), image_urls[:3]
    except Exception as e:
        return "", f"Error scraping: {e}", []

def kurasi_loker(html_mentah, daftar_link, image_urls):
    prompt_teks = f"""
    Kamu adalah asisten karir akuntansi & perpajakan.
    Tugasmu menganalisis info lowongan dan membaca poster loker yang terlampir.

    Daftar Tautan LinkedIn:
    \"\"\"{daftar_link}\"\"\"

    Cuplikan HTML:
    \"\"\"{html_mentah[:4000]}\"\"\"

    ATURAN KURASI:
    1. Saring KHUSUS MAGANG / INTERNSHIP: Junior Auditor (KAP), Tax Intern, Accounting Staff di Indonesia (Jabodetabek).
    2. Jika ada POSTER GAMBAR yang terlampir, baca seluruh tulisan di poster:
       - Nama KAP / Perusahaan
       - Posisi yang dibuka
       - Kualifikasi & Cara melamar (email / nomor WhatsApp / form)
    3. Sajikan daftar rapi:
       *Posisi*: ...
       *Perusahaan / KAP*: ...
       *Lokasi*: ...
       *Kontak / Email Lamaran*: ...
       *Link LinkedIn*: (cantumkan link terkait)
    4. Jika tidak ada loker magang yang cocok pada batch ini, tulis:
       "Belum ada update lowongan magang Audit & Tax baru untuk wilayah Jabodetabek pada sesi ini."
    """

    # Siapkan konten multimodal (teks prompt + gambar poster)
    contents = [prompt_teks]
    for img_url in image_urls:
        try:
            res_img = requests.get(img_url, timeout=10)
            if res_img.status_code == 200:
                img = Image.open(io.BytesIO(res_img.content))
                contents.append(img)
        except Exception:
            continue

    model_list = ["gemini-2.5-flash", "gemini-3.6-flash"]
    for model_name in model_list:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents
            )
            return response.text
        except Exception as e:
            print(f"Model {model_name} kendala: {e}, mencoba model lain...")
            time.sleep(2)
            
    return "Server AI sedang sibuk sementara. Pengecekan akan diulang otomatis pada jadwal berikutnya."

def main():
    print("Mencari lowongan magang dan memindai poster lowongan...")
    html_mentah, daftar_link, image_urls = cari_loker_linkedin()
    hasil = kurasi_loker(html_mentah, daftar_link, image_urls)

    pesan_wa = f"📢 *UPDATE LOKER MAGANG JABODETABEK (AUDIT & TAX)*\n\n{hasil}"
    
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

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=hasil.encode("utf-8"),
            headers={
                "Title": "📢 Loker Magang Audit & Tax".encode("utf-8"),
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
