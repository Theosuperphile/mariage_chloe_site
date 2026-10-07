from werkzeug.security import generate_password_hash
from app import creer_application, Reponse, Participant

def app_test(): return creer_application({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","SECRET_KEY":"test","ADMIN_PASSWORD_HASH":generate_password_hash("test-password"),"ADMIN_USERNAME":"admin"})
def token(c):
    c.get('/')
    with c.session_transaction() as s:return s['csrf_token']
def present(c):
    return c.post('/envoyer',data={"csrf_token":token(c),"nom_prenom":"Marie Martin","telephone":"0600000000","presence":"oui","adultes":"2","enfants":"1","adulte_1_nom":"Marie Martin","adulte_1_allergies":"Arachides","adulte_2_nom":"Jean Martin","adulte_2_allergies":"","enfant_1_nom":"Paul Martin","enfant_1_allergies":"Lactose","repas_classiques":"1","repas_vegetariens":"1","menus_enfants":"1","hebergement":"oui","couchages":"3","brunch":"oui","brunch_adultes":"2","brunch_enfants":"1"})
def test_accueil_sante():
    c=app_test().test_client();assert c.get('/').status_code==200;assert c.get('/sante').json=={"statut":"ok"}
def test_participants():
    a=app_test();c=a.test_client();assert present(c).status_code==302
    with a.app_context():assert Reponse.query.count()==1;assert Participant.query.count()==3;assert Participant.query.filter_by(allergies='Lactose').one().nom_prenom=='Paul Martin'
def test_validation_nom_participant():
    a=app_test();c=a.test_client();d={"csrf_token":token(c),"nom_prenom":"Marie Martin","telephone":"0600000000","presence":"oui","adultes":"2","enfants":"0","adulte_1_nom":"Marie Martin","adulte_2_nom":"","repas_classiques":"2","repas_vegetariens":"0","menus_enfants":"0","hebergement":"non","couchages":"0","brunch":"non","brunch_adultes":"0","brunch_enfants":"0"};assert c.post('/envoyer',data=d).status_code==400
def test_suppression_cascade_et_exports():
    a=app_test();c=a.test_client();present(c);c.get('/admin');
    with c.session_transaction() as s:csrf=s['csrf_token']
    c.post('/admin',data={'csrf_token':csrf,'utilisateur':'admin','mot_de_passe':'test-password'})
    assert c.get('/admin/export.xlsx').status_code==200;assert c.get('/admin/export.csv').status_code==200
    with c.session_transaction() as s:csrf=s['csrf_token']
    assert c.post('/admin/supprimer/1',data={'csrf_token':csrf}).status_code==302
    with a.app_context():assert Participant.query.count()==0
