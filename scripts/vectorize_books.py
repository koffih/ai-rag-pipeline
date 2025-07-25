from langchain_community.document_loaders import PyPDFLoader, UnstructuredEPubLoader, UnstructuredWordDocumentLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
import fitz  # PyMuPDF
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

CHROMA_DIR = "/home/koffi/rag_scripts/chroma_store"

# Configuration du logger
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'vectorization.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class DJVULoader:
    def __init__(self, filepath):
        self.filepath = filepath
    
    def load(self):
        documents = []
        try:
            # Essayer d'abord avec PyMuPDF
            doc = fitz.open(self.filepath)
            print(f"📖 DJVU ouvert avec PyMuPDF, {len(doc)} pages détectées")
            
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    if text.strip():  # Only add non-empty pages
                        documents.append(Document(
                            page_content=text,
                            metadata={"source": os.path.basename(self.filepath), "page": page_num + 1}
                        ))
                except Exception as e:
                    print(f"⚠️ Erreur page {page_num + 1}: {e}")
                    continue
            doc.close()
            
            if documents:
                print(f"✅ {len(documents)} pages DJVU extraites avec succès")
                return documents
                
        except Exception as e:
            print(f"❌ Erreur PyMuPDF DJVU : {e}")
        
        # Fallback: essayer d'extraire au moins quelques pages
        try:
            print("🔄 Tentative de fallback DJVU...")
            doc = fitz.open(self.filepath)
            text = ""
            max_pages = min(len(doc), 5)  # Limiter à 5 pages pour le fallback
            
            for page_num in range(max_pages):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    if page_text.strip():
                        text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
                except:
                    continue
            doc.close()
            
            if text.strip():
                documents.append(Document(
                    page_content=text,
                    metadata={"source": os.path.basename(self.filepath)}
                ))
                print(f"✅ Fallback DJVU réussi: {len(text)} caractères extraits")
                return documents
                
        except Exception as e2:
            print(f"❌ Fallback DJVU échoué: {e2}")
        
        print("❌ Impossible d'extraire le contenu DJVU")
        return documents

def get_loader(filepath):
    ext = filepath.lower().split('.')[-1]
    if ext == 'pdf':
        return PyPDFLoader(filepath)
    elif ext == 'epub':
        return UnstructuredEPubLoader(filepath)
    elif ext in ['docx', 'doc']:
        return UnstructuredWordDocumentLoader(filepath)
    elif ext == 'txt':
        return TextLoader(filepath)
    elif ext == 'djvu':
        return DJVULoader(filepath)
    elif ext == 'azw3':
        return DJVULoader(filepath)  # PyMuPDF peut aussi lire AZW3
    else:
        raise ValueError(f"Format non supporté : {ext}")

def vectorize_pdf(filepath):
    print(f"📄 Vectorisation de : {filepath}")
    start_time = datetime.now()
    try:
        # Chargement du document
        loader = get_loader(filepath)
        documents = loader.load()

        # Découpage du texte
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)

        # Ajout du nom du fichier en tant que métadonnée "source"
        filename = os.path.basename(filepath)
        for chunk in chunks:
            chunk.metadata["source"] = filename

        # Embeddings + insertion dans ChromaDB
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
        vectordb.add_documents(chunks)
        vectordb.persist()

        print(f"✅ {len(chunks)} chunks vectorisés pour {filename}")
        logging.info(f"SUCCESS | {filename} | {len(chunks)} chunks | Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')} | End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"❌ Erreur lors de la vectorisation de {filepath} : {e}")
        logging.error(f"FAILURE | {os.path.basename(filepath)} | Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python vectorize_books.py <filepath>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    vectorize_pdf(filepath)
