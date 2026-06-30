from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

import re

db = SQLAlchemy()


# Modèles de base de données
class Departement(db.Model):
    __tablename__ = 'departements'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(2), unique=True, nullable=False)
    chef_lieu = db.Column(db.String(50))



    def to_dict(self):
        return {'id': self.id, 'nom': self.nom, 'code': self.code}


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    departement_id = db.Column(db.Integer, db.ForeignKey('departements.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    membre = db.relationship('Membre', backref='utilisateur', uselist=False)




class Publication(db.Model):
    __tablename__ = 'publications'
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    contenu = db.Column(db.Text, nullable=False)

    categorie = db.Column(db.String(50))

    # image de la publication
    image = db.Column(db.String(255))

    video = db.Column(db.String(500))  # ← AJOUTER CETTE LIGNE

    type = db.Column(db.String(20), default='general')

    # nom du sponsor
    sponsor = db.Column(db.String(255))

    # lien externe
    lien = db.Column(db.String(500))

    departement_id = db.Column(db.Integer, db.ForeignKey('departements.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_expiration = db.Column(db.DateTime)

    actif = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref='publications')
    departement = db.relationship('Departement', backref='publications')



# Ajoutez ces modèles après le modèle Departement

class Commune(db.Model):
    __tablename__ = 'communes'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    departement_id = db.Column(db.Integer, db.ForeignKey('departements.id'), nullable=False)

    departement = db.relationship('Departement', backref='communes')
    sections = db.relationship('SectionCommunale', backref='commune_parent', lazy=True)

class SectionCommunale(db.Model):
    __tablename__ = 'sections_communales'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    commune_id = db.Column(db.Integer, db.ForeignKey('communes.id'), nullable=False)



    # commune = db.relationship('Commune', backref='sections_list')


# Mettez à jour le modèle Membre pour ajouter commune_id et section_id
class Membre(db.Model):
    __tablename__ = 'membres'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nif = db.Column(db.String(20), unique=True, nullable=False)
    cin = db.Column(db.String(20), unique=True, nullable=False)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)

    sexe = db.Column(db.String(1))  # M ou F
    date_naissance = db.Column(db.Date)  # ← NOUVEAU

    # Documents
    cin_recto = db.Column(db.String(255))  # ← NOUVEAU
    cin_verso = db.Column(db.String(255))  # ← NOUVEAU
    nif_recto = db.Column(db.String(255))  # ← NOUVEAU
    nif_verso = db.Column(db.String(255))  # ← NOUVEAU
    photo = db.Column(db.String(255))  # ← NOUVEAU

    competences = db.Column(db.Text)  # ← NOUVEAU
    domaine = db.Column(db.String(100))  # ← NOUVEAU

    # Engagement
    engagement = db.Column(db.String(50), default='simple_membre')  # ← NOUVEAU

    # Contact urgence
    contact_nom = db.Column(db.String(100))  # ← NOUVEAU
    contact_telephone = db.Column(db.String(20))  # ← NOUVEAU

    type_membre=  db.Column(db.String(20), default='local')

    pays_residence = db.Column(db.String(100), nullable=True)  # Pour diaspora
    ville_residence = db.Column(db.String(100), nullable=True)  # Pour diaspora


    ville_natale = db.Column(db.String(100))
    adresse_actuelle = db.Column(db.Text)
    temps_adresse = db.Column(db.Integer)
    telephone = db.Column(db.String(20))
    occupation = db.Column(db.String(100))
    niveau_etude = db.Column(db.String(50))
    nationalite = db.Column(db.String(50), default='Haïtienne')
    nb_enfants = db.Column(db.Integer, default=0)
    status_matrimonial = db.Column(db.String(20))
    statut = db.Column(db.String(20), default='en_attente')
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)
    departement_id = db.Column(db.Integer, db.ForeignKey('departements.id'))
    commune_id = db.Column(db.Integer, db.ForeignKey('communes.id'), nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections_communales.id'), nullable=True)

    departement = db.relationship('Departement', backref='membres')
    commune = db.relationship('Commune', backref='membres')
    section = db.relationship('SectionCommunale', backref='membres')


class Pays(db.Model):
    __tablename__ = 'pays'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(3), nullable=False)
    continent = db.Column(db.String(50))



class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    expediteur_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    destinataire_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    lu = db.Column(db.Boolean, default=False)
    lu_date = db.Column(db.DateTime, nullable=True)
    supprime_par_expediteur = db.Column(db.Boolean, default=False)
    supprime_par_destinataire = db.Column(db.Boolean, default=False)
    date_envoi = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    expediteur = db.relationship('User', foreign_keys=[expediteur_id], backref='messages_envoyes')
    destinataire = db.relationship('User', foreign_keys=[destinataire_id], backref='messages_recus')

    def __init__(self, expediteur_id, destinataire_id, contenu):
        self.expediteur_id = expediteur_id
        self.destinataire_id = destinataire_id
        self.contenu = contenu
        self.lu = False
        self.date_envoi = datetime.utcnow()

    def marquer_comme_lu(self):
        """Marquer le message comme lu"""
        if not self.lu:
            self.lu = True
            self.lu_date = datetime.utcnow()
            return True
        return False

    def supprimer_pour_expediteur(self):
        """Supprimer le message pour l'expéditeur"""
        self.supprime_par_expediteur = True
        return self._verifier_suppression_complete()

    def supprimer_pour_destinataire(self):
        """Supprimer le message pour le destinataire"""
        self.supprime_par_destinataire = True
        return self._verifier_suppression_complete()

    def _verifier_suppression_complete(self):
        """Vérifier si le message peut être complètement supprimé"""
        if self.supprime_par_expediteur and self.supprime_par_destinataire:
            db.session.delete(self)
            return True
        return False

    def repondre(self, contenu_reponse):
        """Créer une réponse à ce message"""
        return Message(
            expediteur_id=self.destinataire_id,
            destinataire_id=self.expediteur_id,
            contenu=contenu_reponse
        )

    def get_temps_ecoule(self):
        """Obtenir le temps écoulé depuis l'envoi du message"""
        from datetime import datetime
        now = datetime.utcnow()
        diff = now - self.date_envoi

        if diff.days > 0:
            return f"Il y a {diff.days} jour(s)"
        elif diff.seconds > 3600:
            heures = diff.seconds // 3600
            return f"Il y a {heures} heure(s)"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"Il y a {minutes} minute(s)"
        else:
            return "À l'instant"

    def to_dict(self):
        """Convertir le message en dictionnaire pour API"""
        return {
            'id': self.id,
            'expediteur_id': self.expediteur_id,
            'expediteur_email': self.expediteur.email if self.expediteur else None,
            'expediteur_nom': self.expediteur.membre.nom if self.expediteur and self.expediteur.membre else None,
            'destinataire_id': self.destinataire_id,
            'destinataire_email': self.destinataire.email if self.destinataire else None,
            'contenu': self.contenu,
            'lu': self.lu,
            'lu_date': self.lu_date.strftime('%d/%m/%Y %H:%M') if self.lu_date else None,
            'date_envoi': self.date_envoi.strftime('%d/%m/%Y %H:%M'),
            'temps_ecoule': self.get_temps_ecoule()
        }

    def __repr__(self):
        return f'<Message {self.id}: {self.expediteur_id} -> {self.destinataire_id}>'