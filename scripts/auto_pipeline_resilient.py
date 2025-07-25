#!/usr/bin/env python3
"""
Pipeline RAG résilient avec déplacement automatique des fichiers après chaque étape
"""

import os
import time
import shutil
import sys
import subprocess
import logging
import json
from datetime import datetime
from pathlib import Path
import signal
import threading

# Configuration des logs
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'resilient_pipeline.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration des répertoires
WATCH_DIRECTORY = "/home/koffi/rag_project/extractable_files"
DONE_DIRECTORY = os.path.join(WATCH_DIRECTORY, "done")
PROCESSING_DIRECTORY = os.path.join(WATCH_DIRECTORY, "processing")
FAILED_DIRECTORY = os.path.join(WATCH_DIRECTORY, "failed")
BACKUP_DIRECTORY = os.path.join(WATCH_DIRECTORY, "backup")

# Scripts du pipeline
RAG_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
VECTORIZE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "vectorize_books.py")
TOPIC_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "topic_generator.py")
ARTICLE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "generate_articles_from_supabase.py")

SUPPORTED_EXTENSIONS = (".pdf", ".epub", ".mobi", ".azw3", ".txt", ".docx")

# État de traitement par fichier
processing_state = {}

def setup_directories():
    """Créer tous les répertoires nécessaires"""
    directories = [DONE_DIRECTORY, PROCESSING_DIRECTORY, FAILED_DIRECTORY, BACKUP_DIRECTORY]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logging.info(f"Répertoire créé/vérifié: {directory}")

def safe_file_move(src, dst, max_retries=3):
    """Déplacement sécurisé avec retry et backup"""
    for attempt in range(max_retries):
        try:
            if os.path.exists(src):
                # Créer un backup avant déplacement
                backup_path = os.path.join(BACKUP_DIRECTORY, os.path.basename(src))
                shutil.copy2(src, backup_path)
                
                # Déplacer le fichier
                shutil.move(src, dst)
                logging.info(f"Fichier déplacé avec succès: {src} → {dst}")
                return True
            else:
                logging.warning(f"Fichier source non trouvé: {src}")
                return False
        except Exception as e:
            logging.error(f"Tentative {attempt + 1} échouée pour {src}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Backoff exponentiel
            else:
                logging.error(f"Échec définitif du déplacement: {src}")
                return False
    return False

def check_file_in_chroma(filename):
    """Vérifier si un fichier est déjà vectorisé dans ChromaDB"""
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings
        
        CHROMA_DIR = "/home/koffi/rag_scripts/chroma_store"
        embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_model)
        
        # Récupérer tous les documents
        docs = vectorstore.get()["metadatas"]
        texts = vectorstore.get()["documents"]
        
        # Vérifier si le fichier est présent
        for meta in docs:
            if meta.get("source") == filename:
                return True
        return False
    except Exception as e:
        logging.error(f"Erreur lors de la vérification ChromaDB: {e}")
        return False

