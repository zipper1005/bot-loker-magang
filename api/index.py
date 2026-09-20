import io
import json
import os
import requests
from http.server import BaseHTTPRequestHandler

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

def kirim_balasan(chat_id, teks):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": teks
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Gagal kirim ke Telegram:", e)

def tanya_gemini(prompt_teks):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt_teks}]
        }]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        data = res.json()
        
        if "candidates" in data and len(data["candidates"]) > 0:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        elif "error" in data:
            pesan_err = data["error"].get("message", "Unknown error")
            return f"Kendala API Google: {pesan_err}"
        return "Respon API kosong dari server."
    except Exception as e:
        return f"Error koneksi: {str(e)}"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            if not post_data:
                self.send_response(200)
                self.end_headers()
                return

            update = json.loads(post_data.decode("utf-8"))

            if "message" in update:
                msg = update["message"]
                chat_id = msg.get("chat", {}).get("id")

                if "text" in msg and chat_id:
                    teks_user = msg["text"]
                    
                    if teks_user == "/start":
                        kirim_balasan(chat_id, "Halo! Aku asisten karir audit & perpajakan bertenaga Gemini 3.8 Flash. Mau cari info loker KAP apa hari ini?")
                    else:
                        prompt = f"Kamu adalah asisten karir audit, akuntansi, dan perpajakan untuk mahasiswa/fresh graduate. Jawab dengan ramah, santai, dan solutif: '{teks_user}'"
                        jawaban = tanya_gemini(prompt)
                        kirim_balasan(chat_id, jawaban)

        except Exception as err:
            print("Error webhook:", err)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot Webhook Ready")
