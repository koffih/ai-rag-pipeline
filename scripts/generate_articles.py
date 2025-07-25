#!/usr/bin/env python3
import os
import sys
import requests
from datetime import datetime, timezone
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from article_generator import generate_article
from dotenv import load_dotenv
import logging

load_dotenv()

# ===== CONFIGURATION =====
print("\033[1;36m" + "⚙️  Configuration initiale..." + "\033[0m")
CHROMA_PATH = "./chroma_db/time_management"
CATEGORY_NAME = "Business"
AUTHOR_ID = "af351ecc-7bee-435f-b3bb-35e4ab804704"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

# ===== CONFIGURATION DU LOGGER =====
LOG_FILE = os.path.join(os.path.dirname(__file__), 'article_generation.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ===== CHARGEMENT DES EMBEDDINGS =====
print("\033[1;36m" + "\n🔍 Chargement des embeddings HuggingFace..." + "\033[0m")
try:
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    print("\033[1;32m" + "✅ Embeddings chargés avec succès!" + "\033[0m")
except Exception as e:
    print("\033[1;31m" + f"❌ Erreur lors du chargement des embeddings: {str(e)}" + "\033[0m")
    sys.exit(1)

# ===== CHARGEMENT DE LA BASE CHROMA =====
print("\033[1;36m" + "\n📂 Chargement de la base Chroma..." + "\033[0m")
try:
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding)
    retriever = db.as_retriever()
    print("\033[1;32m" + f"✅ Base Chroma chargée depuis {CHROMA_PATH}" + "\033[0m")
    print(f"Nombre de documents indexés: {db._collection.count()}")
except Exception as e:
    print("\033[1;31m" + f"❌ Erreur lors du chargement de ChromaDB: {str(e)}" + "\033[0m")
    sys.exit(1)

# ===== RECHERCHE DE DOCUMENTS =====
print("\033[1;36m" + "\n🔎 Recherche de documents pertinents..." + "\033[0m")
try:
    query = "time management strategies"
    print(f"Requête: '{query}'")
    docs = retriever.invoke(query)
    print("\033[1;32m" + f"✅ {len(docs)} documents trouvés" + "\033[0m")
    for i, doc in enumerate(docs[:3]):  # Affiche les 3 premiers
        print(f"\nDocument {i+1}:")
        print(f"Source: {doc.metadata.get('source', 'inconnue')}")
        print(f"Contenu: {doc.page_content[:200]}...")
except Exception as e:
    print("\033[1;31m" + f"❌ Erreur lors de la recherche: {str(e)}" + "\033[0m")
    sys.exit(1)

# ===== CONSTRUCTION DU PROMPT =====
print("\033[1;36m" + "\n📝 Construction du prompt..." + "\033[0m")
try:
    context = "\n\n".join([doc.page_content for doc in docs[:8]])
    prompt = f"""
    Ton objectif est de rédiger un article inspirant en français en suivant précisément ces instructions:
    [TEXTE COMPLET IDENTIQUE À CE QUE TU AS DÉJÀ]
    Voici les extraits de texte à utiliser:
    {context}
    """
    print("\033[1;32m" + "✅ Prompt construit avec succès!" + "\033[0m")
    print(f"Taille du contexte: {len(context)} caractères")
except Exception as e:
    print("\033[1;31m" + f"❌ Erreur lors de la construction du prompt: {str(e)}" + "\033[0m")
    sys.exit(1)

# ===== APPEL À DEEPSEEK =====
print("\033[1;36m" + "\n🧠 Appel à l'API DeepSeek..." + "\033[0m")
try:
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": "Tu es un rédacteur web expert."},
                {"role": "user", "content": prompt}
            ]
        },
        timeout=30  # 30 secondes timeout
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print("\033[1;31m" + f"❌ Erreur API: {response.text}" + "\033[0m")
        logging.error(f"FAILURE | API DeepSeek | Status: {response.status_code} | {response.text}")
        sys.exit(1)
        
    result = response.json()
    article = result["choices"][0]["message"]["content"]
    print("\033[1;32m" + "✅ Article généré avec succès!" + "\033[0m")
    print(f"Taille de l'article: {len(article)} caractères")
    logging.info(f"SUCCESS | Article généré | Taille: {len(article)}")
except Exception as e:
    print("\033[1;31m" + f"❌ Erreur lors de l'appel à DeepSeek: {str(e)}" + "\033[0m")
    logging.error(f"FAILURE | DeepSeek | Error: {e}")
    sys.exit(1)

# ===== SUPRESSION DES ANCIENS LOGS =====
print("\033[1;36m" + "\n📄 Extraction des métadonnées..." + "\033[0m")
try:
    title_line = article.strip().split("\n")[0].replace("**", "").strip()
    slug = title_line.lower().replace(" ", "-").replace("**", "")[:60]
    excerpt = article.split("\n")[2][:200]
    print("\033[1;32m" + "✅ Métadonnées extraites!" + "\033[0m")
    print(f"Titre: {title_line}")
    print(f"Slug: {slug}")
    print(f"Extrait: {excerpt}")
except Exception as e:
    print("\033[1;31m" + f"❌ Erreur lors de l'extraction: {str(e)}" + "\033[0m")
    sys.exit(1)

# ===== ENVOI À SUPABASE =====
print("\033[1;36m" + "\n🚀 Envoi à Supabase..." + "\033[0m")
try:
    supabase_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    # 1. Récupérer l'ID de catégorie
    print("\033[1;36m" + "   🔍 Récupération de l'ID de catégorie..." + "\033[0m")
    cat_resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/content_categories?name=eq.{CATEGORY_NAME}",
        headers=supabase_headers,
        timeout=10
    )
    print(f"   Status Code: {cat_resp.status_code}")
    category_id = cat_resp.json()[0]["id"]
    print(f"   ID Catégorie: {category_id}")

    # 2. Création du post
    print("\033[1;36m" + "   ✍️ Création du post..." + "\033[0m")
    blog_post_payload = {
        "title": title_line,
        "slug": slug,
        "content": article,
        "excerpt": excerpt,
        "author_id": AUTHOR_ID,
        "status": "draft",
        "published_at": datetime.now(timezone.utc).isoformat(),  # Correction ici
        "featured_image_url": "",
        "additional_images": []
    }
    post_resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/blog_posts",
        headers=supabase_headers,
        json=blog_post_payload,
        timeout=10
    )
    print(f"   Status Code: {post_resp.status_code}")
    print(f"   Response: {post_resp.text}")

    if post_resp.status_code != 201:
        raise Exception(f"Erreur Supabase: {post_resp.text}")

    # 3. Lien avec la catégorie
    print("\033[1;36m" + "   🔗 Liaison avec la catégorie..." + "\033[0m")
    link_resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/blog_post_content_categories",
        headers=supabase_headers,
        json={"post_id": post_resp.json()[0]["id"], "category_id": category_id},
        timeout=10
    )
    print(f"   Status Code: {link_resp.status_code}")

    print("\033[1;32m" + "\n✅✅✅ Article publié avec succès! ✅✅✅" + "\033[0m")
    print(f"\nTitre: {title_line}")
    print(f"URL: {SUPABASE_URL}/blog/{slug}")
    logging.info(f"SUCCESS | Publication | Titre: {title_line} | Slug: {slug}")

except Exception as e:
    print("\033[1;31m" + f"❌ Erreur Supabase: {str(e)}" + "\033[0m")
    logging.error(f"FAILURE | Publication | Titre: {title_line} | Error: {e}")
    sys.exit(1)
