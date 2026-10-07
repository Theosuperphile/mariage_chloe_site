import csv, io, os, secrets
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import qrcode
from flask import Flask, Response, flash, redirect, render_template, request, send_file, session, url_for
from flask_sqlalchemy import SQLAlchemy
from openpyxl import Workbook
from sqlalchemy import func
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash

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
    participants = db.relationship("Participant", back_populates="reponse", cascade="all, delete-orphan", order_by="Participant.ordre")

class Participant(db.Model):
    __tablename__ = "participants"
    id = db.Column(db.Integer, primary_key=True)
    reponse_id = db.Column(db.Integer, db.ForeignKey("reponses.id", ondelete="CASCADE"), nullable=False, index=True)
    nom_prenom = db.Column(db.String(150), nullable=False)
    type_participant = db.Column(db.String(10), nullable=False)
    allergies = db.Column(db.String(500), nullable=False, default="")
    ordre = db.Column(db.Integer, nullable=False, default=1)
    reponse = db.relationship("Reponse", back_populates="participants")

def entier_formulaire(nom, minimum=0, maximum=30):
    try: nombre = int(request.form.get(nom, "0").strip())
    except (TypeError, ValueError): raise ValueError(f"La valeur du champ « {nom} » est invalide.")
    if not minimum <= nombre <= maximum: raise ValueError(f"La valeur du champ « {nom} » doit être comprise entre {minimum} et {maximum}.")
    return nombre

def lire_participants(adultes, enfants, nom_principal):
    participants, erreurs = [], []
    for type_p, total, prefixe in (("adulte", adultes, "adulte"), ("enfant", enfants, "enfant")):
        for i in range(1, total + 1):
            nom = " ".join(request.form.get(f"{prefixe}_{i}_nom", "").split())
            if type_p == "adulte" and i == 1 and not nom: nom = nom_principal
            allergie = request.form.get(f"{prefixe}_{i}_allergies", "").strip()[:500]
            if len(nom) < 3: erreurs.append(f"Indiquez le nom et le prénom de {type_p} {i}.")
            elif len(nom) > 150: erreurs.append(f"Le nom de {type_p} {i} est trop long.")
            participants.append(Participant(nom_prenom=nom[:150], type_participant=type_p, allergies=allergie, ordre=i))
    return participants, erreurs