def process_file_resilient(file_path):
    """Traitement résilient d'un fichier avec déplacement après chaque étape"""
    filename = os.path.basename(file_path)
    file_id = f"{filename}_{int(time.time())}"
    
    print(f"\n" + "="*80)
    print(f"🚀 TRAITEMENT RÉSILIENT: {filename}")
    print(f"🆔 ID: {file_id}")
    print(f"⏰ DÉBUT: {datetime.now().strftime('%H:%M:%S')}")
    print("="*80)
    
    # Initialiser l'état de traitement
    processing_state[file_id] = {
        'filename': filename,
        'start_time': datetime.now(),
        'steps_completed': [],
        'current_step': 'init',
        'errors': []
    }
    
    # Vérifier que le fichier existe
    if not os.path.exists(file_path):
        error_msg = f"Fichier non trouvé: {file_path}"
        processing_state[file_id]['errors'].append(error_msg)
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        return False
    
    # Vérifier si déjà vectorisé
    if check_file_in_chroma(filename):
        print(f"✅ Fichier déjà vectorisé: {filename}")
        # Déplacer directement vers done
        dest = os.path.join(DONE_DIRECTORY, filename)
        if safe_file_move(file_path, dest):
            processing_state[file_id]['steps_completed'].append('already_vectorized')
            print(f"📦 Fichier déplacé vers done: {dest}")
            return True
    
    try:
        # ÉTAPE 1: Vectorisation
        processing_state[file_id]['current_step'] = 'vectorization'
        print(f"\n🔄 [ÉTAPE 1/3] VECTORISATION")
        
        result = subprocess.run([sys.executable, VECTORIZE_SCRIPT, file_path], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Vectorisation réussie")
            processing_state[file_id]['steps_completed'].append('vectorization')
            
            # Déplacer vers processing après vectorisation réussie
            processing_path = os.path.join(PROCESSING_DIRECTORY, filename)
            if safe_file_move(file_path, processing_path):
                file_path = processing_path  # Mettre à jour le chemin
                print(f"📦 Fichier déplacé vers processing après vectorisation")
        else:
            error_msg = f"Erreur vectorisation: {result.stderr}"
            processing_state[file_id]['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            # Déplacer vers failed
            failed_path = os.path.join(FAILED_DIRECTORY, filename)
            safe_file_move(file_path, failed_path)
            return False
        
        # ÉTAPE 2: Génération des topics
        processing_state[file_id]['current_step'] = 'topics'
        print(f"\n🔄 [ÉTAPE 2/3] GÉNÉRATION DES TOPICS")
        
        result = subprocess.run([sys.executable, TOPIC_SCRIPT, filename], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Génération topics réussie")
            processing_state[file_id]['steps_completed'].append('topics')
        else:
            error_msg = f"Erreur génération topics: {result.stderr}"
            processing_state[file_id]['errors'].append(error_msg)
            print(f"⚠️ {error_msg}")
            # Continuer quand même car la vectorisation est réussie
        
        # ÉTAPE 3: Génération des articles
        processing_state[file_id]['current_step'] = 'articles'
        print(f"\n🔄 [ÉTAPE 3/3] GÉNÉRATION DES ARTICLES")
        
        result = subprocess.run([sys.executable, ARTICLE_SCRIPT, "100"], 
                              capture_output=True, text=True, timeout=1800)
        
        if result.returncode == 0:
            print(f"✅ Génération articles réussie")
            processing_state[file_id]['steps_completed'].append('articles')
        else:
            error_msg = f"Erreur génération articles: {result.stderr}"
            processing_state[file_id]['errors'].append(error_msg)
            print(f"⚠️ {error_msg}")
            # Continuer car la vectorisation et les topics sont réussis
        
        # FINALISATION: Déplacer vers done
        processing_state[file_id]['current_step'] = 'finalization'
        dest = os.path.join(DONE_DIRECTORY, filename)
        
        if safe_file_move(file_path, dest):
            processing_state[file_id]['steps_completed'].append('completed')
            processing_state[file_id]['end_time'] = datetime.now()
            
            print(f"\n✅ SUCCÈS COMPLET pour {filename}")
            print(f"📊 Étapes réussies: {', '.join(processing_state[file_id]['steps_completed'])}")
            print(f"📁 Fichier final: {dest}")
            print(f"⏰ Durée totale: {processing_state[file_id]['end_time'] - processing_state[file_id]['start_time']}")
            
            # Sauvegarder l'état de traitement
            save_processing_state(file_id)
            return True
        else:
            error_msg = "Échec du déplacement final"
            processing_state[file_id]['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return False
            
    except subprocess.TimeoutExpired as e:
        error_msg = f"Timeout pour {filename}: {e}"
        processing_state[file_id]['errors'].append(error_msg)
        print(f"⏱️ {error_msg}")
        
        # Déplacer vers failed en cas de timeout
        failed_path = os.path.join(FAILED_DIRECTORY, filename)
        safe_file_move(file_path, failed_path)
        return False
        
    except Exception as e:
        error_msg = f"Erreur critique pour {filename}: {e}"
        processing_state[file_id]['errors'].append(error_msg)
        print(f"❌ {error_msg}")
        logging.error(error_msg)
        
        # Déplacer vers failed
        failed_path = os.path.join(FAILED_DIRECTORY, filename)
        safe_file_move(file_path, failed_path)
        return False

def save_processing_state(file_id):
    """Sauvegarder l'état de traitement dans un fichier JSON"""
    try:
        state_file = os.path.join(WATCH_DIRECTORY, f"processing_state_{file_id}.json")
        with open(state_file, 'w') as f:
            json.dump(processing_state[file_id], f, default=str, indent=2)
        logging.info(f"État de traitement sauvegardé: {state_file}")
    except Exception as e:
        logging.error(f"Erreur sauvegarde état: {e}")

def count_files_by_status():
    """Compter les fichiers par statut"""
    counts = {
        'pending': 0,
        'processing': 0,
        'done': 0,
        'failed': 0
    }
    
    # Fichiers en attente
    for filename in os.listdir(WATCH_DIRECTORY):
        if filename not in ['done', 'processing', 'failed', 'backup']:
            full_path = os.path.join(WATCH_DIRECTORY, filename)
            if os.path.isfile(full_path) and filename.lower().endswith(SUPPORTED_EXTENSIONS):
                counts['pending'] += 1
    
    # Fichiers en cours de traitement
    if os.path.exists(PROCESSING_DIRECTORY):
        counts['processing'] = len([f for f in os.listdir(PROCESSING_DIRECTORY) 
                                   if os.path.isfile(os.path.join(PROCESSING_DIRECTORY, f))])
    
    # Fichiers terminés
    if os.path.exists(DONE_DIRECTORY):
        counts['done'] = len([f for f in os.listdir(DONE_DIRECTORY) 
                             if os.path.isfile(os.path.join(DONE_DIRECTORY, f))])
    
    # Fichiers échoués
    if os.path.exists(FAILED_DIRECTORY):
        counts['failed'] = len([f for f in os.listdir(FAILED_DIRECTORY) 
                               if os.path.isfile(os.path.join(FAILED_DIRECTORY, f))])
    
    return counts

def process_existing_files(only_one=False):
    """Traiter les fichiers existants"""
    print("🔁 Vérification des fichiers existants...")
    
    counts = count_files_by_status()
    print(f"📊 État actuel:")
    print(f"  - En attente: {counts['pending']}")
    print(f"  - En cours: {counts['processing']}")
    print(f"  - Terminés: {counts['done']}")
    print(f"  - Échoués: {counts['failed']}")
    
    processed = 0
    
    # Traiter les fichiers en attente
    for filename in os.listdir(WATCH_DIRECTORY):
        if filename not in ['done', 'processing', 'failed', 'backup']:
            full_path = os.path.join(WATCH_DIRECTORY, filename)
            if os.path.isfile(full_path) and filename.lower().endswith(SUPPORTED_EXTENSIONS):
                print(f"\n🎯 Traitement du fichier: {filename}")
                if process_file_resilient(full_path):
                    processed += 1
                else:
                    print(f"❌ Échec du traitement: {filename}")
                
                if only_one:
                    break
    
    print(f"\n📊 {processed} fichiers traités")
    return processed

def main():
    """Fonction principale"""
    print("🛡️ Pipeline RAG Résilient")
    print("=" * 50)
    
    # Configuration
    setup_directories()
    
    # Traitement des fichiers existants
    process_existing_files()
    
    print("\n✅ Pipeline résilient terminé")
    print(f"📝 Logs détaillés: {LOG_FILE}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--one', action='store_true', help='Traiter un seul fichier')
    args = parser.parse_args()
    
    if args.one:
        process_existing_files(only_one=True)
    else:
        main() 