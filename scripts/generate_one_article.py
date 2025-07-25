import os
import sys
import requests
import psycopg2
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from rag_scripts.llm_utils import generate_text
from dotenv import load_dotenv
import re

load_dotenv()

# 🔧 Config
CHROMA_DIR = "/mnt/c/Users/koffi/Documents/RAG/books/time_management"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

# --- NEW: Fetch topics from Supabase REST API ---
def fetch_topics_from_supabase(source_pdf):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    params = {
        "select": "*",
        "source": f"eq.{source_pdf}"
    }
    response = requests.get(f"{SUPABASE_URL}/rest/v1/topics", headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def slugify(text):
    text = text.lower()
    text = re.sub(r"[’'`]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_one_article.py <source_pdf>")
        exit(1)
    source_pdf = sys.argv[1]
    topics = fetch_topics_from_supabase(source_pdf)
    if not topics:
        print(f"No topics found for {source_pdf}")
        exit(0)
    print(f"[INFO] {len(topics)} topics fetched from Supabase for {source_pdf}")

    # 🧠 Embeddings & Chroma
    embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_function)

    import supabase
    from supabase import create_client
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

    for topic_obj in topics:
        topic = (
            topic_obj.get("title")
            or topic_obj.get("name")
            or topic_obj.get("label")
            or topic_obj.get("topic")
        )
        if not topic:
            print(f"[WARNING] Topic object without valid name: {topic_obj}")
            continue
        print(f"\n📌 Sujet sélectionné : {topic}\n")

        print("🔍 Recherche des documents pertinents...")
        docs = db.similarity_search(topic, k=5)
        context = "\n\n".join([doc.page_content for doc in docs])
        print(f"✅ {len(docs)} documents récupérés\n")

        # Limite de longueur du contexte pour le prompt (modifiable)
        max_context_length = 2000
        if len(context) > max_context_length:
            print(f"[INFO] Contexte tronqué de {len(context)} à {max_context_length} caractères")
            context = context[:max_context_length]

        # ✍️ Prompt structuré
        prompt = f"""
Tu es un expert en gestion du temps. Rédige l'article ci-dessous intégralement en français, même si le contexte est en anglais.
À partir du contexte suivant :

{context}

Génère un article structuré au format suivant :

---
**Citation inspirante**
Une citation puissante qui introduit le sujet.

**Titre principal (en gras, première lettre en majuscule)**  
Un titre percutant.

# **Section 1 : Introduction**  
Présente le sujet avec une voix active, claire et directe.

# **Section 2 : Conseils ou techniques**  
Utilise une énumération avec émojis (1️⃣, 2️⃣, etc.). Donne des exemples concrets.

# **Section 3 : Cas d'usage ou erreur à éviter**  
Sois spécifique, clair et utile.

# **Conclusion**  
Synthétise et propose une réflexion ou un appel à l'action.
---

Rédige en Markdown et uniquement en français.
"""

        print(f"[INFO] Prompt envoyé à DeepSeek : {len(prompt)} caractères")
        # 🤖 Appel à DeepSeek
        print("⚙️ Envoi du prompt à DeepSeek...")
        article = generate_text(prompt, model="deepseek-chat", temperature=0.7)
        print("✅ Article généré\n")

        # 💾 Insertion dans Supabase
        # Vérifie ou crée la catégorie
        print("🔎 Vérification de la catégorie...")
        cat = supabase_client.table("blog_categories").select("*").eq("name", topic).execute()
        if len(cat.data) == 0:
            print("🆕 Catégorie absente, création...")
            cat_slug = slugify(topic)
            new_cat = supabase_client.table("blog_categories").insert({"name": topic, "slug": cat_slug}).execute()
            category_id = new_cat.data[0]["id"]
        else:
            category_id = cat.data[0]["id"]
        print(f"✅ Catégorie ID : {category_id}\n")

        # Vérifie si le slug existe déjà
        slug = slugify(topic)
        existing = supabase_client.table("blog_posts").select("id").eq("slug", slug).execute()
        if existing.data:
            print(f"[INFO] Article déjà existant pour le slug '{slug}', on passe au suivant.")
            continue
        supabase_client.table("blog_posts").insert({
            "title": topic,
            "slug": slug,
            "content": article,
            "category_id": category_id,
            "status": "draft"
        }).execute()

        print("✅ Article inséré dans la base Supabase avec succès.")
