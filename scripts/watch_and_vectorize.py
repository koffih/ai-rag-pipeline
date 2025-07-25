import shutil
import time
import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from vectorize_books import vectorize_pdf
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

WATCH_DIRECTORY = "/home/koffi/rag_project/watched_inbox"
DONE_DIRECTORY = os.path.join(WATCH_DIRECTORY, "done")
os.makedirs(DONE_DIRECTORY, exist_ok=True)

def process_pdf(file_path):
    try:
        print(f"📄 Vectorisation de : {file_path}")
        vectorize_pdf(file_path)
        print("✅ Vectorisation terminée.")

        dest = os.path.join(DONE_DIRECTORY, os.path.basename(file_path))
        shutil.move(file_path, dest)
        print(f"📦 Fichier déplacé vers : {dest}")

    except Exception as e:
        print(f"❌ Erreur pendant la vectorisation : {e}")

# 🔁 1. Traitement des fichiers déjà présents
def process_existing_pdfs():
    print("🔁 Vérification des fichiers déjà présents...")
    files = os.listdir(WATCH_DIRECTORY)
    print(f"[DEBUG] Fichiers détectés dans {WATCH_DIRECTORY} : {files}")
    for filename in files:
        print(f"[DEBUG] Analyse du fichier : {filename}")
        if filename.endswith(".pdf"):
            full_path = os.path.join(WATCH_DIRECTORY, filename)
            if os.path.isfile(full_path):
                print(f"[DEBUG] Fichier PDF détecté et prêt à être traité : {full_path}")
                process_pdf(full_path)

# 🧭 2. Surveillance des nouveaux fichiers
class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".pdf"):
            process_pdf(event.src_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", "-o", action="store_true", help="Traiter les PDF présents puis quitter.")
    args = parser.parse_args()

    print(f"👀 Surveillance du dossier : {WATCH_DIRECTORY}")
    process_existing_pdfs()

    if not args.once:
        event_handler = PDFHandler()
        observer = Observer()
        observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
