from werkzeug.security import generate_password_hash
from app import creer_application, db, Reponse


def app_test():
    app = creer_application({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
        "ADMIN_PASSWORD_HASH": generate_password_hash("mot-de-passe-test"),
        "ADMIN_USERNAME": "admin",
        "WTF_CSRF_ENABLED": False,
    })
    return app


def token(client):
    client.get("/")
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_accueil_et_sante():
    app = app_test()
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/sante").json == {"statut": "ok"}


def test_enregistrement_present():
    app = app_test(); client = app.test_client()
    reponse = client.post("/envoyer", data={
        "csrf_token": token(client), "nom_prenom": "Marie Martin", "telephone": "+33 6 00 00 00 00", "presence": "oui",
        "adultes": "2", "enfants": "1", "repas_classiques": "1", "repas_vegetariens": "1", "menus_enfants": "1",
        "allergies": "Aucune", "hebergement": "oui", "couchages": "3", "brunch": "oui", "brunch_adultes": "2", "brunch_enfants": "1", "message": "Merci"
    }, follow_redirects=False)
    assert reponse.status_code == 302
    with app.app_context():
        assert Reponse.query.count() == 1
        assert Reponse.query.first().couchages == 3


def test_validation_repas():
    app = app_test(); client = app.test_client()
    reponse = client.post("/envoyer", data={
        "csrf_token": token(client), "nom_prenom": "Jean Martin", "telephone": "0600000000", "presence": "oui",
        "adultes": "2", "enfants": "0", "repas_classiques": "1", "repas_vegetariens": "0", "menus_enfants": "0",
        "hebergement": "non", "couchages": "0", "brunch": "non", "brunch_adultes": "0", "brunch_enfants": "0"
    })
    assert reponse.status_code == 400
    assert "total des repas" in reponse.get_data(as_text=True)


def test_absent_et_admin_export():
    app = app_test(); client = app.test_client()
    assert client.post("/envoyer", data={"csrf_token": token(client), "nom_prenom": "Paul Durand", "telephone": "0611111111", "presence": "non", "message": "Désolé"}).status_code == 302
    client.get("/admin")
    with client.session_transaction() as session:
        csrf = session["csrf_token"]
    assert client.post("/admin", data={"csrf_token": csrf, "utilisateur": "admin", "mot_de_passe": "mot-de-passe-test"}).status_code == 302
    assert client.get("/admin/tableau-de-bord").status_code == 200
    assert client.get("/admin/export.xlsx").status_code == 200
    assert client.get("/admin/qr-code.png").status_code == 200
