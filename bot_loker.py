import os
import requests
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN")
ID_GRUP_WA = "120363414007391391@g.us"
NTFY_TOPIC = "Pengingat-Tugas"

client = genai.Client(api_key=GEMINI_API_KEY)

def cari_loker_linkedin():
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": "Junior Auditor Internship Tax",
        "location": "Indonesia",
        "f_TPR": "r86400",
        "start": 0
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        return resp.text
    except Exception as e:
        return f"Gagal mengambil lowongan: {e}"

def kurasi_loker(data_mentah):
    prompt = f"""
    Kamu adalah asisten karir akuntansi & perpajakan. 
    Analisis data mentah lowongan kerja dari LinkedIn berikut:
    \"\"\"{data_mentah[:7000]}\"\"\"

    Tugasmu:
    1. Cari dan saring lowongan magang / internship untuk posisi: Junior Auditor, Tax Intern, Accounting Staff, atau Finance Intern di Indonesia.
    2. Buat daftar rapi berisi:
       - Perusahaan / KAP:
       - Posisi:
       - Lokasi:
       - Link (jika ada):
    3. Jika belum ada yang cocok, tulis singkat: "Belum ada loker magang baru pada sesi ini."
    Format pesan siap baca untuk WhatsApp.
    """
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    return response.text

def main():
    print("Mencari lowongan magang terbaru...")
    mentah = cari_loker_linkedin()
    hasil = kurasi_loker(mentah)

    pesan_wa = f"📢 *UPDATE LOKER MAGANG (AUDIT & TAX)*\n\n{hasil}"

    try:
        requests.post(
            "https://api.fonnte.com/send",
            headers={"Authorization": FONNTE_TOKEN},
            data={"target": ID_GRUP_WA, "message": pesan_wa}
        )
        print("Terkirim ke WhatsApp!")
    except Exception as e:
        print("Error WA:", e)

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data="Loker baru Junior Auditor & Tax sudah dikirim ke WhatsApp!".encode("utf-8"),
            headers={"Title": "Update Loker Magang!".encode("utf-8")}
        )
        print("Terkirim ke ntfy!")
    except Exception as e:
        print("Error ntfy:", e)

if __name__ == "__main__":
    main()
