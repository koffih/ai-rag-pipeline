import sys
import os
import random  # ou tout autre import standard
import logging
from datetime import datetime

# fixer le chemin du projet (juste après os, sys)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# maintenant seulement : les imports internes du projet
from rag_scripts.database import (
    insert_article_to_supabase,
    fetch_unprocessed_topics,
    mark_topic_as_processed
)
from local_llm import generate_article

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuration du logger
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'article_generation.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    print("\n" + "="*80)
    print("🚀 GÉNÉRATION D'ARTICLES DEPUIS SUPABASE")
    print("="*80)
    print(f"⏰ Début du traitement: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Limite d'articles: {limit}")
    print(f"📁 Fichier de log: {LOG_FILE}")
    print("="*80)

    print("\n🔍 RÉCUPÉRATION DES TOPICS DEPUIS SUPABASE...")
    topics = fetch_unprocessed_topics()
    total_topics = len(topics)
    
    print(f"📚 TOTAL TOPICS RÉCUPÉRÉS: {total_topics}")
    
    if total_topics == 0:
        print("⚠️ AUCUN TOPIC NON TRAITÉ DISPONIBLE")
        print("🛑 ARRÊT DU SCRIPT")
        sys.exit(0)

    print(f"🔀 MÉLANGE ALÉATOIRE DES TOPICS")
    random.shuffle(topics)

    print(f"\n📋 APERÇU DES TOPICS À TRAITER:")
    for i, topic in enumerate(topics[:min(5, len(topics))], 1):
        print(f"  {i}. {topic['name']} (ID: {topic.get('id', 'N/A')}, User: {topic.get('user_id', 'N/A')[:8]}...)")
    if len(topics) > 5:
        print(f"  ... et {len(topics) - 5} autres topics")

    generated_count = 0
    start_time = datetime.now()

    for idx, topic in enumerate(topics, start=1):
        topic_name = topic['name']
        topic_id = topic.get('id', 'N/A')
        user_id = topic.get('user_id', 'N/A')
        
        print("\n" + "="*80)
        print(f"🔹 TRAITEMENT [{idx}/{total_topics}] - PROGRESSION: {((idx-1)/total_topics*100):.1f}%")
        print(f"📰 TOPIC: {topic_name}")
        print(f"🆔 TOPIC ID: {topic_id}")
        print(f"👤 USER ID: {user_id}")
        print(f"⏰ Début traitement: {datetime.now().strftime('%H:%M:%S')}")
        print("-"*80)

        try:
            print(f"⚙️ [GÉNÉRATION] Création de l'article pour le topic: '{topic_name}'")
            article_start_time = datetime.now()
            
            markdown = generate_article(topic_name)
            article_duration = (datetime.now() - article_start_time).total_seconds()
            
            article_length = len(markdown) if markdown else 0
            word_count = len(markdown.split()) if markdown else 0
            
            print(f"✅ [GÉNÉRATION] Article généré avec succès!")
            print(f"📊 Statistiques de l'article:")
            print(f"   - Longueur: {article_length} caractères")
            print(f"   - Mots: {word_count} mots")
            print(f"   - Temps de génération: {article_duration:.2f} secondes")
            print(f"   - Aperçu: {markdown[:100]}..." if markdown else "   - Contenu vide")

            print(f"\n📝 [SAUVEGARDE] Insertion dans Supabase...")
            insert_start_time = datetime.now()
            
            insert_article_to_supabase(
                article_markdown=markdown,
                topic=topic_name
            )
            
            insert_duration = (datetime.now() - insert_start_time).total_seconds()
            print(f"📥 [SAUVEGARDE] Article sauvegardé avec succès!")
            print(f"⏱️ Temps de sauvegarde: {insert_duration:.2f} secondes")

            print(f"\n🔖 [MARQUAGE] Marquage du topic comme traité...")
            mark_topic_as_processed(topic_name)
            print(f"✅ [MARQUAGE] Topic marqué comme traité")
            
            # Statistiques de progression
            remaining_topics = total_topics - idx
            progress_percent = (idx / total_topics * 100)
            elapsed_time = (datetime.now() - start_time).total_seconds()
            avg_time_per_topic = elapsed_time / idx
            estimated_remaining_time = remaining_topics * avg_time_per_topic
            
            print(f"\n📊 STATISTIQUES DE PROGRESSION:")
            print(f"   - Traités: {idx}/{total_topics} ({progress_percent:.1f}%)")
            print(f"   - Restants: {remaining_topics}")
            print(f"   - Temps écoulé: {elapsed_time:.0f}s")
            print(f"   - Temps moyen par topic: {avg_time_per_topic:.1f}s")
            print(f"   - Temps estimé restant: {estimated_remaining_time:.0f}s")
            
            logging.info(f"SUCCESS | {topic_name} | ID: {topic_id} | user_id: {user_id} | words: {word_count} | duration: {article_duration:.2f}s")
            
        except Exception as e:
            print(f"❌ [ERREUR] Erreur lors du traitement de '{topic_name}':")
            print(f"   - Topic ID: {topic_id}")
            print(f"   - User ID: {user_id}")
            print(f"   - Erreur: {str(e)}")
            print(f"   - Heure: {datetime.now().strftime('%H:%M:%S')}")
            logging.error(f"FAILURE | {topic_name} | ID: {topic_id} | user_id: {user_id} | Error: {e}")

        generated_count += 1

        if generated_count >= limit:
            print(f"\n⛔️ LIMITE ATTEINTE: {limit} articles générés")
            break

    total_duration = (datetime.now() - start_time).total_seconds()
    print("\n" + "="*80)
    print("🏁 TRAITEMENT TERMINÉ")
    print("="*80)
    print(f"📊 RÉSULTATS FINAUX:")
    print(f"   - Articles générés: {generated_count}")
    print(f"   - Topics traités: {generated_count}/{total_topics}")
    print(f"   - Temps total: {total_duration:.0f}s ({total_duration/60:.1f}min)")
    print(f"   - Moyenne par article: {total_duration/generated_count:.1f}s")
    print(f"⏰ Fin du traitement: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
