import os
import time
import requests
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN")
ID_GRUP_WA = "120363414007391391@g.us"
NTFY_TOPIC = "Pengingat-Tugas"

client = genai.Client(api_key=GEMINI_API_KEY)

def cari_loker_linkedin():
    # Khusus mencari kata kunci magang audit & tax di wilayah Jabodetabek / Jakarta
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": "Internship Junior Auditor Tax Accounting",
        "location": "Greater Jakarta Area, Indonesia",
        "f_TPR": "r86400",  # Lowongan 24 jam terakhir
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
    Kamu adalah asisten karir mahasiswa akuntansi. 
    Analisis data mentah lowongan kerja dari LinkedIn berikut:
    \"\"\"{data_mentah[:7000]}\"\"\"

    ATURAN KETAT:
    1. HANYA ambil lowongan kerja di wilayah INDONESIA, diutamakan area JABODETABEK (Jakarta, Bogor, Depok, Tangerang, Bekasi, atau Remote Indonesia).
    2. Posisi KHUSUS MAGANG / INTERNSHIP:
       - Junior Auditor / Audit Intern (KAP / Perusahaan)
       - Tax Intern / Pajak
       - Accounting / Finance Intern
    3. Buat daftar rapi dan to the point:
       - *Perusahaan / KAP*:
       - *Posisi*:
       - *Lokasi*:
       - *Link Lamaran*: (ambil link linkedin atau url yang tertera)
    4. Jika dalam 24 jam terakhir belum ada loker yang cocok di area Jabodetabek/Indonesia, jawab singkat:
       "Belum ada update lowongan magang Audit/Tax baru untuk wilayah Jabodetabek pada sesi ini."

    Format pesan rapi menggunakan format WhatsApp (pakai asterisk *tebal*).
    """
    
    # Otomatis fallback jika ada model yang sedang padat/503
    model_list = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-3.6-flash"]
    for model_name in model_list:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Model {model_name} sibuk, mencoba model lain...")
            time.sleep(2)
            
    return "Server AI sedang padat sementara. Bot akan mengecek kembali pada jadwal berikutnya."

def main():
    print("Mencari lowongan magang Audit & Tax (Jabodetabek / Indonesia)...")
    mentah = cari_loker_linkedin()
    hasil = kurasi_loker(mentah)

    pesan_wa = f"📢 *UPDATE LOKER MAGANG JABODETABEK (AUDIT & TAX)*\n\n{hasil}"
    
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
            data="Loker baru Jabodetabek (Audit & Tax) sudah dicek!".encode("utf-8"),
            headers={"Title": "Update Loker Magang Jabodetabek!".encode("utf-8")}
        )
        print("Terkirim ke ntfy!")
    except Exception as e:
        print("Error ntfy:", e)

if __name__ == "__main__":
    main()
