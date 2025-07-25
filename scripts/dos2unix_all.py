import os
import subprocess

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

py_files = []
for dirpath, dirnames, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith('.py'):
            full_path = os.path.join(dirpath, filename)
            py_files.append(full_path)

print(f"[INFO] {len(py_files)} fichiers Python trouvés.")

for f in py_files:
    print(f"[INFO] Conversion dos2unix : {f}")
    try:
        subprocess.run(["dos2unix", f], check=True)
    except Exception as e:
        print(f"[ERROR] Erreur sur {f} : {e}")

print("[INFO] Conversion dos2unix terminée sur tous les fichiers .py.") 