# reset_db.py
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, r'C:\Users\conta\PycharmProjects\lagem\plateforme_parti')

# Changer de dossier
os.chdir(r'C:\Users\conta\PycharmProjects\lagem\plateforme_parti')

from app import app, db

with app.app_context():
    db.drop_all()
    db.create_all()
    print("✅ Base de données réinitialisée avec succès!")