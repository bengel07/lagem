from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from plateforme_parti.models import Membre, Message, Publication, Departement, User, Commune, SectionCommunale, db

import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_ici_changez_la'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parti_politique.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['UPLOAD_FOLDER'] = os.path.join(
    BASE_DIR,
    'static',
    'uploads'
)
os.makedirs(
    os.path.join(app.config['UPLOAD_FOLDER'], 'publications'),
    exist_ok=True
)

# Créer UNE SEULE instance de SQLAlchemy

db.init_app(app)

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page'

# ============ CRÉATION AUTO DE L'ADMIN ============
with app.app_context():
    db.create_all()  # Crée les tables si elles n'existent pas

    admin = User.query.filter_by(email='admin@parti.ht').first()
    if not admin:
        admin_password = bcrypt.generate_password_hash('Admin123!').decode('utf-8')
        admin = User(email='admin@parti.ht', password=admin_password, role='admin_general')
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin créé: admin@parti.ht / Admin123!")
    else:
        print("✅ Admin déjà existant")



# IMPORTANT: Attacher db aux modèles AVANT de les importer
import sys
sys.modules['__main__'].db = db

# Maintenant importez les modèles

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Routes
@app.route('/')
def index():
    publications = Publication.query.filter_by(type='general').order_by(Publication.date_creation.desc()).limit(
        10).all()
    departements = Departement.query.all()
    now = datetime.utcnow()  # ← AJOUTEZ CETTE LIGNE
    return render_template('index.html', publications=publications, departements=departements, now=now)  # ← AJOUTER now)





@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        try:
            # Récupérer le type de membre
            type_membre = request.form.get('type_membre', 'local')

            # Vérifier si email existe déjà
            if User.query.filter_by(email=request.form.get('email')).first():
                flash('Cet email est déjà utilisé', 'danger')
                return redirect(url_for('inscription'))

            # Vérifier CIN unique (NIF optionnel donc pas obligatoire)
            if Membre.query.filter_by(cin=request.form.get('cin')).first():
                flash('Ce CIN est déjà utilisé', 'danger')
                return redirect(url_for('inscription'))

            # Création de l'utilisateur
            hashed_password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
            user = User(
                email=request.form.get('email'),
                password=hashed_password,
                role='membre'
            )
            db.session.add(user)
            db.session.flush()

            # Gestion des fichiers uploadés
            def save_uploaded_file(file, subfolder):
                if file and file.filename:
                    filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
                    os.makedirs(upload_path, exist_ok=True)
                    file.save(os.path.join(upload_path, filename))
                    return f"{subfolder}/{filename}"
                return None

            cin_recto = save_uploaded_file(request.files.get('cin_recto'), 'cin')
            cin_verso = save_uploaded_file(request.files.get('cin_verso'), 'cin')
            nif_recto = save_uploaded_file(request.files.get('nif_recto'), 'nif')
            nif_verso = save_uploaded_file(request.files.get('nif_verso'), 'nif')
            photo = save_uploaded_file(request.files.get('photo'), 'photos')

            # Création du membre avec tous les champs
            membre = Membre(
                user_id=user.id,
                nif=request.form.get('nif') or None,
                cin=request.form.get('cin'),
                nom=request.form.get('nom'),
                prenom=request.form.get('prenom'),
                sexe=request.form.get('sexe'),
                date_naissance=datetime.strptime(request.form.get('date_naissance'), '%Y-%m-%d').date() if request.form.get('date_naissance') else None,
                ville_natale=request.form.get('ville_natale'),
                nationalite=request.form.get('nationalite', 'Haïtienne'),
                nb_enfants=int(request.form.get('nb_enfants', 0)),
                status_matrimonial=request.form.get('status_matrimonial'),
                adresse_actuelle=request.form.get('adresse_actuelle'),
                temps_adresse=int(request.form.get('temps_adresse', 0)),
                departement_id=int(request.form.get('departement_id',0)),
                commune_id=int(request.form.get('commune_id')) if request.form.get('commune_id') else None,
                section_id=int(request.form.get('section_id')) if request.form.get('section_id') else None,
                telephone=request.form.get('telephone'),
                occupation=request.form.get('occupation'),
                niveau_etude=request.form.get('niveau_etude'),
                competences=request.form.get('competences'),
                domaine=request.form.get('domaine'),
                engagement=request.form.get('engagement', 'simple_membre'),
                contact_nom=request.form.get('contact_nom'),
                contact_telephone=request.form.get('contact_telephone'),
                cin_recto=cin_recto,
                cin_verso=cin_verso,
                nif_recto=nif_recto,
                nif_verso=nif_verso,
                photo=photo,
                statut='en_attente',

                type_membre=type_membre,
                pays_residence=request.form.get('pays_residence') if type_membre == 'diaspora' else None,
                ville_residence=request.form.get('ville_residence') if type_membre == 'diaspora' else None,

            )
            db.session.add(membre)
            db.session.commit()

            flash('Inscription réussie! En attente de validation par votre admin départemental.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'inscription: {str(e)}', 'danger')
            return redirect(url_for('inscription'))

    departements = Departement.query.all()
    return render_template('inscription.html', departements=departements)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)

            if user.role == 'admin_general':
                return redirect(url_for('dashboard_admin_general'))
            elif user.role == 'admin_depart':
                return redirect(url_for('dashboard_admin_depart'))
            else:
                return redirect(url_for('espace_membre'))
        else:
            flash('Email ou mot de passe incorrect', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('index'))


