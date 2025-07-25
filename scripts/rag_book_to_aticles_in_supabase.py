import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_URL = f"https://{GITHUB_TOKEN}@github.com/koffih/rag_book_to_articles.git"
PROJECT_PATH = "/home/koffi/rag_project"
USER_EMAIL = "koffih@gmail.com"
USER_NAME = "Automated Script"

def run_command(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Erreur commande: {command}")
        print(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)
    else:
        print(result.stdout)
    return result.stdout.strip()

def setup_git():
    run_command("git config user.name '{}'".format(USER_NAME), cwd=PROJECT_PATH)
    run_command("git config user.email '{}'".format(USER_EMAIL), cwd=PROJECT_PATH)

def initialize_repo():
    if not os.path.exists(os.path.join(PROJECT_PATH, ".git")):
        print("🚩 Initialisation du dépôt Git...")
        run_command("git init", cwd=PROJECT_PATH)

def add_remote():
    remotes = run_command("git remote", cwd=PROJECT_PATH)
    if "origin" not in remotes:
        print("🔗 Ajout de l'origine distante...")
        run_command(f"git remote add origin {REPO_URL}", cwd=PROJECT_PATH)
    else:
        print("🔄 Mise à jour URL remote existante...")
        run_command(f"git remote set-url origin {REPO_URL}", cwd=PROJECT_PATH)

def commit_and_push():
    status = run_command("git status --porcelain", cwd=PROJECT_PATH)
    if not status:
        print("✅ Aucun changement détecté.")
        return

    print("📌 Ajout et commit des changements...")
    run_command("git add .", cwd=PROJECT_PATH)

    commit_msg = f"Auto-commit {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    run_command(f"git commit -m '{commit_msg}'", cwd=PROJECT_PATH)

    print("📡 Push vers GitHub...")
    run_command("git branch -M main", cwd=PROJECT_PATH)
    run_command("git push origin main --force", cwd=PROJECT_PATH)
    print("✅ Push terminé avec succès !")

def main():
    print(f"🚀 Push automatique pour le projet situé dans: {PROJECT_PATH}")
    initialize_repo()
    setup_git()
    add_remote()
    commit_and_push()

if __name__ == "__main__":
    main()