def creer_application(config_test=None):
    app = Flask(__name__); app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    database_url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'mariage.db'}")
    if database_url.startswith("postgres://"): database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config.update(SECRET_KEY=os.getenv("SECRET_KEY", secrets.token_hex(32)), SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False, MAX_CONTENT_LENGTH=1024*1024, SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV")=="production",
        APP_BASE_URL=os.getenv("APP_BASE_URL","https://mariage-chloe-khaled.onrender.com").rstrip("/"),
        ADMIN_USERNAME=os.getenv("ADMIN_USERNAME","admin"), ADMIN_PASSWORD_HASH=os.getenv("ADMIN_PASSWORD_HASH",""))
    if config_test: app.config.update(config_test)
    db.init_app(app)
    with app.app_context(): db.create_all()
    def csrf_token():
        if "csrf_token" not in session: session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]
    app.jinja_env.globals["csrf_token"] = csrf_token
    @app.before_request
    def verifier_csrf():
        if request.method == "POST":
            if not session.get("csrf_token") or not secrets.compare_digest(request.form.get("csrf_token",""), session.get("csrf_token","")):
                return render_template("erreur.html", message="La session a expiré. Rechargez la page et recommencez."), 400
    def admin_requis(f):
        @wraps(f)
        def enveloppe(*a, **k):
            return redirect(url_for("admin_connexion", suite=request.path)) if not session.get("admin_connecte") else f(*a, **k)
        return enveloppe
    @app.get("/")
    def accueil(): return render_template("index.html")
    @app.post("/envoyer")
    def envoyer():
        if request.form.get("site_web",""): return redirect(url_for("merci"))
        nom = " ".join(request.form.get("nom_prenom","").split()); tel = " ".join(request.form.get("telephone","").split())
        presence_txt=request.form.get("presence",""); message=request.form.get("message","").strip()[:2000]; erreurs=[]; participants=[]
        if len(nom)<3: erreurs.append("Indiquez le nom et le prénom.")
        if len(tel)<6: erreurs.append("Indiquez un numéro de téléphone valide.")
        if presence_txt not in {"oui","non"}: erreurs.append("Indiquez si vous serez présent au mariage.")
        try:
            if presence_txt=="oui":
                adultes=entier_formulaire("adultes",0,20); enfants=entier_formulaire("enfants",0,20)
                rc=entier_formulaire("repas_classiques",0,20); rv=entier_formulaire("repas_vegetariens",0,20); me=entier_formulaire("menus_enfants",0,20)
                couch=entier_formulaire("couchages",0,40); ba=entier_formulaire("brunch_adultes",0,20); be=entier_formulaire("brunch_enfants",0,20)
                if adultes+enfants<1: erreurs.append("Indiquez au moins une personne présente.")
                if rc+rv!=adultes: erreurs.append("Le total des repas classique et végétarien doit correspondre au nombre d’adultes.")
                if me!=enfants: erreurs.append("Le nombre de menus enfant doit correspondre au nombre d’enfants.")
                ht=request.form.get("hebergement",""); bt=request.form.get("brunch","")
                if ht not in {"oui","non"}: erreurs.append("Indiquez votre choix d’hébergement.")
                if bt not in {"oui","non"}: erreurs.append("Indiquez votre présence au brunch.")
                heberg=ht=="oui"; brunch=bt=="oui"
                if heberg and not 1<=couch<=adultes+enfants: erreurs.append("Le nombre de couchages doit être compris entre 1 et le nombre de personnes présentes.")
                if not heberg: couch=0
                if brunch:
                    if ba+be<1: erreurs.append("Indiquez le nombre de personnes présentes au brunch.")
                    if ba>adultes or be>enfants: erreurs.append("Le nombre de participants au brunch ne peut pas dépasser le nombre de participants au mariage.")
                else: ba=be=0
                participants, ep = lire_participants(adultes,enfants,nom); erreurs.extend(ep)
            else:
                adultes=enfants=rc=rv=me=couch=ba=be=0; heberg=brunch=None
        except ValueError as e: erreurs.append(str(e))
        if erreurs:
            for e in erreurs: flash(e,"erreur")
            return render_template("index.html", donnees=request.form),400
        r=Reponse(nom_prenom=nom,telephone=tel,presence=presence_txt=="oui",adultes=adultes,enfants=enfants,
            repas_classiques=rc,repas_vegetariens=rv,menus_enfants=me,allergies="",hebergement=heberg,couchages=couch,
            brunch=brunch,brunch_adultes=ba,brunch_enfants=be,message=message,participants=participants)
        try: db.session.add(r); db.session.commit()
        except Exception: db.session.rollback(); raise
        session["derniere_reponse_id"]=r.id; return redirect(url_for("merci"))
    @app.get("/merci")
    def merci():
        ident=session.get("derniere_reponse_id"); return render_template("merci.html",reponse=db.session.get(Reponse,ident) if ident else None)
    @app.route("/admin",methods=["GET","POST"])
    def admin_connexion():
        if request.method=="POST":
            h=app.config["ADMIN_PASSWORD_HASH"]
            if h and request.form.get("utilisateur","")==app.config["ADMIN_USERNAME"] and check_password_hash(h,request.form.get("mot_de_passe","")):
                session.clear(); session["admin_connecte"]=True; session["csrf_token"]=secrets.token_urlsafe(32); return redirect(url_for("admin_tableau"))
            flash("Identifiant ou mot de passe incorrect.","erreur")
        return render_template("admin/connexion.html")
    @app.get("/admin/deconnexion")
    def admin_deconnexion(): session.clear(); return redirect(url_for("admin_connexion"))
    @app.get("/admin/tableau-de-bord")
    @admin_requis
    def admin_tableau():
        rs=Reponse.query.order_by(Reponse.cree_le.desc()).all(); stats={"reponses":len(rs),"presents":sum(r.adultes+r.enfants for r in rs if r.presence),"adultes":sum(r.adultes for r in rs),"enfants":sum(r.enfants for r in rs),"absents":sum(not r.presence for r in rs),"classiques":sum(r.repas_classiques for r in rs),"vegetariens":sum(r.repas_vegetariens for r in rs),"menus_enfants":sum(r.menus_enfants for r in rs),"couchages":sum(r.couchages for r in rs),"brunch":sum(r.brunch_adultes+r.brunch_enfants for r in rs)}
        doublons={t for t,n in db.session.query(Reponse.telephone,func.count(Reponse.id)).group_by(Reponse.telephone).having(func.count(Reponse.id)>1).all()}
        return render_template("admin/tableau.html",reponses=rs,stats=stats,doublons=doublons)
    @app.post("/admin/supprimer/<int:reponse_id>")
    @admin_requis
    def admin_supprimer(reponse_id): db.session.delete(db.get_or_404(Reponse,reponse_id)); db.session.commit(); flash("La réponse a été supprimée.","succes"); return redirect(url_for("admin_tableau"))
    entetes=["ID","Nom et prénom","Téléphone","Présence","Adultes","Enfants","Repas classiques","Repas végétariens","Menus enfants","Allergies","Hébergement","Couchages","Brunch","Adultes brunch","Enfants brunch","Message","Date de réponse"]
    def lignes_export():
        for r in Reponse.query.order_by(Reponse.cree_le.asc()).all():
            allergies="; ".join(f"{p.nom_prenom}: {p.allergies or 'Aucune'}" for p in r.participants) or r.allergies
            yield [r.id,r.nom_prenom,r.telephone,"Oui" if r.presence else "Non",r.adultes,r.enfants,r.repas_classiques,r.repas_vegetariens,r.menus_enfants,allergies,"Oui" if r.hebergement else ("Non" if r.hebergement is False else ""),r.couchages,"Oui" if r.brunch else ("Non" if r.brunch is False else ""),r.brunch_adultes,r.brunch_enfants,r.message,r.cree_le.strftime("%d/%m/%Y %H:%M")]
    @app.get("/admin/export.csv")
    @admin_requis
    def admin_export_csv():
        s=io.StringIO(); s.write("\ufeff"); w=csv.writer(s,delimiter=";"); w.writerow(entetes); w.writerows(lignes_export()); return Response(s.getvalue(),mimetype="text/csv; charset=utf-8",headers={"Content-Disposition":"attachment; filename=reponses_mariage.csv"})
    @app.get("/admin/export.xlsx")
    @admin_requis
    def admin_export_xlsx():
        wb=Workbook(); f=wb.active; f.title="Réponses"; f.append(entetes)
        for l in lignes_export(): f.append(l)
        f.freeze_panes="A2"; f.auto_filter.ref=f.dimensions
        p=wb.create_sheet("Participants"); p.append(["ID réponse","Répondant","Type","Ordre","Nom et prénom","Allergies"])
        for r in Reponse.query.order_by(Reponse.id).all():
            for x in r.participants: p.append([r.id,r.nom_prenom,x.type_participant.capitalize(),x.ordre,x.nom_prenom,x.allergies or "Aucune"])
        for sh in (f,p):
            for col in sh.columns: sh.column_dimensions[col[0].column_letter].width=min(max(len(str(c.value or "")) for c in col)+2,45)
        b=io.BytesIO(); wb.save(b); b.seek(0); return send_file(b,as_attachment=True,download_name="reponses_mariage.xlsx",mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    @app.get("/admin/qr-code.png")
    @admin_requis
    def admin_qr_code():
        qr=qrcode.QRCode(version=None,box_size=12,border=4); qr.add_data(app.config["APP_BASE_URL"]); qr.make(fit=True); image=qr.make_image(fill_color="#2e2724",back_color="white"); b=io.BytesIO(); image.save(b,format="PNG"); b.seek(0); return send_file(b,as_attachment=True,download_name="qr_code_mariage_chloe_khaled.png",mimetype="image/png")
    @app.get("/sante")
    def sante(): return {"statut":"ok"}
    @app.errorhandler(404)
    def introuvable(_): return render_template("erreur.html",message="Cette page n’existe pas."),404
    @app.errorhandler(413)
    def volumineux(_): return render_template("erreur.html",message="Les données envoyées sont trop volumineuses."),413
    return app
app=creer_application()
if __name__=="__main__": app.run(debug=True)
