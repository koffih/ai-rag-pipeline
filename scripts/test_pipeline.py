import os
import shutil
import subprocess
import time
import logging
from pathlib import Path
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from rag_scripts.database import supabase

# --- CONFIG ---
PDF_NAME = "BeYourOwnSailingCoach.pdf"
PDF_SOURCE = PDF_NAME
PDF_ORIGIN = os.path.join("/home/koffi/rag_project/watched_inbox", PDF_NAME)
WATCHED_DIR = "/home/koffi/watched_inbox"
DONE_DIR = os.path.join(WATCHED_DIR, "done")
PDF_DEST = os.path.join(WATCHED_DIR, PDF_NAME)
CHROMA_DIR = "/home/koffi/rag_scripts/chroma_store"

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("test_pipeline")

def run_subprocess(script, args=None):
    cmd = [sys.executable, script]
    if args:
        cmd += args
    logger.info(f"Lancement du script : {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.info(result.stdout)
    if result.returncode != 0:
        logger.error(result.stderr)
        raise RuntimeError(f"Le script {script} a échoué.")

def copy_pdf():
    if not os.path.exists(PDF_DEST):
        if os.path.exists(PDF_ORIGIN):
            shutil.copy(PDF_ORIGIN, PDF_DEST)
            logger.info(f"PDF de test copié dans {WATCHED_DIR}")
        else:
            logger.error(f"Le PDF de test n'existe pas à {PDF_ORIGIN}")
            raise FileNotFoundError(PDF_ORIGIN)
    else:
        logger.info(f"Le PDF de test est déjà présent dans {WATCHED_DIR}")

def wait_for_file_in_done(timeout=60):
    logger.info("Attente du déplacement du PDF dans le dossier 'done'...")
    dest = os.path.join(DONE_DIR, PDF_NAME)
    for _ in range(timeout):
        if os.path.exists(dest):
            logger.info(f"PDF déplacé dans {DONE_DIR} : vectorisation OK.")
            return True
        time.sleep(1)
    logger.error("Le PDF n'a pas été déplacé dans 'done' après vectorisation.")
    return False

def get_topics():
    logger.info("Vérification des topics générés pour ce PDF...")
    resp = supabase.table("topics").select("*").eq("source", PDF_SOURCE).execute()
    return resp.data if resp.data else []

def get_articles_for_topics(topic_names):
    logger.info("Vérification des articles générés pour les topics...")
    if not topic_names:
        return []
    # On suppose que le champ 'title' correspond au topic
    resp = supabase.table("blog_posts").select("*").in_("title", topic_names).execute()
    return resp.data if resp.data else []

def cleanup():
    logger.info("Nettoyage des données de test...")
    # 1. Supprimer le PDF de test dans watched_pdfs/ et done/
    for path in [PDF_DEST, os.path.join(DONE_DIR, PDF_NAME)]:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Fichier supprimé : {path}")
    # 2. Supprimer les topics et articles dans Supabase
    topics = get_topics()
    topic_names = [t["name"] for t in topics]
    if topics:
        ids = [t["id"] for t in topics if "id" in t]
        for id_ in ids:
            supabase.table("topics").delete().eq("id", id_).execute()
        logger.info(f"Topics supprimés dans Supabase : {len(ids)}")
    articles = get_articles_for_topics(topic_names)
    if articles:
        ids = [a["id"] for a in articles if "id" in a]
        for id_ in ids:
            supabase.table("blog_posts").delete().eq("id", id_).execute()
        logger.info(f"Articles supprimés dans Supabase : {len(ids)}")
    logger.warning("Nettoyage ChromaDB manuel recommandé si besoin (pas d'API pour suppression ciblée)")

def main():
    try:
        logger.info("--- DÉBUT DU TEST PIPELINE RAG ---")
        copy_pdf()
        run_subprocess(os.path.join(os.path.dirname(__file__), "watch_and_vectorize.py"), ["--once"])
        if not wait_for_file_in_done():
            raise RuntimeError("Vectorisation non détectée.")
        run_subprocess(os.path.join(os.path.dirname(__file__), "topic_generator.py"), [PDF_NAME])
        topics = get_topics()
        if not topics:
            raise RuntimeError("Aucun topic généré pour ce PDF.")
        logger.info(f"{len(topics)} topics générés.")
        run_subprocess(os.path.join(os.path.dirname(__file__), "generate_articles_from_supabase.py"), ["1"])
        articles = get_articles_for_topics([t["name"] for t in topics])
        if not articles:
            raise RuntimeError("Aucun article généré pour ce PDF.")
        logger.info(f"{len(articles)} article(s) généré(s) pour ce PDF.")
        logger.info("--- TEST PIPELINE RÉUSSI ---")
    except Exception as e:
        logger.error(f"Erreur lors du test pipeline : {e}")
    finally:
        cleanup()

if __name__ == "__main__":
    main() 