@app.route('/admin/general')
@login_required
def dashboard_admin_general():
    if current_user.role != 'admin_general':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))

    stats = {
        'total_membres': Membre.query.count(),
        'membres_actifs': Membre.query.filter_by(statut='actif').count(),
        'membres_attente': Membre.query.filter_by(statut='en_attente').count(),
        'total_publications': Publication.query.count(),
        'membres_par_departement': []
    }

    for dept in Departement.query.all():
        stats['membres_par_departement'].append({
            'departement': dept.nom,
            'total': Membre.query.filter_by(departement_id=dept.id).count(),
            'actifs': Membre.query.filter_by(departement_id=dept.id, statut='actif').count(),
            'en_attente': Membre.query.filter_by(departement_id=dept.id, statut='en_attente').count()
        })

    admins_depart = User.query.filter_by(role='admin_depart').all()
    departements = Departement.query.all()
    membres_attente = Membre.query.filter_by(statut='en_attente').all()

    return render_template('dashboard_admin_general.html', stats=stats, admins_depart=admins_depart,
                           departements=departements,membres_attente=membres_attente )


@app.route('/admin/creer-admin-depart', methods=['POST'])
@login_required
def creer_admin_depart():
    if current_user.role != 'admin_general':
        flash('Non autorisé', 'danger')
        return redirect(url_for('index'))

    email = request.form.get('email')
    departement_id = request.form.get('departement_id')
    password = request.form.get('password')

    if User.query.filter_by(email=email).first():
        flash('Cet email est déjà utilisé', 'danger')
        return redirect(url_for('dashboard_admin_general'))

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    admin = User(
        email=email,
        password=hashed_password,
        role='admin_depart',
        departement_id=departement_id
    )
    db.session.add(admin)
    db.session.commit()

    flash(f'Admin départemental créé avec succès', 'success')
    return redirect(url_for('dashboard_admin_general'))



@app.route('/admin/publication', methods=['POST'])
@login_required
def publication_generale():

    if current_user.role not in ['admin_general', 'admin_depart']:
        flash('Non autorisé', 'danger')
        return redirect(url_for('index'))

    titre = request.form.get('titre')
    contenu = request.form.get('contenu')
    video = request.form.get('video')  # ← AJOUTER

    # annonce ou commercial
    pub_type = request.form.get('pub_type', 'annonce')

    # durée en jours
    duree = int(request.form.get('duree', 30))

    sponsor = request.form.get('sponsor')
    lien = request.form.get('lien')

    # Upload image
    image_name = None
    image = request.files.get('image')

    if image and image.filename:
        filename = secure_filename(image.filename)

        image_name = f"{int(datetime.utcnow().timestamp())}_{filename}"

        image.save(
            os.path.join(
                app.config['UPLOAD_FOLDER'],
                'publications',
                image_name
            )
        )

    publication = Publication(
        titre=titre,
        contenu=contenu,

        # général, départemental ou commercial
        type=(
            'general'
            if current_user.role == 'admin_general'
            else 'departemental'
        ),

        categorie=pub_type,  # annonce ou commercial

        video=video,  # ← AJOUTER

        user_id=current_user.id,

        departement_id=(
            current_user.departement_id
            if current_user.role == 'admin_depart'
            else None
        ),

        sponsor=sponsor,
        lien=lien,
        image=image_name,

        date_creation=datetime.utcnow(),

        date_expiration=datetime.utcnow() + timedelta(days=duree),

        actif=True
    )

    db.session.add(publication)
    db.session.commit()

    flash('Publication ajoutée avec succès', 'success')

    if current_user.role == 'admin_general':
        return redirect(url_for('dashboard_admin_general'))

    return redirect(url_for('dashboard_admin_depart'))


@app.route('/admin/departement')
@login_required
def dashboard_admin_depart():
    if current_user.role != 'admin_depart':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))

    membres = Membre.query.filter_by(departement_id=current_user.departement_id).all()
    publications = Publication.query.filter(
        (Publication.type == 'general') |
        ((Publication.type == 'departemental') & (Publication.departement_id == current_user.departement_id))
    ).order_by(Publication.date_creation.desc()).all()

    membres_attente = Membre.query.filter_by(departement_id=current_user.departement_id, statut='en_attente').all()

    stats = {
        'total': len(membres),
        'actifs': len([m for m in membres if m.statut == 'actif']),
        'en_attente': len([m for m in membres if m.statut == 'en_attente'])
    }

    departement = Departement.query.get(current_user.departement_id)

    return render_template('dashboard_admin_depart.html',
                           membres=membres,
                           membres_attente=membres_attente,
                           publications=publications,
                           stats=stats,
                           departement=departement)


@app.route('/admin/valider-membre/<int:membre_id>')
@login_required
def valider_membre(membre_id):
    if current_user.role not in ['admin_general', 'admin_depart']:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))

    membre = Membre.query.get_or_404(membre_id)

    if current_user.role == 'admin_depart' and membre.departement_id != current_user.departement_id:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('dashboard_admin_depart'))

    membre.statut = 'actif'
    db.session.commit()

    flash(f'Membre {membre.nom} {membre.prenom} validé avec succès', 'success')

    if current_user.role == 'admin_general':
        return redirect(url_for('dashboard_admin_general'))
    else:
        return redirect(url_for('dashboard_admin_depart'))


@app.route('/admin/suspendre-membre/<int:membre_id>')
@login_required
def suspendre_membre(membre_id):
    if current_user.role not in ['admin_general', 'admin_depart']:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))

    membre = Membre.query.get_or_404(membre_id)

    if current_user.role == 'admin_depart' and membre.departement_id != current_user.departement_id:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('dashboard_admin_depart'))

    membre.statut = 'suspendu'
    db.session.commit()

    flash(f'Membre {membre.nom} {membre.prenom} suspendu', 'warning')

    if current_user.role == 'admin_general':
        return redirect(url_for('dashboard_admin_general'))
    else:
        return redirect(url_for('dashboard_admin_depart'))


