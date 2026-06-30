import sqlite3
import os

# Recherche automatique de la base
db_path = None

for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".db"):
            db_path = os.path.join(root, file)
            break

if not db_path:
    print("❌ Aucune base SQLite trouvée.")
    exit()

print("✅ Base trouvée :", db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n===== STRUCTURE DE LA TABLE publications =====")

try:
    cursor.execute("PRAGMA table_info(publications)")
    colonnes = cursor.fetchall()

    if not colonnes:
        print("❌ La table publications n'existe pas.")
    else:
        for col in colonnes:
            print(
                f"Nom: {col[1]} | Type: {col[2]} | Nullable: {not col[3]} | Default: {col[4]}"
            )

except Exception as e:
    print("Erreur :", e)

print("\n===== DERNIÈRES PUBLICATIONS =====")

try:
    cursor.execute("SELECT * FROM publications LIMIT 5")
    rows = cursor.fetchall()

    if not rows:
        print("⚠️ Aucune publication enregistrée.")
    else:
        print(f"{len(rows)} publication(s) trouvée(s).")
        for row in rows:
            print(row)

except Exception as e:
    print("Erreur :", e)

conn.close()

print("\n✅ Diagnostic terminé.")