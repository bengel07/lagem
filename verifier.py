# Ajouter le chemin du projet
import sys
import os

sys.path.insert(0, r'C:\Users\conta\PycharmProjects\lagem\plateforme_parti')

# Changer de dossier
os.chdir(r'C:\Users\conta\PycharmProjects\lagem\plateforme_parti')

from app import app, db, User

with app.app_context():
    admin = User.query.filter_by(email='admin@parti.ht').first()
    if admin:
        print(f"Admin trouvé: {admin.email}")
        print(f"Mot de passe hashé: {admin.password}")
    else:
        print("Admin non trouvé!")