@app.route('/membre/espace')
@login_required
def espace_membre():
    if current_user.role != 'membre':
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))

    membre = Membre.query.filter_by(user_id=current_user.id).first()

    if not membre:
        flash('Profil membre non trouvé', 'danger')
        return redirect(url_for('logout'))

    # Publications (générales + départementales)
    publications = Publication.query.filter(
        (Publication.type == 'general') |
        ((Publication.type == 'departemental') & (Publication.departement_id == membre.departement_id))
    ).order_by(Publication.date_creation.desc()).all()

    # Messages reçus (avec eager loading pour éviter les N+1 queries)
    messages_recus = Message.query.filter_by(destinataire_id=current_user.id) \
        .options(db.joinedload(Message.expediteur).joinedload(User.membre)) \
        .order_by(Message.date_envoi.desc()).all()

    # Messages envoyés
    messages_envoyes = Message.query.filter_by(expediteur_id=current_user.id) \
        .options(db.joinedload(Message.destinataire).joinedload(User.membre)) \
        .order_by(Message.date_envoi.desc()).all()

    # Autres membres actifs (pour messagerie)
    autres_membres = Membre.query.filter(
        Membre.id != membre.id,
        Membre.statut == 'actif'
    ).options(db.joinedload(Membre.user), db.joinedload(Membre.commune), db.joinedload(Membre.departement)).limit(
        50).all()

    return render_template('espace_membre.html',
                           membre=membre,
                           publications=publications,
                           messages_recus=messages_recus,
                           messages_envoyes=messages_envoyes,
                           autres_membres=autres_membres)


@app.route('/membre/envoyer-message', methods=['POST'])
@login_required
def envoyer_message():
    if current_user.role != 'membre':
        flash('Non autorisé', 'danger')
        return redirect(url_for('index'))

    destinataire_id = request.form.get('destinataire_id')
    contenu = request.form.get('contenu')

    if not contenu or not destinataire_id:
        flash('Message ou destinataire manquant', 'danger')
        return redirect(url_for('espace_membre'))

    message = Message(
        expediteur_id=current_user.id,
        destinataire_id=destinataire_id,
        contenu=contenu
    )
    db.session.add(message)
    db.session.commit()

    flash('Message envoyé avec succès', 'success')
    return redirect(url_for('espace_membre'))


# Routes API pour les messages
@app.route('/api/messages/non_lus')
@login_required
def api_messages_non_lus():
    """API pour obtenir le nombre de messages non lus"""
    count = Message.query.filter_by(
        destinataire_id=current_user.id,
        lu=False,
        supprime_par_destinataire=False
    ).count()
    return jsonify({'count': count})


@app.route('/api/messages/recus')
@login_required
def api_messages_recus():
    """API pour obtenir les messages reçus (JSON)"""
    messages = Message.query.filter_by(
        destinataire_id=current_user.id,
        supprime_par_destinataire=False
    ).order_by(Message.date_envoi.desc()).all()
    return jsonify([msg.to_dict() for msg in messages])


@app.route('/api/messages/envoyes')
@login_required
def api_messages_envoyes():
    """API pour obtenir les messages envoyés (JSON)"""
    messages = Message.query.filter_by(
        expediteur_id=current_user.id,
        supprime_par_expediteur=False
    ).order_by(Message.date_envoi.desc()).all()
    return jsonify([msg.to_dict() for msg in messages])


@app.route('/message/supprimer/<int:message_id>', methods=['POST'])
@login_required
def supprimer_message(message_id):
    """Supprimer un message (pour l'utilisateur courant)"""
    message = Message.query.get_or_404(message_id)

    if message.expediteur_id == current_user.id:
        message.supprimer_pour_expediteur()
        flash('Message supprimé', 'success')
    elif message.destinataire_id == current_user.id:
        message.supprimer_pour_destinataire()
        flash('Message supprimé', 'success')
    else:
        flash('Action non autorisée', 'danger')
        return redirect(url_for('espace_membre'))

    db.session.commit()
    return redirect(url_for('espace_membre'))


@app.route('/message/repondre/<int:message_id>', methods=['GET', 'POST'])
@login_required
def repondre_message(message_id):
    """Répondre à un message"""
    message_original = Message.query.get_or_404(message_id)

    # Vérifier que l'utilisateur est le destinataire du message original
    if message_original.destinataire_id != current_user.id:
        flash('Vous ne pouvez pas répondre à ce message', 'danger')
        return redirect(url_for('espace_membre'))

    if request.method == 'POST':
        contenu = request.form.get('contenu')
        if contenu:
            nouveau_message = message_original.repondre(contenu)
            db.session.add(nouveau_message)
            db.session.commit()
            flash('Réponse envoyée avec succès', 'success')
            return redirect(url_for('espace_membre'))
        else:
            flash('Le message ne peut pas être vide', 'danger')

    return render_template('repondre_message.html', message_original=message_original)


@app.route('/message/forward/<int:message_id>', methods=['POST'])
@login_required
def forward_message(message_id):
    """Transférer un message à un autre membre"""
    message_original = Message.query.get_or_404(message_id)
    destinataire_id = request.form.get('destinataire_id')
    commentaire = request.form.get('commentaire', '')

    if not destinataire_id:
        flash('Veuillez sélectionner un destinataire', 'danger')
        return redirect(url_for('espace_membre'))

    contenu_forward = f"[Message transféré de {message_original.expediteur.email}]\n\n"
    if commentaire:
        contenu_forward += f"Commentaire: {commentaire}\n\n"
    contenu_forward += message_original.contenu

    nouveau_message = Message(
        expediteur_id=current_user.id,
        destinataire_id=destinataire_id,
        contenu=contenu_forward
    )
    db.session.add(nouveau_message)
    db.session.commit()

    flash('Message transféré avec succès', 'success')
    return redirect(url_for('espace_membre'))


