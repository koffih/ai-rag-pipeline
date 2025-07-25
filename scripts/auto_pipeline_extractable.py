import os
import time
import shutil
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import argparse

WATCH_DIRECTORY = "/home/koffi/rag_project/extractable_files"
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

def count_remaining_files():
    """Compter les fichiers restants à traiter"""
    if not os.path.exists(WATCH_DIRECTORY):
        return 0, 0
    
    total_files = 0
    done_files = 0
    
    # Compter tous les fichiers dans le répertoire principal
    for filename in os.listdir(WATCH_DIRECTORY):
        if filename == "done":
            continue
        full_path = os.path.join(WATCH_DIRECTORY, filename)
        if os.path.isfile(full_path) and filename.lower().endswith(SUPPORTED_EXTENSIONS):
            total_files += 1
    
    # Compter les fichiers terminés
    done_dir = os.path.join(WATCH_DIRECTORY, "done")
    if os.path.exists(done_dir):
        for filename in os.listdir(done_dir):
            full_path = os.path.join(done_dir, filename)
            if os.path.isfile(full_path):
                done_files += 1
    
    return total_files, done_files

def process_pdf(file_path):
    filename = os.path.basename(file_path)
    
    # Statistiques détaillées
    remaining, done = count_remaining_files()
    total = remaining + done
    progress = (done / total * 100) if total > 0 else 0
    
    print(f"\n" + "="*80)
    print(f"🚀 TRAITEMENT FICHIER: {filename}")
    print(f"📊 PROGRESSION: {done}/{total} fichiers terminés ({progress:.1f}%)")
    print(f"⏳ RESTANTS: {remaining} fichiers")
    print(f"📁 CHEMIN: {file_path}")
    print(f"⏰ DÉBUT: {time.strftime('%H:%M:%S')}")
    print("="*80)
    
    # Vérifier que le fichier existe avant de commencer
    if not os.path.exists(file_path):
        print(f"❌ ERREUR: Fichier non trouvé: {file_path}")
        return
    
    try:
        # 1. Vectorisation
        print(f"\n🔄 [ÉTAPE 1/3] VECTORISATION")
        print(f"📄 Fichier: {filename}")
        print(f"🔗 Script: {VECTORIZE_SCRIPT}")
        print(f"⏰ Début vectorisation: {time.strftime('%H:%M:%S')}")
        
        result = subprocess.run([sys.executable, VECTORIZE_SCRIPT, file_path], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Vectorisation réussie pour {filename}")
            if result.stdout:
                print(f"📝 Sortie: {result.stdout[:200]}...")
        else:
            print(f"⚠️ Erreur vectorisation: {result.stderr}")
            print(f"📝 Sortie complète: {result.stdout}")

        # 2. Génération des topics
        print(f"\n🔄 [ÉTAPE 2/3] GÉNÉRATION DES TOPICS")
        print(f"📄 Fichier: {filename}")
        print(f"🔗 Script: {TOPIC_SCRIPT}")
        print(f"⏰ Début génération topics: {time.strftime('%H:%M:%S')}")
        
        result = subprocess.run([sys.executable, TOPIC_SCRIPT, filename], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Génération topics réussie pour {filename}")
            if result.stdout:
                print(f"📝 Topics générés: {result.stdout[:300]}...")
        else:
            print(f"⚠️ Erreur génération topics: {result.stderr}")
            print(f"📝 Sortie complète: {result.stdout}")

        # 3. Génération des articles
        print(f"\n🔄 [ÉTAPE 3/3] GÉNÉRATION DES ARTICLES")
        print(f"📄 Fichier source: {filename}")
        print(f"🔗 Script: {ARTICLE_SCRIPT}")
        print(f"📊 Nombre d'articles: 100")
        print(f"⏰ Début génération articles: {time.strftime('%H:%M:%S')}")
        
        result = subprocess.run([sys.executable, ARTICLE_SCRIPT, "100"], 
                              capture_output=True, text=True, timeout=1800)
        
        if result.returncode == 0:
            print(f"✅ Génération articles réussie")
            if result.stdout:
                print(f"📝 Articles générés: {result.stdout[:400]}...")
        else:
            print(f"⚠️ Erreur génération articles: {result.stderr}")
            print(f"📝 Sortie complète: {result.stdout}")

        # Déplacement sécurisé du fichier
        dest = os.path.join(DONE_DIRECTORY, filename)
        print(f"\n📦 FINALISATION")
        print(f"🔄 Déplacement: {file_path} → {dest}")
        
        if safe_file_move(file_path, dest):
            # Nouvelles statistiques après traitement
            remaining_after, done_after = count_remaining_files()
            total_after = remaining_after + done_after
            progress_after = (done_after / total_after * 100) if total_after > 0 else 0
            
            print(f"✅ SUCCÈS COMPLET pour {filename}")
            print(f"📊 NOUVELLE PROGRESSION: {done_after}/{total_after} fichiers terminés ({progress_after:.1f}%)")
            print(f"⏳ NOUVEAUX RESTANTS: {remaining_after} fichiers")
            print(f"📁 Fichier déplacé: {dest}")
            print(f"⏰ Fin: {time.strftime('%H:%M:%S')}")
            print("="*80 + "\n")
        else:
            print(f"⚠️ Pipeline terminé mais fichier non déplacé: {filename}")
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ TIMEOUT pour {filename}")
        print(f"⏰ Timeout atteint: {time.strftime('%H:%M:%S')}")
        dest = os.path.join(DONE_DIRECTORY, filename)
        safe_file_move(file_path, dest)
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE dans le pipeline pour {filename} : {e}")
        print(f"⏰ Erreur survenue: {time.strftime('%H:%M:%S')}")
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
