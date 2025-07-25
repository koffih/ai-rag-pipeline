import os
import shutil
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCHED_DIR = "/home/koffi/watched_sources"
OUTPUT_DIR = "/home/koffi/watched_inbox"

# 📚 Extensions eBook convertibles automatiquement avec Calibre
CONVERTIBLE_EXTENSIONS = [
    ".azw", ".azw3", ".mobi", ".kf8", ".prc",
    ".epub", ".fb2", ".lit", ".pdb",
    ".rtf", ".doc", ".docx", ".html", ".htm", ".odt"
]

def convert_to_pdf(file_path):
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    ext = ext.lower()

    pdf_output_path = os.path.join(OUTPUT_DIR, f"OCR_{name}.pdf")

    try:
        if ext == ".pdf":
            print(f"📄 PDF direct : {filename}")
            shutil.copy(file_path, os.path.join(OUTPUT_DIR, filename))
            os.remove(file_path)
            print(f"🧹 Fichier source supprimé : {file_path}")

        elif ext == ".txt":
            print(f"📝 Conversion TXT → PDF : {filename}")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", size=12)
            for line in content.splitlines():
                pdf.cell(200, 10, txt=line[:90], ln=1)
            pdf.output(pdf_output_path)
            print(f"✅ Fichier TXT converti : {pdf_output_path}")
            os.remove(file_path)
            print(f"🧹 Fichier source supprimé : {file_path}")

        elif ext in CONVERTIBLE_EXTENSIONS:
            print(f"🔁 Conversion Calibre : {filename}")
            subprocess.run(["ebook-convert", file_path, pdf_output_path], check=True)
            print(f"✅ Fichier converti avec Calibre : {pdf_output_path}")
            os.remove(file_path)
            print(f"🧹 Fichier source supprimé : {file_path}")

        else:
            print(f"⚠️ Format non supporté : {filename}")

    except Exception as e:
        print(f"❌ Erreur pour {filename} : {e}")

def process_existing_files():
    print("🔁 Traitement des fichiers existants...")
    for filename in os.listdir(WATCHED_DIR):
        full_path = os.path.join(WATCHED_DIR, filename)
        if os.path.isfile(full_path):
            convert_to_pdf(full_path)

class SourceHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            time.sleep(1)
            convert_to_pdf(event.src_path)

if __name__ == "__main__":
    print(f"👀 Surveillance de : {WATCHED_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    process_existing_files()

    event_handler = SourceHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
