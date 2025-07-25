# clean_topics.py

INPUT_FILE = "topics_raw.txt"
OUTPUT_FILE = "topics_cleaned.txt"

def is_useless_line(line):
    line = line.strip()
    return (
        not line
        or line.startswith("---")
        or line.lower().startswith("index")
        or line.replace("–", "").replace("-", "").replace(",", "").isdigit()
        or len(line.strip()) <= 2
    )

def clean_and_group_topics(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as infile:
        lines = infile.readlines()

    topics = []
    current = []

    for line in lines:
        line = line.strip()
        if is_useless_line(line):
            continue
        # Nouvelle entrée si ligne commence par majuscule sans ponctuation en fin
        if line and line[0].isupper() and not line.endswith((",", ".", ":", ";")):
            if current:
                full = " ".join(current).strip()
                if len(full.split()) > 3:
                    topics.append(full)
                current = []
        current.append(line)

    if current:
        full = " ".join(current).strip()
        if len(full.split()) > 3:
            topics.append(full)

    with open(output_file, "w", encoding="utf-8") as outfile:
        for topic in topics:
            outfile.write(topic + "\n")

    print(f"✅ Fichier nettoyé généré avec {len(topics)} topics : {output_file}")

if __name__ == "__main__":
    clean_and_group_topics(INPUT_FILE, OUTPUT_FILE)
