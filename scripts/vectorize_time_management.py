from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 📁 Chemin vers les fichiers PDF
DATA_PATH = "/mnt/c/Users/koffi/Documents/RAG/books/time_management"

# 📄 Charger tous les fichiers PDF
documents = []
for filename in os.listdir(DATA_PATH):
    if filename.endswith(".pdf"):
        print(f"📥 Chargement de : {filename}")
        loader = PyPDFLoader(os.path.join(DATA_PATH, filename))
        documents.extend(loader.load())

# ✂️ Split en chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = splitter.split_documents(documents)

print(f"🔍 {len(chunks)} chunks générés pour l'indexation")

# 🧠 Embeddings HuggingFace local
embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# 🗃️ Créer la base Chroma (persist automatique)
db = Chroma.from_documents(chunks, embedding, persist_directory="./chroma_db/time_management")

print("✅ Vectorisation locale terminée avec HuggingFace + ChromaDB")
