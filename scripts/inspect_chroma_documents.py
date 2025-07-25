from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from collections import Counter
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 🔁 Mets ici ton chemin vers la base vectorielle
CHROMA_DIR = "/home/koffi/rag_scripts/chroma_store"

embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_model)

# Récupère tous les documents
docs = vectorstore.get()
metadatas = docs["metadatas"]

# 🧪 Affiche les 5 premières métadonnées brutes
print("🔍 Extrait brut des 5 premières métadonnées :\n")
for i, meta in enumerate(metadatas[:5]):
    print(f"{i+1}. {meta}")


