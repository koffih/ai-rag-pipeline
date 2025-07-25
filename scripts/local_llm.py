# local_llm.py

from rag_scripts.llm_utils import generate_text

def generate_article(topic: str, context: str = "", max_tokens: int = 1024) -> str:
    context_str = f"Voici le contexte à utiliser :\n{context}" if context else ""
    prompt = f"""
Tu es un rédacteur expert. Rédige un article en français sur le sujet suivant : '{topic}'.
{context_str}
L'article doit être structuré, inspirant, et écrit en français, avec une introduction, des conseils pratiques, des exemples, et une conclusion.
IMPORTANT : Même si le contexte ou le sujet est en anglais ou dans une autre langue, la rédaction doit être intégralement en français.
"""
    return generate_text(prompt, model="deepseek-chat", temperature=0.7, max_tokens=max_tokens)

