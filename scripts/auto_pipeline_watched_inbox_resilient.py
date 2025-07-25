#!/usr/bin/env python3
"""
Pipeline RAG résilient pour watched_inbox avec gestion de tous les types de fichiers
"""

import os
import time
import shutil
import sys
import subprocess
import logging
import json
import mimetypes
from datetime import datetime
from pathlib import Path
import signal
import threading

# Configuration des logs
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'watched_inbox_resilient.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configuration des répertoires
WATCH_DIRECTORY = "/home/koffi/rag_project/watched_inbox"
DONE_DIRECTORY = os.path.join(WATCH_DIRECTORY, "done")
PROCESSING_DIRECTORY = os.path.join(WATCH_DIRECTORY, "processing")
FAILED_DIRECTORY = os.path.join(WATCH_DIRECTORY, "failed")
BACKUP_DIRECTORY = os.path.join(WATCH_DIRECTORY, "backup")
CONVERTED_DIRECTORY = os.path.join(WATCH_DIRECTORY, "converted")

# Scripts du pipeline
RAG_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
VECTORIZE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "vectorize_books.py")
TOPIC_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "topic_generator.py")
ARTICLE_SCRIPT = os.path.join(RAG_SCRIPTS_DIR, "generate_articles_from_supabase.py")

# Types de fichiers supportés
SUPPORTED_EXTENSIONS = {
    'text': (".pdf", ".txt", ".docx", ".rtf", ".odt", ".html", ".htm"),
    'ebook': (".epub", ".mobi", ".azw", ".azw3", ".fb2", ".lit", ".pdb"),
    'audio': (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"),
    'image': (".jpg", ".jpeg", ".png", ".tiff", ".bmp")
}

# État de traitement par fichier
processing_state = {}

def setup_directories():
    """Créer tous les répertoires nécessaires"""
    directories = [DONE_DIRECTORY, PROCESSING_DIRECTORY, FAILED_DIRECTORY, BACKUP_DIRECTORY, CONVERTED_DIRECTORY]
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

def detect_file_type(filepath):
    """Détecter le type de fichier"""
    ext = os.path.splitext(filepath)[1].lower()
    
    for file_type, extensions in SUPPORTED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    
    return 'unknown'

def convert_audio_to_text(audio_path, output_path):
    """Convertir un fichier audio en texte via Whisper"""
    try:
        import whisper
        print(f"🎵 Transcription audio: {os.path.basename(audio_path)}")
        
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        text = result["text"]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f"✅ Transcription réussie: {len(text)} caractères")
        return True
    except Exception as e:
        print(f"❌ Erreur transcription: {e}")
        return False

