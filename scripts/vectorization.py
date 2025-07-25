from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

# Dossier Chroma existant
CHROMA_DIR = "/mnt/c/Users/koffi/Documents/RAG/books/time_management"

# Embeddings
embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def vectorize_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"❌ Fichier introuvable : {pdf_path}")
        return

    print(f"📥 Traitement de : {pdf_path}")

    # Chargement et découpage du PDF
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    if not docs:
        print(f"⚠️ Aucun contenu extrait du PDF : {pdf_path}")
        return

    # Vectorisation et insertion dans la base
    db = Chroma(persist_directory=CHROMA_DIR, embedding_function=embedding_function)
    db.add_documents(docs)

    print(f"✅ Vectorisation terminée pour : {pdf_path}")
