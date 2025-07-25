print("[DEBUG] Début d'exécution de topic_generator.py")
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import uuid
import requests
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import argparse
from rag_scripts.llm_utils import generate_text
import re

# Chargement des variables d'environnement
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY") or os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

# Configuration
CHROMA_DIR = "/home/koffi/rag_scripts/chroma_store"
MODEL_PATH = "/home/koffi/.cache/huggingface/hub/models--TheBloke--Mistral-7B-Instruct-v0.1-GPTQ/snapshots/6ae1e4ae2cfbaf107c705ed722ec243b4f88014d"

def clean_chunk(text):
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        l = line.strip()
        # Ignore pagination, numéros de page, titres génériques
        if re.match(r'^(page|chapitre|table des matières|sommaire|contents|index|copyright|isbn|\d+)$', l, re.IGNORECASE):
            continue
        if l.isdigit() or len(l) < 3:
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)

def extract_topics_from_source(source_name, batch_size=8):
    print("[DEBUG] Entrée dans extract_topics_from_source")
    print("[DEBUG] Avant HuggingFaceEmbeddings")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    print("[DEBUG] Après HuggingFaceEmbeddings")
    print("[DEBUG] Avant Chroma")
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_model)
    print("[DEBUG] Après Chroma")
    docs = vectorstore.get()["metadatas"]
    texts = vectorstore.get()["documents"]
    print(f"[DEBUG] Récupération des metadatas et textes OK : {len(docs)} metadatas, {len(texts)} textes")
    filtered_chunks = [
        texts[i] for i, meta in enumerate(docs)
        if meta.get("source") == source_name
    ]
    print(f"[DEBUG] {len(filtered_chunks)} chunks filtrés pour {source_name}")
    if not filtered_chunks:
        print("⚠️ Aucun chunk trouvé pour ce document.")
        return []
    print("[DEBUG] Début de la boucle de génération de topics")
    all_topics = []
    max_prompt_length = 4000
    for i in range(0, len(filtered_chunks), batch_size):
        if i >= batch_size * 5:
            print("[DEBUG] Arrêt anticipé pour test (5 batchs)")
            break
        print(f"[DEBUG] Batch {i//batch_size+1} sur {len(filtered_chunks)//batch_size+1}")
        batch = [clean_chunk(chunk) for chunk in filtered_chunks[i:i + batch_size]]
        full_text = "\n".join(batch)
        if len(full_text) > max_prompt_length:
            full_text = full_text[:max_prompt_length]
        prompt = (
            "Voici un extrait d'un livre. Donne une **liste de 10 à 30 topics importants**, "
            "chaque topic sur une seule ligne. Pas de phrases longues. Pas d'exemples. Pas de détails. "
            "Seulement des mots-clés ou concepts brefs (1 à 6 mots).\n\n"
            "N'inclus pas la pagination, les numéros de page, les titres de chapitre, ou tout élément technique. "
            "Ne retiens que les vrais concepts ou idées du livre.\n\n"
            f"---\n{full_text}\n---\n\nListe :\n"
        )
        print(f"[INFO] Génération de topics pour le batch {i//batch_size+1} (taille: {len(batch)})")
        print(f"[DEBUG] Prompt envoyé (premiers 200 caractères): {prompt[:200]} ...")
        try:
            result = generate_text(prompt, model="deepseek-chat", temperature=0.3, max_tokens=300)
            print("[INFO] Réponse reçue de DeepSeek.")
        except Exception as e:
            print(f"[ERROR] Erreur lors de l'appel à DeepSeek: {e}")
            continue
        lines = result.split("Liste :")[-1].strip().split("\n")
        raw_topics = [line.strip("-•*–—1234567890. ").strip() for line in lines if line.strip()]
        # Post-filtrage : ignore topics qui ressemblent à des numéros, à 'Page X', ou trop courts
        filtered = [
            t for t in raw_topics
            if 3 <= len(t) <= 60 and not re.match(r'^(page|chapitre|\d+)$', t, re.IGNORECASE) and t.lower() not in ("liste", "introduction") and " " in t
        ]
        all_topics.extend(filtered)

    unique = list(dict.fromkeys(all_topics))
    print(f"✅ {len(unique)} topics nettoyés.")
    return unique

def insert_topics_to_supabase(topics, user_id, source_name):
    print("📤 Insertion dans Supabase via REST API...")
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    }

    success = 0
    for topic in topics:
        payload = {
            "id": str(uuid.uuid4()),
            "name": topic,
            "label": topic,
            "source": source_name,
            "user_id": user_id
        }
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/topics",
            headers=headers,
            json=payload
        )
        if response.status_code in (200, 201):
            success += 1
        else:
            print(f"❌ Erreur pour '{topic}' : {response.status_code} {response.text}")

    print(f"✅ {success} topics insérés avec succès.")

if __name__ == "__main__":
    print("[DEBUG] Entrée dans le main de topic_generator.py")
    parser = argparse.ArgumentParser()
    parser.add_argument("source_name", nargs="?", type=str, help="Nom du PDF à traiter (ex: BeYourOwnSailingCoach.pdf)")
    parser.add_argument("--user_id", type=str, default=None, help="ID utilisateur pour l'insertion Supabase (UUID)")
    parser.add_argument("--test-deepseek", action="store_true", help="Test rapide de l'API DeepSeek")
    args = parser.parse_args()

    if args.test_deepseek:
        print("[TEST] Appel DeepSeek avec prompt minimal...")
        try:
            result = generate_text("Bonjour, peux-tu générer une liste de 3 topics sur la gestion du temps ?", model="deepseek-chat", temperature=0.3, max_tokens=100)
            print("[SUCCESS] Réponse DeepSeek :")
            print(result)
        except Exception as e:
            print(f"[ERROR] DeepSeek API test failed: {e}")
        exit(0)

    # Si aucun user_id n'est fourni, on génère un UUID aléatoire
    user_id = args.user_id if args.user_id else str(uuid.uuid4())
    topics = extract_topics_from_source(args.source_name)
    print("[DEBUG] Fin de extract_topics_from_source")
    if not topics:
        print("⚠️ Aucun topic généré pour ce document.")
    else:
        insert_topics_to_supabase(topics, user_id, args.source_name)

