import csv
import io
import os
import secrets
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import qrcode
from flask import Flask, Response, flash, redirect, render_template, request, send_file, session, url_for
from flask_sqlalchemy import SQLAlchemy
from openpyxl import Workbook
from sqlalchemy import func
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent

db = SQLAlchemy()


class Reponse(db.Model):
    __tablename__ = "reponses"

    id = db.Column(db.Integer, primary_key=True)
    nom_prenom = db.Column(db.String(150), nullable=False)
    telephone = db.Column(db.String(40), nullable=False, index=True)
    presence = db.Column(db.Boolean, nullable=False)
    adultes = db.Column(db.Integer, nullable=False, default=0)
    enfants = db.Column(db.Integer, nullable=False, default=0)
    repas_classiques = db.Column(db.Integer, nullable=False, default=0)
    repas_vegetariens = db.Column(db.Integer, nullable=False, default=0)
    menus_enfants = db.Column(db.Integer, nullable=False, default=0)
    allergies = db.Column(db.Text, nullable=False, default="")
    hebergement = db.Column(db.Boolean, nullable=True)
    couchages = db.Column(db.Integer, nullable=False, default=0)
    brunch = db.Column(db.Boolean, nullable=True)
    brunch_adultes = db.Column(db.Integer, nullable=False, default=0)
    brunch_enfants = db.Column(db.Integer, nullable=False, default=0)
    message = db.Column(db.Text, nullable=False, default="")
    cree_le = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


def entier_formulaire(nom, minimum=0, maximum=30):
    valeur = request.form.get(nom, "0").strip()
    try:
        nombre = int(valeur)
    except (TypeError, ValueError):
        raise ValueError(f"La valeur du champ « {nom} » est invalide.")
    if not minimum <= nombre <= maximum:
        raise ValueError(f"La valeur du champ « {nom} » doit être comprise entre {minimum} et {maximum}.")
    return nombre


