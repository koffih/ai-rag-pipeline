import requests
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import re

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_API_KEY") or os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_unprocessed_topics():
    response = supabase.table("topics") \
        .select("*") \
        .eq("processed", False) \
        .execute()
    return response.data

def mark_topic_as_processed(topic_name):
    supabase.table("topics") \
        .update({"processed": True}) \
        .eq("name", topic_name) \
        .execute()

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def insert_article_to_supabase(article_markdown: str, topic: str):
    slug = slugify(topic)
    data = {
        "title": topic[:100],
        "slug": slug,
        "content": article_markdown,
        "category_id": None,  # Peut être mis à jour plus tard
        "status": "published"  # Ajout du statut obligatoire
    }

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/blog_posts",
        json=data,
        headers=headers
    )

    if response.status_code == 201:
        print("✅ Article inséré dans Supabase")
    elif response.status_code == 409:
        print("⚠️ Article déjà existant (slug dupliqué), ignoré.")
    else:
        print(f"❌ Erreur d'insertion Supabase : {response.status_code}")
        print(response.text)
