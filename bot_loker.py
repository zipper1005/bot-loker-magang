import os
import re
import time
import requests
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
        
        pattern = r'jobPosting:(\d+)'
        job_ids = list(dict.fromkeys(re.findall(pattern, html)))
        
        daftar_loker = []
        for jid in job_ids[:10]:
            link = f"https://www.linkedin.com/jobs/view/{jid}"
            daftar_loker.append(f"- ID: {jid} | Link: {link}")
            
        return html, "\n".join(daftar_loker)
    except Exception as e:
        return "", f"Error scraping: {e}"

def kurasi_loker(html_mentah, daftar_link):
    prompt = f"""
    Kamu adalah asisten karir akuntansi & perpajakan.
    Berikut adalah cuplikan data lowongan dari LinkedIn:
    \"\"\"{html_mentah[:6000]}\"\"\"

    Daftar Tautan Resmi LinkedIn yang diekstrak:
    \"\"\"{daftar_link}\"\"\"

    Tugasmu:
    1. Saring lowongan khusus MAGANG/INTERN: Junior Auditor, Tax Intern, Accounting Staff di Indonesia (khususnya Jabodetabek).
    2. Cocokkan posisi dan perusahaan dengan tautan LinkedIn di atas.
    3. Sajikan daftar rapi siap kirim ke WhatsApp:
       *Posisi*: ...
       *Perusahaan / KAP*: ...
       *Lokasi*: ...
       *Link Lamaran*: (wajib sertakan link https://www.linkedin.com/jobs/view/... yang sesuai)
    4. Jika belum ada loker yang cocok pada batch 24 jam ini, tulis:
       "Belum ada update lowongan magang Audit & Tax baru untuk wilayah Jabodetabek pada sesi ini."
    """

    model_list = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-3.6-flash"]
    for model_name in model_list:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Model {model_name} kendala: {e}, mencoba model cadangan...")
            time.sleep(2)
            
    return "Server AI sedang sibuk sementara. Pengecekan akan diulang otomatis pada jadwal berikutnya."

def main():
    print("Mencari lowongan magang terbaru...")
    html_mentah, daftar_link = cari_loker_linkedin()
    hasil = kurasi_loker(html_mentah, daftar_link)

    pesan_wa = f"📢 *UPDATE LOKER MAGANG JABODETABEK (AUDIT & TAX)*\n\n{hasil}"
    
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
