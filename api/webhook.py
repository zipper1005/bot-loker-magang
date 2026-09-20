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
    payload = {"chat_id": chat_id, "text": teks}
    requests.post(url, json=payload, timeout=10)

def handler(request):
    pass

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        
        try:
            update = json.loads(body)
            if "message" not in update:
                self.send_response(200)
                self.end_headers()
                return

            msg = update["message"]
            chat_id = msg["chat"]["id"]
            
            # Kasus 1: Pengguna mengirim pesan teks / tanya lowongan
            if "text" in msg:
                user_text = msg["text"]
                prompt = f"""
                Kamu adalah asisten karir audit, akuntansi, dan perpajakan untuk mahasiswa/fresh graduate.
                Jawab pertanyaan pengguna dengan ramah, lugas, dan praktis:
                "{user_text}"
                """
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt]
                )
                kirim_balasan(chat_id, response.text)

            # Kasus 2: Pengguna mengirim gambar flyer / poster loker
            elif "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]
                file_info = requests.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
                ).json()
                file_path = file_info["result"]["file_path"]
                img_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                
                img_data = requests.get(img_url).content
                image = Image.open(io.BytesIO(img_data))

                caption = msg.get("caption", "Ekstrak informasi penting dari poster ini.")
                prompt_vision = f"""
                Analisis poster loker ini dan rangkum:
                1. Posisi & Perusahaan/KAP
                2. Kualifikasi penting (jurusan, semester, keahlian)
                3. Cara melamar (email, deadline, subjek email)
                Instruksi tambahan pengguna: {caption}
                """
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt_vision, image]
                )
                kirim_balasan(chat_id, response.text)

        except Exception as e:
            print("Error handling webhook:", e)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
