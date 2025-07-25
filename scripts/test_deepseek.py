from rag_scripts.llm_utils import generate_text

if __name__ == "__main__":
    print("[TEST] Appel DeepSeek avec prompt minimal...")
    try:
        result = generate_text("Bonjour, peux-tu générer une liste de 3 topics sur la gestion du temps ?", model="deepseek-chat", temperature=0.3, max_tokens=100)
        print("[SUCCESS] Réponse DeepSeek :")
        print(result)
    except Exception as e:
        print(f"[ERROR] DeepSeek API test failed: {e}") 