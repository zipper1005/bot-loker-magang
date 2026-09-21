import os
import json
import urllib.parse
from datetime import datetime, timezone
import email.utils
import xml.etree.ElementTree as ET
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8932857674").strip()
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()

# Target langsung portal kerja dan kata kunci magang audit/pajak 30 hari terakhir
QUERIES = [
    'site:linkedin.com/jobs ("magang" OR "internship") ("audit" OR "tax" OR "KAP") Jakarta when:30d',
    'site:id.jobstreet.com/id/job ("magang" OR "internship") ("audit" OR "tax" OR "pajak") when:30d',
    'site:glints.com/id/opportunities/jobs ("intern" OR "magang") ("audit" OR "pajak" OR "tax") when:30d',
    '"lowongan magang" ("KAP" OR "kantor akuntan publik" OR "konsultan pajak") Jabodetabek when:30d',
    'magang "junior auditor" KAP Jakarta when:30d',
    'internship "tax" konsultan pajak Jakarta when:30d'
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for q in QUERIES:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=id&gl=ID&ceid=ID:id"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200:
                continue

            root = ET.fromstring(res.content)
            for item in root.findall("./channel/item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_elem = item.find("pubDate")

                title = title_elem.text if title_elem is not None else ""
                link = link_elem.text if link_elem is not None else ""
                pub_date = pub_elem.text if pub_elem is not None else ""

                if pub_date and not is_recent(pub_date, max_days=30):
                    continue

                if link and link not in seen_links:
                    seen_links.add(link)
                    hasil.append({
                        "title": title,
                        "link": link,
                        "published": pub_date
                    })
        except Exception as e:
            print(f"Gagal mengambil RSS: {e}")

    return hasil

def kurasi_dengan_gemini(daftar_loker):
    if not daftar_loker:
        return "Tidak ada lowongan magang KAP/Pajak yang terdeteksi dalam 30 hari terakhir."

    data_teks = json.dumps(daftar_loker[:25], indent=2)
    prompt = f"""
    Kamu adalah kurator karir spesialis akuntansi, audit (KAP), dan perpajakan di Indonesia.
    Tugasmu memvalidasi data temuan lowongan kerja/magang berikut:
    {data_teks}

    ATURAN KURASI:
    1. Ambil posisi yang relevan dengan: Magang / Intern / Junior Auditor di KAP, Tax Intern di Konsultan Pajak, atau Staff Akuntansi/Pajak entry-level.
    2. Abaikan berita umum, artikel opini, kursus berbayar, atau postingan yang jelas-jelas bukan lowongan kerja.
    3. Format tiap lowongan yang valid:
       - 📌 **Posisi & Instansi/KAP**: [Nama Posisi] - [Nama Perusahaan/KAP]
       - 📍 **Lokasi**: [Jabodetabek / Kota / WFH]
       - 📝 **Ringkasan Syarat**: [Pendidikan / Kemampuan utama]
       - 🔗 **Link Info/Loker**: [Tautkan link asli dari data]

    Jika dari daftar tersebut tidak ada satupun posisi audit/pajak yang valid, tulis:
    "Belum ada rilis lowongan magang KAP/Pajak baru yang valid pada portal kerja dalam 30 hari terakhir."
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        data = res.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            return f"Kendala API Gemini: {data['error'].get('message', 'Tidak diketahui')}"
        return "Respon kurasi kosong dari server AI."
    except Exception as e:
        return f"Gagal memproses kurasi AI: {str(e)}"

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
    print("Mencari lowongan magang portal kerja 30 hari terakhir...")
    data_mentah = ambil_loker_rss()
    print(f"Ditemukan {len(data_mentah)} postingan baru.")
    
    hasil_kurasi = kurasi_dengan_gemini(data_mentah)
    pesan_akhir = f"📢 UPDATE LOKER AUDIT & PAJAK (PORTAL KERJA 30 HARI TERAKHIR)\n\n{hasil_kurasi}"
    
    kirim_notifikasi(pesan_akhir)
    print("Selesai diproses dan dikirim.")

if __name__ == "__main__":
    main()
