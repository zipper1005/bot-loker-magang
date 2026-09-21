import os
import requests
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8932857674").strip()
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()

client = genai.Client(api_key=GEMINI_API_KEY)

def cari_dan_kurasi_loker():
    prompt = """
    Lakukan pencarian Google langsung di portal lowongan kerja (LinkedIn, Jobstreet, Glints, Kalibrr, dan website resmi KAP/konsultan pajak).
    
    Kriteria:
    1. Posisi: Magang / Internship / Junior Auditor di KAP, atau Tax Intern di Konsultan Pajak.
    2. Wilayah: Jabodetabek (Jakarta, Bogor, Depok, Tangerang, Bekasi).
    3. Rentang Waktu: HANYA yang aktif dan dipublikasikan maksimal 30 hari terakhir.
    
    Format tiap lowongan yang ditemukan:
    📌 Posisi & KAP / Perusahaan: [Nama Posisi] - [Nama Perusahaan]
    📍 Lokasi: [Kota / WFH / WFO]
    📝 Ringkasan Syarat: [Kualifikasi singkat]
    🔗 Link Lamaran: [Tautan lowongan asli]

    Jika tidak ada satupun yang sesuai kriteria 30 hari terakhir, tulis persis:
    "Belum ditemukan lowongan magang KAP/Pajak yang valid dalam 30 hari terakhir."
    """

    tools = [{'type': 'google_search'}]
    generation_config = {
        'temperature': 0.7,
        'max_output_tokens': 4096,
        'thinking_level': 'high'
    }

    try:
        interaction = client.interactions.create(
            model='models/gemini-3-flash-preview',
            input=prompt,
            tools=tools,
            generation_config=generation_config
        )
        return interaction.steps[-1].content
    except Exception as e:
        return f"Terjadi kendala saat memproses dengan Gemini 3: {e}"

def kirim_notifikasi(pesan):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url_tele = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": pesan,
            "disable_web_page_preview": True
        }
        try:
            requests.post(url_tele, json=payload, timeout=15)
        except Exception as e:
            print("Gagal kirim Telegram:", e)

    if NTFY_TOPIC:
        try:
            requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=pesan.encode("utf-8"), timeout=15)
        except Exception as e:
            print("Gagal kirim ntfy:", e)

def main():
    print("Menjalankan pencarian live search loker dengan Gemini 3 Flash...")
    hasil = cari_dan_kurasi_loker()
    pesan_akhir = f"📢 UPDATE LOKER AUDIT & PAJAK (LIVE GOOGLE SEARCH - 30 HARI TERAKHIR)\n\n{hasil}"
    kirim_notifikasi(pesan_akhir)
    print("Selesai dikirim.")

if __name__ == "__main__":
    main()