@app.route('/api/messages/marquer_tous_lus', methods=['POST'])
@login_required
def marquer_tous_messages_lus():
    """Marquer tous les messages comme lus"""
    messages = Message.query.filter_by(
        destinataire_id=current_user.id,
        lu=False
    ).all()

    count = 0
    for message in messages:
        if message.marquer_comme_lu():
            count += 1

    db.session.commit()
    return jsonify({'marked': count})

@app.route('/membre/marquer-lu/<int:message_id>')
@login_required
def marquer_lu(message_id):
    message = Message.query.get_or_404(message_id)
    if message.destinataire_id == current_user.id:
        message.lu = True
        db.session.commit()
    return redirect(url_for('espace_membre'))


@app.route('/api/communes/<int:departement_id>')
def get_communes(departement_id):
    communes = Commune.query.filter_by(departement_id=departement_id).all()
    return jsonify([{'id': c.id, 'nom': c.nom} for c in communes])

@app.route('/api/sections/<int:commune_id>')
def get_sections(commune_id):
    sections = SectionCommunale.query.filter_by(commune_id=commune_id).all()
    return jsonify([{'id': s.id, 'nom': s.nom} for s in sections])


@app.route('/admin/approuver-membre/<int:membre_id>')
@login_required
def approuver_membre(membre_id):
    # Vérifier que l'utilisateur est admin (général ou départemental)
    if current_user.role not in ['admin_general', 'admin_depart']:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))

    membre = Membre.query.get_or_404(membre_id)

    # Vérifier que l'admin départemental n'approuve que ses membres
    if current_user.role == 'admin_depart' and membre.departement_id != current_user.departement_id:
        flash('Vous ne pouvez pas approuver ce membre', 'danger')
        return redirect(url_for('dashboard_admin_depart'))

    # Changer le statut
    membre.statut = 'actif'
    db.session.commit()

    flash(f'Membre {membre.nom} {membre.prenom} approuvé avec succès!', 'success')

    if current_user.role == 'admin_general':
        return redirect(url_for('dashboard_admin_general'))
    else:
        return redirect(url_for('dashboard_admin_depart'))


@app.route('/admin/refuser-membre/<int:membre_id>', methods=['GET', 'POST'])
@login_required
def refuser_membre(membre_id):
    if current_user.role not in ['admin_general', 'admin_depart']:
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('index'))

    membre = Membre.query.get_or_404(membre_id)

    if request.method == 'POST':
        motif = request.form.get('motif', 'Non spécifié')
        membre.statut = 'refuse'
        db.session.commit()
        flash(f'Membre {membre.nom} {membre.prenom} refusé. Motif: {motif}', 'danger')
        return redirect(
            url_for('dashboard_admin_general' if current_user.role == 'admin_general' else 'dashboard_admin_depart'))

    return render_template('refuser_membre.html', membre=membre)


