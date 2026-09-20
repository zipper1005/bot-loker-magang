import io
import json
import os
import requests
from http.server import BaseHTTPRequestHandler
from PIL import Image
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

client = genai.Client(api_key=GEMINI_API_KEY)

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

                # 1. Balas pesan teks
                if "text" in msg and chat_id:
                    teks_user = msg["text"]
                    prompt = f"""
                    Kamu adalah asisten karir audit, akuntansi, dan perpajakan untuk mahasiswa/fresh graduate.
                    Jawab pertanyaan ini dengan santai, ramah, dan solutif:
                    "{teks_user}"
                    """
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    kirim_balasan(chat_id, response.text)

                # 2. Analisis foto poster loker
                elif "photo" in msg and chat_id:
                    file_id = msg["photo"][-1]["file_id"]
                    res_file = requests.get(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}",
                        timeout=10
                    ).json()
                    
                    file_path = res_file.get("result", {}).get("file_path")
                    if file_path:
                        img_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                        img_bytes = requests.get(img_url, timeout=15).content
                        gambar = Image.open(io.BytesIO(img_bytes))

                        caption = msg.get("caption", "Tolong bedah poster loker ini.")
                        prompt_vision = f"""
                        Analisis poster loker ini dan rangkum:
                        1. Nama KAP / Instansi & Posisi yang dibuka
                        2. Kualifikasi & Syarat utama
                        3. Cara Melamar (Email/Link, Format Subjek, Deadline)
                        Catatan tambahan user: {caption}
                        """
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[prompt_vision, gambar]
                        )
                        kirim_balasan(chat_id, response.text)

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
