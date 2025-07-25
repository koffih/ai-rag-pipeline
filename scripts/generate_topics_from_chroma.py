from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

CHROMA_DIR = "/mnt/c/Users/koffi/Documents/RAG/books/time_management"
embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
db = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_function)

print(f"Nombre de documents dans la base : {db._collection.count()}")
query = "Liste toutes les techniques, modèles, conseils et principes liés à la gestion du temps."
results = db.similarity_search(query, k=100)

with open("topics_raw.txt", "w", encoding="utf-8") as f:
    for i, doc in enumerate(results):
        f.write(f"\n--- Résultat #{i+1} ---\n")
        f.write(doc.page_content + "\n")
