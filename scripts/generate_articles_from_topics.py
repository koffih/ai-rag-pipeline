import time
import os
import sys
import logging
from datetime import datetime

from local_llm import generate_article
from rag_scripts.database import insert_article, get_or_create_category

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuration du logger
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'article_generation.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

with open("topics_cleaned.txt", "r") as f:
    topics = [line.strip() for line in f if line.strip()]

limit = 3
print(f"📝 Génération limitée à {limit} d'articles.")
print(f"📚 {len(topics)} topics chargés.\n")

for i, topic in enumerate(topics[:limit], 1):
    print(f"🔹 [{i}] Génération pour le topic : {topic}\n")
    try:
        article = generate_article(topic)
        category_name = topic.split(",")[0].strip().capitalize()
        category_id = get_or_create_category(category_name)
        if not category_id:
            print(f"❌ Impossible de créer ou récupérer la catégorie pour {category_name}")
            logging.error(f"FAILURE | {topic} | Catégorie non trouvée")
            continue
        insert_article(article, category_id)
        print("✅ Article inséré dans la base de données\n")
        logging.info(f"SUCCESS | {topic} | Catégorie: {category_name}")
    except Exception as e:
        print(f"❌ Erreur lors de la génération de l'article pour {topic} : {e}")
        logging.error(f"FAILURE | {topic} | Error: {e}")
    time.sleep(1)

print("\n✅ Limite atteinte :", limit, "articles générés.")
print("\n🚀 Terminé.")