def creer_application(config_test=None):
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    database_url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'mariage.db'}")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", secrets.token_hex(32)),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
        APP_BASE_URL=os.getenv("APP_BASE_URL", "https://mariage-chloe.onrender.com").rstrip("/"),
        ADMIN_USERNAME=os.getenv("ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD_HASH", ""),
    )
    if config_test:
        app.config.update(config_test)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def verifier_csrf():
        if request.method == "POST":
            recu = request.form.get("csrf_token", "")
            attendu = session.get("csrf_token", "")
            if not attendu or not secrets.compare_digest(recu, attendu):
                return render_template("erreur.html", message="La session a expiré. Rechargez la page et recommencez."), 400

    def admin_requis(fonction):
        @wraps(fonction)
        def enveloppe(*args, **kwargs):
            if not session.get("admin_connecte"):
                return redirect(url_for("admin_connexion", suite=request.path))
            return fonction(*args, **kwargs)
        return enveloppe

    @app.get("/")
    def accueil():
        return render_template("index.html")

    @app.post("/envoyer")
    def envoyer():
        if request.form.get("site_web", ""):
            return redirect(url_for("merci"))

        nom_prenom = " ".join(request.form.get("nom_prenom", "").split())
        telephone = " ".join(request.form.get("telephone", "").split())
        presence_texte = request.form.get("presence", "")
        message = request.form.get("message", "").strip()[:2000]

        erreurs = []
        if len(nom_prenom) < 3:
            erreurs.append("Indiquez le nom et le prénom.")
        if len(telephone) < 6:
            erreurs.append("Indiquez un numéro de téléphone valide.")
        if presence_texte not in {"oui", "non"}:
            erreurs.append("Indiquez si vous serez présent au mariage.")

        try:
            if presence_texte == "oui":
                adultes = entier_formulaire("adultes", 0, 20)
                enfants = entier_formulaire("enfants", 0, 20)
                repas_classiques = entier_formulaire("repas_classiques", 0, 20)
                repas_vegetariens = entier_formulaire("repas_vegetariens", 0, 20)
                menus_enfants = entier_formulaire("menus_enfants", 0, 20)
                couchages = entier_formulaire("couchages", 0, 40)
                brunch_adultes = entier_formulaire("brunch_adultes", 0, 20)
                brunch_enfants = entier_formulaire("brunch_enfants", 0, 20)
                if adultes + enfants < 1:
                    erreurs.append("Indiquez au moins une personne présente.")
                if repas_classiques + repas_vegetariens != adultes:
                    erreurs.append("Le total des repas classique et végétarien doit correspondre au nombre d’adultes.")
                if menus_enfants != enfants:
                    erreurs.append("Le nombre de menus enfant doit correspondre au nombre d’enfants.")

                hebergement_texte = request.form.get("hebergement", "")
                brunch_texte = request.form.get("brunch", "")
                if hebergement_texte not in {"oui", "non"}:
                    erreurs.append("Indiquez votre choix d’hébergement.")
                if brunch_texte not in {"oui", "non"}:
                    erreurs.append("Indiquez votre présence au brunch.")
                hebergement = hebergement_texte == "oui"
                brunch = brunch_texte == "oui"
                if hebergement and not 1 <= couchages <= adultes + enfants:
                    erreurs.append("Le nombre de couchages doit être compris entre 1 et le nombre de personnes présentes.")
                if not hebergement:
                    couchages = 0
                if brunch:
                    if brunch_adultes + brunch_enfants < 1:
                        erreurs.append("Indiquez le nombre de personnes présentes au brunch.")
                    if brunch_adultes > adultes or brunch_enfants > enfants:
                        erreurs.append("Le nombre de participants au brunch ne peut pas dépasser le nombre de participants au mariage.")
                else:
                    brunch_adultes = 0
                    brunch_enfants = 0
            else:
                adultes = enfants = repas_classiques = repas_vegetariens = menus_enfants = 0
                couchages = brunch_adultes = brunch_enfants = 0
                hebergement = brunch = None
        except ValueError as erreur:
            erreurs.append(str(erreur))

        if erreurs:
            for erreur in erreurs:
                flash(erreur, "erreur")
            return render_template("index.html", donnees=request.form), 400

        reponse = Reponse(
            nom_prenom=nom_prenom,
            telephone=telephone,
            presence=presence_texte == "oui",
            adultes=adultes,
            enfants=enfants,
            repas_classiques=repas_classiques,
            repas_vegetariens=repas_vegetariens,
            menus_enfants=menus_enfants,
            allergies=request.form.get("allergies", "").strip()[:2000] if presence_texte == "oui" else "",
            hebergement=hebergement,
            couchages=couchages,
            brunch=brunch,
            brunch_adultes=brunch_adultes,
            brunch_enfants=brunch_enfants,
            message=message,
        )
        db.session.add(reponse)
        db.session.commit()
        session["derniere_reponse_id"] = reponse.id
        return redirect(url_for("merci"))

    @app.get("/merci")
    def merci():
        reponse = db.session.get(Reponse, session.get("derniere_reponse_id")) if session.get("derniere_reponse_id") else None
        return render_template("merci.html", reponse=reponse)

    @app.route("/admin", methods=["GET", "POST"])
    def admin_connexion():
        if request.method == "POST":
            utilisateur = request.form.get("utilisateur", "")
            mot_de_passe = request.form.get("mot_de_passe", "")
            hash_configure = app.config["ADMIN_PASSWORD_HASH"]
            valide = bool(hash_configure) and utilisateur == app.config["ADMIN_USERNAME"] and check_password_hash(hash_configure, mot_de_passe)
            if valide:
                session.clear()
                session["admin_connecte"] = True
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("admin_tableau"))
            flash("Identifiant ou mot de passe incorrect.", "erreur")
        return render_template("admin/connexion.html")

    @app.get("/admin/deconnexion")
    def admin_deconnexion():
        session.clear()
        return redirect(url_for("admin_connexion"))

    @app.get("/admin/tableau-de-bord")
    @admin_requis
    def admin_tableau():
        reponses = Reponse.query.order_by(Reponse.cree_le.desc()).all()
        stats = {
            "reponses": len(reponses),
            "presents": sum(r.adultes + r.enfants for r in reponses if r.presence),
            "adultes": sum(r.adultes for r in reponses),
            "enfants": sum(r.enfants for r in reponses),
            "absents": sum(1 for r in reponses if not r.presence),
            "classiques": sum(r.repas_classiques for r in reponses),
            "vegetariens": sum(r.repas_vegetariens for r in reponses),
            "menus_enfants": sum(r.menus_enfants for r in reponses),
            "couchages": sum(r.couchages for r in reponses),
            "brunch": sum(r.brunch_adultes + r.brunch_enfants for r in reponses),
        }
        doublons = {telephone for telephone, total in db.session.query(Reponse.telephone, func.count(Reponse.id)).group_by(Reponse.telephone).having(func.count(Reponse.id) > 1).all()}
        return render_template("admin/tableau.html", reponses=reponses, stats=stats, doublons=doublons)

    @app.post("/admin/supprimer/<int:reponse_id>")
    @admin_requis
    def admin_supprimer(reponse_id):
        reponse = db.get_or_404(Reponse, reponse_id)
        db.session.delete(reponse)
        db.session.commit()
        flash("La réponse a été supprimée.", "succes")
        return redirect(url_for("admin_tableau"))

    def lignes_export():
        for r in Reponse.query.order_by(Reponse.cree_le.asc()).all():
            yield [
                r.id, r.nom_prenom, r.telephone, "Oui" if r.presence else "Non",
                r.adultes, r.enfants, r.repas_classiques, r.repas_vegetariens,
                r.menus_enfants, r.allergies, "Oui" if r.hebergement else ("Non" if r.hebergement is False else ""),
                r.couchages, "Oui" if r.brunch else ("Non" if r.brunch is False else ""),
                r.brunch_adultes, r.brunch_enfants, r.message,
                r.cree_le.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC") if r.cree_le.tzinfo else r.cree_le.strftime("%d/%m/%Y %H:%M"),
            ]

    entetes = ["ID", "Nom et prénom", "Téléphone", "Présence", "Adultes", "Enfants", "Repas classiques", "Repas végétariens", "Menus enfants", "Allergies", "Hébergement", "Couchages", "Brunch", "Adultes brunch", "Enfants brunch", "Message", "Date de réponse"]

    @app.get("/admin/export.csv")
    @admin_requis
    def admin_export_csv():
        sortie = io.StringIO()
        sortie.write("\ufeff")
        writer = csv.writer(sortie, delimiter=";")
        writer.writerow(entetes)
        writer.writerows(lignes_export())
        return Response(sortie.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=reponses_mariage.csv"})

    @app.get("/admin/export.xlsx")
    @admin_requis
    def admin_export_xlsx():
        classeur = Workbook()
        feuille = classeur.active
        feuille.title = "Réponses"
        feuille.append(entetes)
        for ligne in lignes_export():
            feuille.append(ligne)
        feuille.freeze_panes = "A2"
        feuille.auto_filter.ref = feuille.dimensions
        for colonne in feuille.columns:
            longueur = min(max(len(str(cell.value or "")) for cell in colonne) + 2, 45)
            feuille.column_dimensions[colonne[0].column_letter].width = longueur
        tampon = io.BytesIO()
        classeur.save(tampon)
        tampon.seek(0)
        return send_file(tampon, as_attachment=True, download_name="reponses_mariage.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    @app.get("/admin/qr-code.png")
    @admin_requis
    def admin_qr_code():
        qr = qrcode.QRCode(version=None, box_size=12, border=4)
        qr.add_data(app.config["APP_BASE_URL"])
        qr.make(fit=True)
        image = qr.make_image(fill_color="#2e2724", back_color="white")
        tampon = io.BytesIO()
        image.save(tampon, format="PNG")
        tampon.seek(0)
        return send_file(tampon, as_attachment=True, download_name="qr_code_mariage_chloe.png", mimetype="image/png")

    @app.get("/sante")
    def sante():
        return {"statut": "ok"}

    @app.errorhandler(404)
    def introuvable(_erreur):
        return render_template("erreur.html", message="Cette page n’existe pas."), 404

    @app.errorhandler(413)
    def trop_volumineux(_erreur):
        return render_template("erreur.html", message="Les données envoyées sont trop volumineuses."), 413

    return app


app = creer_application()


if __name__ == "__main__":
    app.run(debug=True)
