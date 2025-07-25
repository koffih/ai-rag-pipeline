# 🚀 AI RAG Pipeline

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/koffi/ai-rag-pipeline.svg)](https://github.com/koffi/ai-rag-pipeline/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/koffi/ai-rag-pipeline.svg)](https://github.com/koffi/ai-rag-pipeline/network)
[![GitHub issues](https://img.shields.io/github/issues/koffi/ai-rag-pipeline.svg)](https://github.com/koffi/ai-rag-pipeline/issues)

> Pipeline RAG (Retrieval-Augmented Generation) intelligent et résilient pour le traitement automatique de documents et la génération d'articles

## 🌟 Fonctionnalités

- **🔄 Pipeline Résilient** : Gestion d'erreurs robuste avec retry automatique
- **📄 Multi-format** : Support PDF, EPUB, Audio, Images, Documents
- **🤖 IA Intégrée** : Vectorisation, génération de topics et d'articles
- **⚡ Performance** : Optimisé GPU/CPU avec monitoring temps réel
- **🔧 Auto-installation** : Script d'installation automatique
- **📊 Monitoring** : Interface de suivi en temps réel

## 🚀 Installation Rapide

### Prérequis
- Python 3.10+
- GPU NVIDIA (recommandé) ou CPU
- 8GB+ RAM
- 50GB+ espace disque

### Installation Automatique
```bash
# Cloner le repository
git clone https://github.com/koffi/ai-rag-pipeline.git
cd ai-rag-pipeline

# Installation automatique
./install.sh

# Configuration
cp .env.example .env
nano .env  # Ajouter vos clés API

# Test
python test_installation.py
```

## 🎯 Utilisation

### Pipeline Unifié (Recommandé)
```bash
# Lancer le pipeline complet
python run_unified_resilient_pipeline.py

# Monitoring en temps réel
python monitor_pipeline_realtime.py
```

### Traitement Manuel
```bash
# Placer vos fichiers dans extractable_files/ ou watched_inbox/
python scripts/auto_pipeline_resilient.py --one
```

## 📊 Types de Fichiers Supportés

| Type | Formats | Pipeline |
|------|---------|----------|
| **Documents** | PDF, TXT, DOCX, RTF, ODT, HTML | extractable_files |
| **eBooks** | EPUB, MOBI, AZW, AZW3, FB2, LIT, PDB | watched_inbox |
| **Audio** | MP3, WAV, M4A, FLAC, OGG, AAC | watched_inbox |
| **Images** | JPG, PNG, TIFF, BMP (OCR) | watched_inbox |

## 🏗️ Architecture

```
ai-rag-pipeline/
├── scripts/                    # Scripts du pipeline
│   ├── auto_pipeline_resilient.py
│   ├── vectorize_books.py
│   ├── topic_generator.py
│   └── generate_articles_from_supabase.py
├── docs/                       # Documentation
├── tests/                      # Tests automatisés
├── examples/                   # Exemples d'utilisation
├── data/                       # Données (topics, etc.)
├── config/                     # Configuration
└── logs/                       # Logs
```

## 🔧 Configuration

### Variables d'environnement (.env)
```bash
# Supabase (obligatoire)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_API_KEY=your_supabase_anon_key

# OpenAI (optionnel)
OPENAI_API_KEY=sk-your_openai_key

# HuggingFace (optionnel)
HUGGINGFACE_API_KEY=hf_your_huggingface_key
```

## 📈 Performance

| Hardware | Fichiers/heure | Mémoire |
|----------|----------------|---------|
| **RTX 4090** | 50-100 | 24GB VRAM |
| **RTX 3080** | 30-60 | 10GB VRAM |
| **CPU 8 cores** | 10-20 | 16GB RAM |

## 🛠️ Développement

### Installation pour développement
```bash
git clone https://github.com/koffi/ai-rag-pipeline.git
cd ai-rag-pipeline
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Tests
```bash
# Tests unitaires
python -m pytest tests/

# Tests d'intégration
python test_installation.py

# Tests de performance
python tests/test_performance.py
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📝 Changelog

Voir [CHANGELOG.md](CHANGELOG.md) pour l'historique des versions.

## 📄 Licence

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

- [LangChain](https://langchain.com/) pour le framework RAG
- [ChromaDB](https://www.trychroma.com/) pour la base de données vectorielle
- [HuggingFace](https://huggingface.co/) pour les modèles d'IA
- [Supabase](https://supabase.com/) pour la base de données

## 📞 Support

- 📖 [Documentation](docs/)
- 🐛 [Issues](https://github.com/koffi/ai-rag-pipeline/issues)
- 💬 [Discussions](https://github.com/koffi/ai-rag-pipeline/discussions)
- 📧 Email: support@ai-rag-pipeline.com

---

⭐ **Si ce projet vous aide, n'oubliez pas de le star !**

**Créé avec ❤️ par Koffi**
