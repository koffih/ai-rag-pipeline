import requests
import json
from topic_generator import extract_topics_from_source
import os
from dotenv import load_dotenv

load_dotenv()

# 📁 Nom du document PDF vectorisé
SOURCE_NAME = "OCR_Ghanadan, Hamid - Persuading Scientists_ Marketing to the World's Most Skeptical Audience-Linus Press (2019).pdf"

# 🔐 Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# 🗃️ Table cible Supabase
TABLE_NAME = "topics"

# 📚 Extraction
topics = extract_topics_from_source(SOURCE_NAME)

# 🔁 Insertion une par une (ou tu peux grouper)
for topic in topics:
    data = {
        "source": SOURCE_NAME,
        "label": topic
    }

    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        data=json.dumps(data)
    )

    if response.status_code in (200, 201, 204):
        print(f"✅ Inséré : {topic}")
    else:
        print(f"❌ Erreur pour '{topic}' → {response.status_code} : {response.text}")
