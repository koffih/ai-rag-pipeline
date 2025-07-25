import os
import time
import whisper
import logging
from datetime import datetime

WATCHED_MP3 = os.path.join(os.path.dirname(__file__), '..', 'watched_mp3')
WATCHED_TXT = os.path.join(os.path.dirname(__file__), '..', 'watched_txt')
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'transcription.log')

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def transcribe_mp3(mp3_path, output_txt_path):
    try:
        model = whisper.load_model("base")
        logging.info(f"START | {os.path.basename(mp3_path)}")
        result = model.transcribe(mp3_path, language="fr")
        text = result["text"]
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        logging.info(f"SUCCESS | {os.path.basename(mp3_path)} | Output: {output_txt_path}")
        print(f"✅ Transcription terminée pour {mp3_path}")
    except Exception as e:
        logging.error(f"FAILURE | {os.path.basename(mp3_path)} | Error: {e}")
        print(f"❌ Erreur lors de la transcription de {mp3_path} : {e}")

def process_existing_mp3():
    files = os.listdir(WATCHED_MP3)
    for filename in files:
        if filename.lower().endswith('.mp3'):
            mp3_path = os.path.join(WATCHED_MP3, filename)
            txt_path = os.path.join(WATCHED_TXT, filename.rsplit('.', 1)[0] + '.txt')
            if not os.path.exists(txt_path):
                transcribe_mp3(mp3_path, txt_path)

if __name__ == "__main__":
    print(f"👀 Surveillance du dossier : {WATCHED_MP3}")
    while True:
        process_existing_mp3()
        time.sleep(10)  # Vérifie toutes les 10 secondes 