# Initialisation de la base de données
def init_db():
    with app.app_context():
        db.create_all()

        # Données des départements, communes et sections
        data_geo = {
            'Ouest': {
                'chef_lieu': 'Port-au-Prince',
                'communes': {
                    'Port-au-Prince': ['Turgeau', 'Bolosse', 'Bel Air', 'La Saline', 'Carrefour-Feuilles', 'Christ-Roi',
                                       'Fontamara', 'Martissant'],
                    'Carrefour': ['Brossard', 'Corail-Lestomac', 'Tibourg', 'Welfrand'],
                    'Delmas': ['Delmas 1', 'Delmas 2', 'Delmas 3', 'Delmas 4', 'Delmas 5'],
                    'Pétion-Ville': ['Belot', 'Bois d\'Avril', 'Morin', 'Pélissier'],
                    'Kenscoff': ['Bongars', 'Coupeau', 'Manneville', 'Mombin-Crochu'],
                    'Gressier': ['Gressier', 'Morne-à-Bateau', 'Morne-à-Chien'],
                    'Léogâne': ['Délé, Citronnier, Fontaine, La fontaine, Lévèque, Mirbalais, Petit-Bois, Rouche',
                                'Trou-balan'],
                    'Arcahaie': ['Arcahaie', 'Baie-de-Henne', 'Bois-Myrtre', 'La Citerne', 'Mapou'],
                    'Cabaret': ['Bois-Neuf', 'Cabaret', 'Croix-des-Bouquets', 'Côtes-de-Fer', 'La Tournelle'],
                    'Croix-des-Bouquets': ['Beaubrun', 'Croix-des-Bouquets', 'Fermathe', 'Ganthier', 'Grande-Plaine',
                                           'Le Côteau', 'Mare-Rose', 'Marion', 'Montagne-Noire', 'Nan-Haïtien',
                                           'Noailly'],
                    'Cornillon': ['Cornillon', 'Grand-Bois', 'L\'Asile', 'La Bruyère', 'La Hoye', 'Malgène', 'Manoir'],
                    'Thomazeau': ['Barrière-Battant', 'Bayard', 'Bellefontaine', 'Célestin', 'Charlotte', 'Colombier',
                                  'Cornillon', 'Grande-Rivière', 'La Croix-Mission', 'La Montagne', 'La Selle',
                                  'Morne-à-Brûler', 'Morne-Pierre']
                }
            },
            'Nord': {
                'chef_lieu': 'Cap-Haïtien',
                'communes': {
                    'Cap-Haïtien': ['Bande-du-Nord', 'Haut-du-Cap', 'Petit-Anse', 'Grande-Anse'],
                    'Milot': ['Bois-Marcel', 'Milot', 'Petite-Anse', 'Vieux-Milot'],
                    'Limbé': ['Bois-de-Lance', 'Limbé', 'Source-Marmont', 'Trou'],
                    'Plaine-du-Nord': ['Bois-Moulin', 'Le Trou', 'Morne-à-Bruler', 'Plaine-du-Nord'],
                    'Acul-du-Nord': ['Acul-du-Nord', 'Bas-de-l\'Acul', 'Camp-Coq', 'Coupe-à-Mathurin', 'La Soufrière',
                                     'Morne-à-Fleur', 'Morne-à-Pierre'],
                    'Borgne': ['Borgne', 'Chalet-Minot', 'Décade', 'Lamontagne', 'Pilate'],
                    'Port-Margot': ['Baille-Dimanche', 'Bel-Air', 'Bois-Dauphin', 'Caracol', 'Gens-de-Nantes',
                                    'La Souffrance', 'Limonade', 'Morne-à-Bonbon'],
                    'Saint-Raphaël': ['Dondon', 'La Coupe', 'La Ferme', 'Phaëton', 'Sainte-Suzanne', 'Vallière'],
                    'Ranquitte': ['Derrière-La-Rivière', 'Grande-Savane', 'La Hoye', 'La Source', 'Morne-à-Bateau',
                                  'Ranquitte'],
                    'Pignon': ['Bois-de-Lance', 'Cachiman', 'Carrefour-Déa', 'Déa', 'La Bruyère', 'La Guayamouille',
                               'Lapointe', 'Morne-à-Bœuf']
                }
            },
            'Nord-Est': {
                'chef_lieu': 'Fort-Liberté',
                'communes': {
                    'Fort-Liberté': ['Dérac', 'Dumol', 'Laou', 'Laville', 'Moron', 'Nan-Boucan', 'Vallières'],
                    'Ouanaminthe': ['Bassin-Dimanche', 'Bois-Blanc', 'Café-Mathurin', 'Carrefour-La-Place',
                                    'Carrefour-Neuf', 'Cassagnade', 'Ferme-Neuve', 'Grand-Bois', 'La Fleur', 'La Joie',
                                    'Mombin-Crochu', 'Morne-à-Bœuf', 'Morne-à-Chien', 'Morne-à-Bateau',
                                    'Roche-Blanche'],
                    'Trou-du-Nord': ['Bord-de-mer', 'Caracol', 'Caribes', 'Grand-Bois', 'La Soufrière', 'Lagon',
                                     'Morne-à-Chien', 'Morne-à-Fleur', 'Morne-à-Fromager', 'Morne-à-Pierre',
                                     'Nan-Boucan'],
                    'Sainte-Suzanne': ['Bois-Blanc', 'Bois-Griffon', 'Bois-Neuf', 'Bord-de-mer', 'Carrefour-La-Place',
                                       'Carrefour-Neuf', 'Citronnelle', 'Coq-Chante', 'Desruisseaux', 'Grande-Saline',
                                       'La Bruyère', 'La Coupe', 'La Hoye', 'La Jalousie', 'La Source', 'Lactose',
                                       'Morne-à-Brûler', 'Morne-à-Bœuf', 'Morne-à-Chien', 'Morne-à-Fleur',
                                       'Morne-à-Pierre', 'Morne-Brûlé', 'Morne-Rouge', 'Nan-Ciel', 'Nancivier',
                                       'Source-Bleue', 'Terre-Rouge', 'Trou-d Eau'],
                                                                                 'Terrier-Rouge': ['Beaumont',
                                                                                                   'Bois-Griffon',
                                                                                                   'Bois-Neuf',
                                                                                                   'Carrefour-La-Place',
                                                                                                   'Carrefour-Neuf',
                                                                                                   'Coq-Chante',
                                                                                                   'Desruisseaux',
                                                                                                   'La Coupe',
                                                                                                   'La Hoye',
                                                                                                   'La Source',
                                                                                                   'Morne-à-Brûler',
                                                                                                   'Morne-à-Bœuf',
                                                                                                   'Morne-à-Chien',
                                                                                                   'Morne-à-Fleur',
                                                                                                   'Morne-à-Pierre',
                                                                                                   'Morne-Brûlé',
                                                                                                   'Morne-Rouge',
                                                                                                   'Nan-Ciel',
                                                                                                   'Nancivier',
                                                                                                   'Source-Bleue',
                                                                                                   'Terre-Rouge',
                                                                                                   'Trou-d Eau'],
                                                                                                              'Ferrier': [
            'Bois-Blanc', 'Bois-Griffon', 'Bois-Neuf', 'Carrefour-La-Place', 'Carrefour-Neuf', 'Coq-Chante',
            'Desruisseaux', 'La Coupe', 'La Hoye', 'La Source', 'Morne-à-Brûler', 'Morne-à-Bœuf', 'Morne-à-Chien',
            'Morne-à-Fleur', 'Morne-à-Pierre', 'Morne-Brûlé', 'Morne-Rouge', 'Nan-Ciel', 'Nancivier', 'Source-Bleue',
            'Terre-Rouge', 'Trou-d Eau']
        }
        },
            'Centre': {
                'chef_lieu': 'Hinche',
                'communes': {
                    'Hinche': ['Baptiste', 'Ca-Ica', 'Grand-Bois', 'Marmont', 'Morne-à-Bateau', 'Savane-Longue',
                               'Saut-d\'Eau'],
                    'Mirebalais': ['La Coupe', 'Lemonade', 'Morne-à-Bateau', 'Périgny', 'Saut-d\'Eau'],
                    'Cerca-la-Source': ['Cerca-la-Source', 'Lascahobas', 'Trou-d\'Eau'],
                    'Lascahobas': ['Baptiste', 'Boucan-Carré', 'Lascahobas', 'Morne-à-Bateau', 'Savane-Longue'],
                    'Savane-carrée': ['Savane-carrée', 'Thomonde'],
                    'Thomonde': ['Thomonde', 'Maïssade']
                }
            },
            'Sud': {
                'chef_lieu': 'Les Cayes',
                'communes': {
                    'Les Cayes': ['Bernard', 'Bordeaux', 'Camp-Perrin', 'Cavaillon', 'Chantal', 'Les Cayes', 'Maniche',
                                  'Ravine-des-Cabris', 'Tourniquet'],
                    'Camp-Perrin': ['Camp-Perrin', 'Côteaux', 'Port-à-Piment', 'Roche-à-Bateau'],
                    'Chantal': ['Chantal', 'Torbeck', 'Saint-Jean-du-Sud'],
                    'Torbeck': ['Torbeck', 'Arniquet', 'Saint-Louis-du-Sud'],
                    'Côteaux': ['Côteaux', 'Port-Salut', 'Roche-à-Bateau']
                }
            },
            'Sud-Est': {
                'chef_lieu': 'Jacmel',
                'communes': {
                    'Jacmel': ['Jacmel', 'Marigot', 'Cayes-Jacmel', 'La Vallée', 'Belle-Anse'],
                    'Belle-Anse': ['Belle-Anse', 'Anse-à-Pitres', 'Grand-Gosier', 'Thiotte']
                }
            },
            'Grand\'Anse': {
                'chef_lieu': 'Jérémie',
                'communes': {
                    'Jérémie': ['Jérémie', 'Abricots', 'Bonbon', 'Chambellan', 'Dame-Marie', 'Les Anglais', 'Moron'],
                    'Moron': ['Moron', 'Beaumont', 'Roseaux']
                }
            },
            'Nippes': {
                'chef_lieu': 'Miragoâne',
                'communes': {
                    'Miragoâne': ['Miragoâne', 'Anse-à-Veau', 'Arnaud', 'Baradères', 'Fonds-des-Nègres', 'Paillant',
                                  'Petit-Trou-de-Nippes', 'Plaisance-du-Sud']
                }
            },
        'Nord-Ouest': {
            'chef_lieu': 'Port-de-Paix',
            'communes': {
                'Port-de-Paix': ['Aubert', 'Baptiste', 'Bassin-Bleu', 'Bord-de-Mer', 'Boucan-Neuf', 'Caracol',
                                 'Carrefour-La-Place', 'Carrefour-Neuf', 'Catin', 'Champin', 'Chardonnette',
                                 'Coco-Blanc', 'Courlande', 'Désiré', 'Duchity', 'Dumol', 'Garde-Camp',
                                 'Garde-Champêtre', 'Gervais', 'Grande-Rivière', 'La Coupe', 'La Hoye', 'La Mission',
                                 'La Montagne', 'La Passe', 'La Source', 'LaTerre', 'Lacoma', 'Lagon', 'Lamare',
                                 'Landel', 'Lapierre', 'Laroche', 'Laurence', 'Léogâne', 'Les Irois', 'Lespasse',
                                 'Lester', 'Liancourt', 'Madame-Marcel', 'Mahotière', 'Malgène', 'Malfini',
                                 'Mallebranche', 'Mancel', 'Marcel', 'Mare-Rose', 'Marié-Galant', 'Marigot', 'Marin',
                                 'Marmelade', 'Martin', 'Matthieu', 'Maufant', 'Maxime', 'Mérotte', 'Milot',
                                 'Mirebalais', 'Mombin-Crochu', 'Monchilot', 'Monfort', 'Mont-Organisé', 'Montalbano',
                                 'Montagne-Noire', 'Morne-à-Bateau', 'Morne-à-Brûler', 'Morne-à-Chien', 'Morne-à-Fleur',
                                 'Morne-à-Fromager', 'Morne-à-Pierre', 'Morne-Brûlé', 'Morne-Rouge', 'Nan-Ciel',
                                 'Nan-Fleury', 'Nan-Grégoire', 'Nan-Mango', 'Nancivier', 'Noailles', 'Organisé',
                                 'Ouanaminthe', 'Paille', 'Palmiste', 'Passe-Reine', 'Péan', 'Pelletier', 'Périgny',
                                 'Pestel', 'Petit-Bourg', 'Petit-Goâve', 'Petit-Trou', 'Philippe', 'Plaine-du-Nord',
                                 'Plaisance', 'Pointe-à-Raquette', 'Pointe-Sèche', 'Port-Margot', 'Port-Salut',
                                 'Poterie', 'Pouly', 'Ravine-à-Bœuf', 'Ravine-Sèche', 'Roche-Blanche', 'Roche-Plate',
                                 'Rondelle', 'Roseau', 'Saint-Louis-du-Nord', 'Saint-Marc',
                                 'Saint-Michel-de-l\'Atalaye', 'Sainte-Anne', 'Sainte-Suzanne', 'Salagnac', 'Salines',
                                 'Savane-à-Roches', 'Savane-Bataille', 'Savane-Carrière', 'Savane-Dlo',
                                 'Savane-Grégoire', 'Savane-Longue', 'Savane-Neuf', 'Savane-Pin', 'Savane-Ronde',
                                 'Savane-Sèche', 'Savane-Souris', 'Savanette', 'Savary', 'Séjour', 'Soleil',
                                 'Source-Bleue', 'Source-Cabrit', 'Source-Canon', 'Source-Chaude', 'Source-Désirée',
                                 'Source-Froide', 'Source-Galette', 'Source-Marmont', 'Source-Mercier', 'Source-Mousse',
                                 'Source-Orange', 'Source-Paradis', 'Source-Puante', 'Source-Rouge', 'Source-Salée',
                                 'Source-Sèche', 'Source-Trou', 'Souris', 'Soyer', 'Terre-Blanche', 'Terre-Froide',
                                 'Terre-Neuve', 'Terre-Rouge', 'Thomonde', 'Thor', 'Ti-Goâve', 'Ti-Rivière', 'Torbeck',
                                 'Toto', 'Trou', 'Trou-d Eau', 'Trou - du - Nord', 'Vallières', 'Verrettes', 'Vieux - Bourg',
                                 'Vieux - Bourg - d\'Aquin', 'Vieux-Verger', 'Ville-Bonheur', 'Villiers', 'Violette', 'Wassac', 'Wolbert'],
        'Saint-Louis-du-Nord': ['Bois-Blanc', 'Bois-Griffon', 'Bois-Neuf', 'Carrefour-La-Place', 'Carrefour-Neuf',
                                'Coq-Chante', 'Desruisseaux', 'La Coupe', 'La Hoye', 'La Source', 'Morne-à-Brûler',
                                'Morne-à-Bœuf', 'Morne-à-Chien', 'Morne-à-Fleur', 'Morne-à-Pierre', 'Morne-Brûlé',
                                'Morne-Rouge', 'Nan-Ciel', 'Nancivier', 'Source-Bleue', 'Terre-Rouge', 'Trou-d Eau']
        }
        },
        'Artibonite': {
            'chef_lieu': 'Gonaïves',
            'communes': {
                'Gonaïves': ['Bayonaise', 'Bocozelle', 'Bord-Mare', 'Brisse', 'Cafeau', 'Carrefour-Matheux',
                             'Chauffard', 'Chapelet', 'Cocotiers', 'Côte-de-Fer', 'Coum', 'Debbin', 'Derrière-Morne',
                             'Desdunes', 'Dézaley', 'Doco', 'Douro', 'Drouillard', 'Duclos', 'Duval', 'Ennery',
                             'Entre-Deux', 'Épinard', 'Estère', 'Étang', 'Fayette', 'Félicité', 'Gaillet', 'Garde',
                             'Grand-Bois', 'Grand-Fond', 'Grande-Rivière', 'Grande-Saline', 'Gros-Morne', 'Guillaume',
                             'Haut-Palmiste', 'Ile-de-la-Gonave', 'Jean-Rabel', 'Jean-Renaud', 'La Chapelle',
                             'La Coupe', 'La Croix', 'La Ferme', 'La Hoye', 'La Montagne', 'La Piste', 'La Pointe',
                             'La Rue', 'La Savane', 'La Source', 'LaTerre', 'Lacahou', 'Lagon', 'Lamare', 'Lamartine',
                             'Lanzac', 'Lapierre', 'Larose', 'Latanier', 'Laudy', 'Lauriers', 'Laville', 'Léogâne',
                             'Les Anglais', 'Les Baradères', 'Les Cayes', 'Les Irois', 'Lester', 'Liancourt', 'Maldoue',
                             'Mallebranche', 'Malpasse', 'Manceau', 'Mango', 'Mapou', 'Marcel', 'Mare-Rouge',
                             'Marié-Galant', 'Marigot', 'Marin', 'Marmelade', 'Marseille', 'Martin', 'Maufant',
                             'Mergué', 'Mérotte', 'Milot', 'Miragoâne', 'Mirebalais', 'Mombin-Crochu', 'Monfort',
                             'Mont-Organisé', 'Montagne-Noire', 'Montalbano', 'Morne-à-Bateau', 'Morne-à-Brûler',
                             'Morne-à-Chien', 'Morne-à-Fleur', 'Morne-à-Fromager', 'Morne-à-Pierre', 'Morne-Brûlé',
                             'Morne-Rouge', 'Nan-Ciel', 'Nan-Fleury', 'Nan-Grégoire', 'Nan-Mango', 'Nancivier'],
                'Saint-Marc': ['Bois-Blanc', 'Bois-Griffon', 'Bois-Neuf', 'Carrefour-La-Place', 'Carrefour-Neuf',
                               'Coq-Chante', 'Desruisseaux', 'La Coupe', 'La Hoye', 'La Source', 'Morne-à-Brûler',
                               'Morne-à-Bœuf', 'Morne-à-Chien', 'Morne-à-Fleur', 'Morne-à-Pierre', 'Morne-Brûlé',
                               'Morne-Rouge', 'Nan-Ciel', 'Nancivier', 'Source-Bleue', 'Terre-Rouge', 'Trou-d Eau']
            }

        }
        }

        # Création du département Diaspora
        diaspora = Departement.query.filter_by(nom='Diaspora').first()
        if not diaspora:
            diaspora = Departement(nom='Diaspora', code='DI', chef_lieu='Monde')
            db.session.add(diaspora)
            db.session.flush()

        # Liste des pays du monde - METTRE ICI
        pays_liste = [
            'France', 'Canada', 'États-Unis', 'Allemagne', 'Royaume-Uni', 'Italie', 'Espagne',
            'Belgique', 'Suisse', 'Luxembourg', 'Pays-Bas', 'Portugal', 'Suède', 'Norvège',
            'Danemark', 'Finlande', 'Irlande', 'Autriche', 'Grèce', 'Turquie', 'Russie',
            'Chine', 'Japon', 'Corée du Sud', 'Inde', 'Brésil', 'Argentine', 'Mexique',
            'Chili', 'Pérou', 'Colombie', 'Venezuela', 'Cuba', 'République Dominicaine',
            'Bahamas', 'Jamaïque', 'Sénégal', 'Côte d\'Ivoire', 'Cameroun', 'Congo',
            'Maroc', 'Algérie', 'Tunisie', 'Égypte', 'Afrique du Sud', 'Nigéria',
            'Australie', 'Nouvelle-Zélande', 'Israël', 'Émirats Arabes Unis', 'Qatar',
            'Arabie Saoudite', 'Thaïlande', 'Vietnam', 'Philippines', 'Malaisie',
            'Singapour', 'Indonésie', 'Pakistan', 'Bangladesh', 'Népal', 'Sri Lanka'
        ]

        for pays_nom in pays_liste:
            if not Commune.query.filter_by(nom=pays_nom, departement_id=diaspora.id).first():
                pays = Commune(nom=pays_nom, departement_id=diaspora.id)
                db.session.add(pays)
                db.session.flush()

                villes = ['Capitale', 'Ville principale']
                for ville in villes:
                    if not SectionCommunale.query.filter_by(nom=ville, commune_id=pays.id).first():
                        section = SectionCommunale(nom=ville, commune_id=pays.id)
                        db.session.add(section)

        # Pour simplifier, nous allons ajouter les communes essentielles pour tous les départements
        communes_base = {
            1: ['Port-au-Prince', 'Carrefour', 'Delmas', 'Pétion-Ville', 'Kenscoff', 'Gressier', 'Léogâne',
                'Croix-des-Bouquets', 'Thomazeau'],
            2: ['Cap-Haïtien', 'Milot', 'Limbé', 'Plaine-du-Nord', 'Acul-du-Nord', 'Borgne', 'Port-Margot',
                'Saint-Raphaël', 'Ranquitte', 'Pignon'],
            3: ['Fort-Liberté', 'Ouanaminthe', 'Trou-du-Nord', 'Sainte-Suzanne', 'Terrier-Rouge', 'Ferrier'],
            4: ['Port-de-Paix', 'Saint-Louis-du-Nord', 'Bassin-Bleu', 'Chansolme', 'La Tortue'],
            5: ['Gonaïves', 'Saint-Marc', 'Dessalines', 'Petite-Rivière-de-l\'Artibonite', 'Verrettes', 'Ennery',
                'Grande-Saline', 'Desdunes'],
            6: ['Hinche', 'Mirebalais', 'Cerca-la-Source', 'Lascahobas', 'Savane-carrée', 'Saut-d\'Eau', 'Thomonde'],
            7: ['Les Cayes', 'Camp-Perrin', 'Chantal', 'Maniche', 'Torbeck', 'Côteaux', 'Port-Salut', 'Roche-à-Bateau',
                'Saint-Jean-du-Sud', 'Arniquet'],
            8: ['Jacmel', 'Marigot', 'Cayes-Jacmel', 'La Vallée', 'Belle-Anse', 'Anse-à-Pitres', 'Thiotte'],
            9: ['Jérémie', 'Moron', 'Les Anglais', 'Dame-Marie', 'Chambellan', 'Beaumont', 'Bonbon', 'Abricots',
                'Roseaux'],
            10: ['Miragoâne', 'Anse-à-Veau', 'Arnaud', 'Petit-Trou-de-Nippes', 'Paillant', 'Baradères',
                 'Fonds-des-Nègres', 'Plaisance-du-Sud']
        }

        # Sections communales de base
        sections_base = [
            '1ère Section', '2ème Section', '3ème Section', '4ème Section',
            'Bois d\'Orme', 'Bois Neuf', 'Carrefour', 'Centre Ville',
            'Croix Rouge', 'Grande Ravine', 'La Plaine', 'Morne à Cabrit',
            'Nan Citron', 'Nan Mangot', 'Plateau', 'Ravine Sèche'
        ]

        for dept_nom, dept_info in data_geo.items():
            dept = Departement.query.filter_by(nom=dept_nom).first()
            if not dept:
                # Utilisez:
                codes_uniques = {
                    'Ouest': 'OU',
                    'Nord': 'ND',
                    'Nord-Est': 'NE',
                    'Nord-Ouest': 'NO',
                    'Artibonite': 'AR',
                    'Centre': 'CE',
                    'Sud': 'SU',
                    'Sud-Est': 'SE',
                    "Grand'Anse": 'GA',
                    'Nippes': 'NI',
                    'Diaspora': 'DA'
                }

                dept = Departement(nom=dept_nom, code=codes_uniques[dept_nom], chef_lieu=dept_info['chef_lieu'])
                db.session.add(dept)
                db.session.flush()

            for commune_nom, sections in dept_info['communes'].items():
                commune = Commune.query.filter_by(nom=commune_nom, departement_id=dept.id).first()
                if not commune:
                    commune = Commune(nom=commune_nom, departement_id=dept.id)
                    db.session.add(commune)
                    db.session.flush()

                for section_nom in sections:
                    if isinstance(section_nom, str) and section_nom.strip():
                        if not SectionCommunale.query.filter_by(nom=section_nom, commune_id=commune.id).first():
                            section = SectionCommunale(nom=section_nom, commune_id=commune.id)
                            db.session.add(section)

        db.session.commit()


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
