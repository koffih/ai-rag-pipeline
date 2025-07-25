import os
import time
import shutil
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import argparse

WATCH_DIRECTORY = "/home/koffi/rag_project/watched_inbox"
DONE_DIRECTORY = os.path.join(WATCH_DIRECTORY, "done")
os.makedirs(DONE_DIRECTORY, exist_ok=True)

# Utilitaires pour chaque étape
RAG_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Vectorisation
VECTORIZE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "vectorize_books.py")
# 2. Génération de topics
TOPIC_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "topic_generator.py")
# 3. Génération d'articles
ARTICLE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "generate_articles_from_supabase.py")

# Extensions de fichiers à vectoriser
SUPPORTED_EXTENSIONS = (".pdf", ".epub", ".mobi", ".azw3")

def process_pdf(file_path):
    filename = os.path.basename(file_path)
    print(f"\n=== 🚀 Nouveau fichier détecté : {filename} ===")
    try:
        # 1. Vectorisation
        print("[1/3] Vectorisation...")
        subprocess.run([sys.executable, VECTORIZE_SCRIPT, file_path], check=True)

        # 2. Génération des topics
        print("[2/3] Génération des topics...")
        subprocess.run([sys.executable, TOPIC_SCRIPT, filename], check=True)

        # 3. Génération des articles
        print("[3/3] Génération des articles...")
        subprocess.run([sys.executable, ARTICLE_SCRIPT, "1000"], check=True)  # Limite à 1000 articles, modifiable

        # Déplacement du fichier dans 'done/'
        dest = os.path.join(DONE_DIRECTORY, filename)
        shutil.move(file_path, dest)
        print(f"✅ Pipeline terminé pour {filename}. Fichier déplacé dans : {dest}\n")
    except Exception as e:
        print(f"❌ Erreur dans le pipeline pour {filename} : {e}")
        # Déplacer le fichier dans 'done/' même en cas d'échec, pour ne pas bloquer le pipeline
        dest = os.path.join(DONE_DIRECTORY, filename)
        shutil.move(file_path, dest)
        print(f"⚠️ Fichier ignoré/déplacé suite à une erreur : {dest}\n")


class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            process_pdf(event.src_path)


def process_existing_pdfs(only_one=False):
    print("🔁 Vérification des fichiers déjà présents...")
    files = os.listdir(WATCH_DIRECTORY)
    processed = 0
    for filename in files:
        full_path = os.path.join(WATCH_DIRECTORY, filename)
        if os.path.isfile(full_path):
            process_pdf(full_path)
            processed += 1
            if only_one:
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--one', '--single', action='store_true', help='Traiter un seul fichier et arrêter')
    args = parser.parse_args()

    print(f"👀 Surveillance du dossier : {WATCH_DIRECTORY}")
    process_existing_pdfs(only_one=args.one)

    if not args.one:
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
