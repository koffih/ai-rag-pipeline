import os
import time
import logging
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import mimetypes
import subprocess
import sys
from pdf2image import convert_from_path
import pytesseract

WATCHED_INBOX = os.path.join(os.path.dirname(__file__), '..', 'watched_inbox')
WATCHED_TXT = os.path.join(os.path.dirname(__file__), '..', 'watched_txt')
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'super_pipeline.log')
RAG_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
VECTORIZE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, 'vectorize_books.py')
TOPIC_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, 'topic_generator.py')
ARTICLE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, 'generate_articles_from_supabase.py')

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Assure que le dossier texte existe
os.makedirs(WATCHED_TXT, exist_ok=True)

# Détection du type de fichier
def detect_type(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in ['.pdf', '.txt', '.docx', '.rtf', '.odt', '.html', '.htm']:
        return 'text'
    if ext in ['.epub', '.mobi', '.azw', '.azw3', '.fb2', '.lit', '.pdb']:
        return 'ebook'
    if ext in ['.mp3', '.wav', '.m4a', '.flac']:
        return 'audio'
    return 'unknown'

# Traitement selon le type
def process_file(filepath):
    filename = os.path.basename(filepath)
    filetype = detect_type(filepath)
    logging.info(f"START | {filename} | Type: {filetype}")
    try:
        out_txt = os.path.join(WATCHED_TXT, filename.rsplit('.', 1)[0] + '.txt')
        if filetype == 'text':
            if filename.endswith('.pdf'):
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(filepath)
                docs = loader.load()
                text = '\n'.join([doc.page_content for doc in docs])
                # Ajout OCR si texte vide
                if not text.strip():
                    logging.info(f"OCR | {filename} | PDF sans texte, lancement de l'OCR...")
                    images = convert_from_path(filepath)
                    ocr_text = ""
                    for img in images:
                        ocr_text += pytesseract.image_to_string(img, lang="fra")
                    text = ocr_text
                    logging.info(f"OCR | {filename} | OCR terminé, texte extrait.")
                with open(out_txt, 'w', encoding='utf-8') as f:
                    f.write(text)
                logging.info(f"SUCCESS | {filename} | PDF extrait en TXT (avec OCR si besoin)")
            elif filename.endswith('.txt'):
                shutil.copy(filepath, out_txt)
                logging.info(f"SUCCESS | {filename} | Copié en TXT")
            else:
                # Pour docx, rtf, odt, html, conversion en txt via pandoc si dispo
                try:
                    subprocess.run(['pandoc', filepath, '-t', 'plain', '-o', out_txt], check=True)
                    logging.info(f"SUCCESS | {filename} | Converti en TXT via pandoc")
                except Exception as e:
                    logging.error(f"FAILURE | {filename} | Conversion pandoc: {e}")
        elif filetype == 'ebook':
            # Conversion en PDF via Calibre, puis extraction texte
            pdf_path = os.path.join(WATCHED_TXT, filename.rsplit('.', 1)[0] + '.pdf')
            try:
                subprocess.run(['ebook-convert', filepath, pdf_path], check=True)
                # Extraction texte du PDF
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(pdf_path)
                docs = loader.load()
                text = '\n'.join([doc.page_content for doc in docs])
                with open(out_txt, 'w', encoding='utf-8') as f:
                    f.write(text)
                logging.info(f"SUCCESS | {filename} | eBook converti en PDF puis TXT")
            except Exception as e:
                logging.error(f"FAILURE | {filename} | Conversion eBook: {e}")
        elif filetype == 'audio':
            # Transcription audio via Whisper
            try:
                import whisper
                model = whisper.load_model("base")
                result = model.transcribe(filepath)
                text = result["text"]
                with open(out_txt, 'w', encoding='utf-8') as f:
                    f.write(text)
                logging.info(f"SUCCESS | {filename} | Audio transcrit en TXT")
            except Exception as e:
                logging.error(f"FAILURE | {filename} | Transcription audio: {e}")
        else:
            logging.warning(f"IGNORED | {filename} | Type inconnu")
            return
        # AUTOMATISATION : Vectorisation puis génération d'articles
        try:
            print(f"[AUTOMATION] Vectorisation de {out_txt}")
            subprocess.run([sys.executable, VECTORIZE_SCRIPT, out_txt], check=True)
            print(f"[AUTOMATION] Génération de topics pour {os.path.basename(out_txt)}")
            subprocess.run([sys.executable, TOPIC_SCRIPT, os.path.basename(out_txt)], check=True)
            print(f"[AUTOMATION] Génération d'articles pour {os.path.basename(out_txt)}")
            subprocess.run([sys.executable, ARTICLE_SCRIPT, "5"], check=True)
            logging.info(f"AUTOMATION | {filename} | Vectorisation et génération d'articles OK")
        except Exception as e:
            logging.error(f"AUTOMATION | {filename} | Erreur vectorisation/génération : {e}")
    except Exception as e:
        logging.error(f"FAILURE | {filename} | Error: {e}")

# Surveillance du dossier
class InboxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            process_file(event.src_path)

if __name__ == "__main__":
    print(f"👀 Surveillance du dossier universel : {WATCHED_INBOX}")
    # Traite les fichiers déjà présents
    for f in os.listdir(WATCHED_INBOX):
        full_path = os.path.join(WATCHED_INBOX, f)
        if os.path.isfile(full_path):
            process_file(full_path)
    # Lance la surveillance
    event_handler = InboxHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_INBOX, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join() 