def convert_ebook_to_text(ebook_path, output_path):
    """Convertir un eBook en texte"""
    try:
        # Essayer d'abord avec Calibre
        pdf_path = os.path.join(CONVERTED_DIRECTORY, os.path.splitext(os.path.basename(ebook_path))[0] + '.pdf')
        
        print(f"📚 Conversion eBook: {os.path.basename(ebook_path)}")
        
        # Conversion en PDF
        result = subprocess.run(['ebook-convert', ebook_path, pdf_path], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(pdf_path):
            # Extraction texte du PDF
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            text = '\n'.join([doc.page_content for doc in docs])
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            print(f"✅ Conversion eBook réussie: {len(text)} caractères")
            return True
        else:
            print(f"❌ Erreur conversion eBook: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Erreur conversion eBook: {e}")
        return False

def convert_document_to_text(doc_path, output_path):
    """Convertir un document en texte"""
    try:
        print(f"📄 Conversion document: {os.path.basename(doc_path)}")
        
        # Utiliser pandoc pour la conversion
        result = subprocess.run(['pandoc', doc_path, '-t', 'plain', '-o', output_path], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Vérifier que le fichier contient du texte
            with open(output_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
                if text and len(text) > 100:
                    print(f"✅ Conversion document réussie: {len(text)} caractères")
                    return True
        
        print(f"❌ Erreur conversion document: {result.stderr}")
        return False
    except Exception as e:
        print(f"❌ Erreur conversion document: {e}")
        return False

def convert_pdf_with_ocr(pdf_path, output_path):
    """Convertir un PDF en texte avec OCR si nécessaire"""
    try:
        print(f"📄 Traitement PDF: {os.path.basename(pdf_path)}")
        
        # Essayer d'abord l'extraction normale
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        text = '\n'.join([doc.page_content for doc in docs])
        
        # Si pas de texte, essayer l'OCR
        if not text.strip():
            print(f"🔄 PDF sans texte, lancement OCR...")
            from pdf2image import convert_from_path
            import pytesseract
            
            images = convert_from_path(pdf_path)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img, lang="fra")
            text = ocr_text
            print(f"✅ OCR terminé: {len(text)} caractères")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f"✅ Traitement PDF réussi: {len(text)} caractères")
        return True
    except Exception as e:
        print(f"❌ Erreur traitement PDF: {e}")
        return False

def convert_file_to_text(file_path):
    """Convertir un fichier en texte selon son type"""
    filename = os.path.basename(file_path)
    file_type = detect_file_type(file_path)
    
    # Créer le fichier de sortie
    txt_filename = os.path.splitext(filename)[0] + '.txt'
    txt_path = os.path.join(CONVERTED_DIRECTORY, txt_filename)
    
    print(f"\n🔄 CONVERSION: {filename} (Type: {file_type})")
    
    success = False
    
    if file_type == 'text':
        if filename.lower().endswith('.pdf'):
            success = convert_pdf_with_ocr(file_path, txt_path)
        elif filename.lower().endswith('.txt'):
            # Copier directement
            shutil.copy2(file_path, txt_path)
            success = True
        else:
            success = convert_document_to_text(file_path, txt_path)
    
    elif file_type == 'ebook':
        success = convert_ebook_to_text(file_path, txt_path)
    
    elif file_type == 'audio':
        success = convert_audio_to_text(file_path, txt_path)
    
    else:
        print(f"❌ Type de fichier non supporté: {file_type}")
        return None
    
    if success and os.path.exists(txt_path):
        return txt_path
    else:
        return None

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
        
        # Vérifier si le fichier est présent
        for meta in docs:
            if meta.get("source") == filename:
                return True
        return False
    except Exception as e:
        logging.error(f"Erreur lors de la vérification ChromaDB: {e}")
        return False

def process_file_resilient(file_path):
    """Traitement résilient d'un fichier avec conversion et déplacement automatique"""
    filename = os.path.basename(file_path)
    file_id = f"{filename}_{int(time.time())}"
    
    print(f"\n" + "="*80)
    print(f"🚀 TRAITEMENT RÉSILIENT WATCHED_INBOX: {filename}")
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
        # ÉTAPE 1: Conversion en texte
        processing_state[file_id]['current_step'] = 'conversion'
        print(f"\n🔄 [ÉTAPE 1/4] CONVERSION EN TEXTE")
        
        txt_path = convert_file_to_text(file_path)
        
        if txt_path and os.path.exists(txt_path):
            print(f"✅ Conversion réussie")
            processing_state[file_id]['steps_completed'].append('conversion')
            
            # Déplacer le fichier original vers processing
            processing_path = os.path.join(PROCESSING_DIRECTORY, filename)
            if safe_file_move(file_path, processing_path):
                file_path = processing_path  # Mettre à jour le chemin
                print(f"📦 Fichier original déplacé vers processing")
        else:
            error_msg = "Échec de la conversion en texte"
            processing_state[file_id]['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            # Déplacer vers failed
            failed_path = os.path.join(FAILED_DIRECTORY, filename)
            safe_file_move(file_path, failed_path)
            return False
        
        # ÉTAPE 2: Vectorisation
        processing_state[file_id]['current_step'] = 'vectorization'
        print(f"\n🔄 [ÉTAPE 2/4] VECTORISATION")
        
        result = subprocess.run([sys.executable, VECTORIZE_SCRIPT, txt_path], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Vectorisation réussie")
            processing_state[file_id]['steps_completed'].append('vectorization')
        else:
            error_msg = f"Erreur vectorisation: {result.stderr}"
            processing_state[file_id]['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            # Déplacer vers failed
            failed_path = os.path.join(FAILED_DIRECTORY, filename)
            safe_file_move(file_path, failed_path)
            return False
        
        # ÉTAPE 3: Génération des topics
        processing_state[file_id]['current_step'] = 'topics'
        print(f"\n🔄 [ÉTAPE 3/4] GÉNÉRATION DES TOPICS")
        
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
        
        # ÉTAPE 4: Génération des articles
        processing_state[file_id]['current_step'] = 'articles'
        print(f"\n🔄 [ÉTAPE 4/4] GÉNÉRATION DES ARTICLES")
        
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
        if filename not in ['done', 'processing', 'failed', 'backup', 'converted']:
            full_path = os.path.join(WATCH_DIRECTORY, filename)
            if os.path.isfile(full_path):
                # Vérifier si c'est un type supporté
                file_type = detect_file_type(full_path)
                if file_type != 'unknown':
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
        if filename not in ['done', 'processing', 'failed', 'backup', 'converted']:
            full_path = os.path.join(WATCH_DIRECTORY, filename)
            if os.path.isfile(full_path):
                # Vérifier si c'est un type supporté
                file_type = detect_file_type(full_path)
                if file_type != 'unknown':
                    print(f"\n🎯 Traitement du fichier: {filename} (Type: {file_type})")
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
    print("🛡️ Pipeline RAG Résilient - Watched Inbox")
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