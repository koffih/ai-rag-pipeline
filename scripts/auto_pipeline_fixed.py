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

RAG_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
VECTORIZE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "vectorize_books.py")
TOPIC_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "topic_generator.py")
ARTICLE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "generate_articles_from_supabase.py")

SUPPORTED_EXTENSIONS = (".pdf", ".epub", ".mobi", ".azw3", ".txt", ".docx")

def safe_file_move(src, dst):
    """Déplacement sécurisé des fichiers avec gestion d'erreurs"""
    try:
        if os.path.exists(src):
            shutil.move(src, dst)
            return True
        else:
            print(f"⚠️ Fichier source non trouvé: {src}")
            return False
    except Exception as e:
        print(f"❌ Erreur lors du déplacement: {e}")
        return False

def process_pdf(file_path):
    filename = os.path.basename(file_path)
    print(f"\n=== 🚀 Nouveau fichier détecté : {filename} ===")
    
    # Vérifier que le fichier existe avant de commencer
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé: {file_path}")
        return
    
    try:
        # 1. Vectorisation
        print("[1/3] Vectorisation...")
        result = subprocess.run([sys.executable, VECTORIZE_SCRIPT, file_path], 
                              capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"⚠️ Erreur vectorisation: {result.stderr}")

        # 2. Génération des topics
        print("[2/3] Génération des topics...")
        result = subprocess.run([sys.executable, TOPIC_SCRIPT, filename], 
                              capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"⚠️ Erreur génération topics: {result.stderr}")

        # 3. Génération des articles
        print("[3/3] Génération des articles...")
        result = subprocess.run([sys.executable, ARTICLE_SCRIPT, "100"], 
                              capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            print(f"⚠️ Erreur génération articles: {result.stderr}")

        # Déplacement sécurisé du fichier
        dest = os.path.join(DONE_DIRECTORY, filename)
        if safe_file_move(file_path, dest):
            print(f"✅ Pipeline terminé pour {filename}. Fichier déplacé dans : {dest}\n")
        else:
            print(f"⚠️ Pipeline terminé mais fichier non déplacé: {filename}\n")
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ Timeout pour {filename}")
        dest = os.path.join(DONE_DIRECTORY, filename)
        safe_file_move(file_path, dest)
    except Exception as e:
        print(f"❌ Erreur dans le pipeline pour {filename} : {e}")
        dest = os.path.join(DONE_DIRECTORY, filename)
        safe_file_move(file_path, dest)

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            # Attendre un peu pour s'assurer que le fichier est complètement écrit
            time.sleep(2)
            if os.path.exists(event.src_path):
                process_pdf(event.src_path)

def process_existing_pdfs(only_one=False):
    print("🔁 Vérification des fichiers déjà présents...")
    if not os.path.exists(WATCH_DIRECTORY):
        print(f"❌ Répertoire de surveillance non trouvé: {WATCH_DIRECTORY}")
        return
    
    files = os.listdir(WATCH_DIRECTORY)
    processed = 0
    
    for filename in files:
        if filename == "done":  # Ignorer le répertoire done
            continue
            
        full_path = os.path.join(WATCH_DIRECTORY, filename)
        if os.path.isfile(full_path) and filename.lower().endswith(SUPPORTED_EXTENSIONS):
            process_pdf(full_path)
            processed += 1
            if only_one:
                break
    
    print(f"📊 {processed} fichiers traités")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--one', '--single', action='store_true', help='Traiter un seul fichier et arrêter')
    parser.add_argument('--test', action='store_true', help='Mode test avec timeout réduit')
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
