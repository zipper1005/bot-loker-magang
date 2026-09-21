import os
import json
import urllib.parse
from datetime import datetime, timezone
import email.utils
import feedparser
import requests
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8932857674").strip()
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()

client = genai.Client(api_key=GEMINI_API_KEY)

QUERIES = [
    '"internship" "junior auditor" KAP Jabodetabek when:30d',
    '"tax intern" konsultan pajak Jakarta when:30d',
    '"magang audit" KAP Jakarta Bogor when:30d',
    '"intern" "auditor" KAP when:30d'
]

def is_recent(published_str, max_days=30):
    try:
        parsed_tuple = email.utils.parsedate_to_datetime(published_str)
        now = datetime.now(timezone.utc)
        if (now - parsed_tuple).days <= max_days:
            return True
        return False
    except Exception:
        return True

def ambil_loker_rss():
    hasil = []
    seen_links = set()

    for q in QUERIES:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=id&gl=ID&ceid=ID:id"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            link = getattr(entry, "link", "")
            title = getattr(entry, "title", "")
            pub_date = getattr(entry, "published", "")

            if pub_date and not is_recent(pub_date, max_days=30):
                continue

            if link and link not in seen_links:
                seen_links.add(link)
                hasil.append({
                    "title": title,
                    "link": link,
                    "published": pub_date
                })
    return hasil

def kurasi_dengan_gemini(daftar_loker):
    if not daftar_loker:
        return "Tidak ada lowongan magang KAP/Pajak yang valid dalam 30 hari terakhir."

    data_teks = json.dumps(daftar_loker[:15], indent=2)
    prompt = f"""
    Kamu adalah kurator karir spesialis akuntansi, audit (KAP), dan perpajakan.
    Tugasmu memvalidasi data lowongan berikut:
    {data_teks}

    ATURAN KETAT:
    1. HANYA ambil lowongan yang AKTIF dan dirilis maksimal 30 hari terakhir.
    2. ABAIKAN berita umum, artikel opini, loker kedaluwarsa, atau postingan tahun lalu.
    3. Format tiap lowongan yang lolos kurasi:
       - Posisi & KAP / Perusahaan
       - Lokasi (Jabodetabek diutamakan)
       - Ringkasan Syarat
       - Link Lamaran

    Jika tidak ada yang sesuai kriteria magang audit/pajak 30 hari terakhir, tulis persis:
    "Tidak ada lowongan magang KAP/Pajak yang valid dalam 30 hari terakhir."
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def kirim_notifikasi(pesan):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url_tele = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": pesan}
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
    print("Mencari lowongan magang 30 hari terakhir...")
    data_mentah = ambil_loker_rss()
    print(f"Ditemukan {len(data_mentah)} data berumur <= 30 hari.")
    
    hasil_kurasi = kurasi_dengan_gemini(data_mentah)
    pesan_akhir = f"📌 UPDATE LOKER AUDIT & PAJAK (MAKS. 30 HARI TERAKHIR)\n\n{hasil_kurasi}"
    
    kirim_notifikasi(pesan_akhir)
    print("Selesai dikirim.")

if __name__ == "__main__":
    main()
