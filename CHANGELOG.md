# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pipeline RAG résilient avec gestion d'erreurs
- Support multi-format (PDF, EPUB, Audio, Images)
- Monitoring en temps réel
- Scripts d'installation automatique
- Documentation complète

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [1.0.0] - 2025-07-25

### Added
- Pipeline RAG complet avec vectorisation
- Génération automatique de topics
- Génération d'articles via LLM
- Support ChromaDB pour le stockage vectoriel
- Interface Supabase pour les données
- Scripts de monitoring et maintenance
- Documentation complète et guides d'installation
- Tests automatisés
- CI/CD avec GitHub Actions

### Features
- **Pipeline Résilient** : Gestion d'erreurs robuste avec retry automatique
- **Multi-format** : Support PDF, EPUB, MOBI, Audio, Images avec OCR
- **Performance** : Optimisé GPU/CPU avec monitoring temps réel
- **Auto-installation** : Script d'installation automatique
- **Monitoring** : Interface de suivi en temps réel

### Technical
- LangChain pour le framework RAG
- HuggingFace Embeddings (all-MiniLM-L6-v2)
- ChromaDB pour la base de données vectorielle
- Supabase pour le stockage des topics et articles
- PyTorch pour l'accélération GPU
- Watchdog pour la surveillance de fichiers

---
