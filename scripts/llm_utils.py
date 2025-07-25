import os
import requests
from dotenv import load_dotenv
import time
import logging

load_dotenv()

# Configuration des API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def test_api_connectivity():
    """Test la connectivité des différentes API"""
    results = {}
    
    # Test DeepSeek
    try:
        response = requests.get("https://api.deepseek.com", timeout=5)
        results["deepseek"] = True
    except:
        results["deepseek"] = False
    
    # Test OpenAI
    try:
        response = requests.get("https://api.openai.com", timeout=5)
        results["openai"] = True
    except:
        results["openai"] = False
    
    return results

def generate_text_with_fallback(prompt, model="auto", temperature=0.7, max_tokens=500):
    """Génère du texte avec fallback automatique entre APIs"""
    
    # Test de connectivité
    connectivity = test_api_connectivity()
    
    # Priorité: DeepSeek -> OpenAI -> Local/Offline
    if connectivity.get("deepseek", False) and DEEPSEEK_API_KEY:
        try:
            return generate_text_deepseek(prompt, temperature, max_tokens)
        except Exception as e:
            print(f"[WARNING] DeepSeek échoué: {e}")
    
    if connectivity.get("openai", False) and OPENAI_API_KEY:
        try:
            return generate_text_openai(prompt, temperature, max_tokens)
        except Exception as e:
            print(f"[WARNING] OpenAI échoué: {e}")
    
    # Fallback vers génération locale/offline
    return generate_text_offline(prompt, max_tokens)

def generate_text_deepseek(prompt, temperature=0.7, max_tokens=500):
    """Génération via DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"DeepSeek API error: {response.status_code}")

def generate_text_openai(prompt, temperature=0.7, max_tokens=500):
    """Génération via OpenAI API"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"OpenAI API error: {response.status_code}")

def generate_text_offline(prompt, max_tokens=500):
    """Génération offline/locale de base"""
    print("[INFO] Utilisation du mode offline - génération basique")
    
    # Templates de base pour différents types de contenu
    if "article" in prompt.lower():
        return f"""# Article généré (Mode Offline)

## Introduction
Ce contenu a été généré en mode offline car les API externes ne sont pas disponibles.

## Contenu
Le sujet traité nécessite une recherche approfondie et une rédaction professionnelle.

## Conclusion
Pour une meilleure qualité, veuillez vérifier la connectivité internet et les clés API.

*Généré automatiquement en mode offline*
"""
    
    elif "topic" in prompt.lower():
        return """
- Concept principal
- Idée secondaire
- Élément important
- Notion clé
- Principe fondamental
"""
    
    else:
        return f"""Contenu généré en mode offline pour: {prompt[:100]}...

Ce contenu de base nécessite une révision manuelle."""

# Fonction compatible avec l'ancien système
def generate_text(prompt, model="auto", temperature=0.7, max_tokens=500):
    """Fonction principale compatible avec l'ancien système"""
    return generate_text_with_fallback(prompt, model, temperature, max_tokens)

