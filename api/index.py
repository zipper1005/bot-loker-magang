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
    daftar_model = ["gemini-2.5-flash", "gemini-1.5-flash"]
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt_teks}]
        }]
    }

    for model in daftar_model:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            data = res.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            continue

    return "Server AI sedang sibuk sementara. Silakan kirim ulang pesanmu dalam beberapa detik ya!"

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
                        kirim_balasan(chat_id, "Halo! Aku asisten karir audit & perpajakan. Mau tanya tips interview, review CV, atau info lowongan KAP apa hari ini?")
                    else:
                        prompt = f"Kamu asisten karir audit, akuntansi, dan perpajakan untuk mahasiswa/fresh graduate. Jawab ramah, santai, dan to the point: '{teks_user}'"
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
