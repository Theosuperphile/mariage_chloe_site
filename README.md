# Mariage Chloé et Khaled · Version 1.0.0

Application complète de réponse au mariage, prévue pour l’adresse `https://mariage-chloe.onrender.com`.

## Fonctions incluses

- formulaire responsive pour smartphone, tablette et PC ;
- un seul QR code pour tous les invités ;
- nom, prénom et téléphone ;
- présence, adultes, enfants, repas, allergies, hébergement et brunch ;
- affichage dynamique des questions ;
- contrôles de cohérence côté navigateur et côté serveur ;
- tableau de bord privé ;
- détection visuelle des numéros de téléphone en doublon ;
- exports Excel et CSV ;
- téléchargement du QR code depuis l’administration ;
- protection CSRF, mot de passe haché, cookie sécurisé en production et piège anti-robot.

# Mise en route locale

## 1. Installer Python

Utiliser Python 3.11 ou plus récent.

## 2. Ouvrir un terminal dans le dossier

Sous Windows : clic droit dans le dossier, puis ouvrir dans le Terminal.

## 3. Créer l’environnement et installer les dépendances

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Générer le mot de passe administrateur

```powershell
python generer_mot_de_passe.py
```

Copier la longue valeur affichée.

## 5. Définir les variables pour l’essai local

Dans PowerShell :

```powershell
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD_HASH="COLLER_ICI_LA_LONGUE_VALEUR"
$env:SECRET_KEY="une-cle-secrete-tres-longue-et-aleatoire"
python app.py
```

Ouvrir ensuite :

- formulaire : `http://127.0.0.1:5000`
- administration : `http://127.0.0.1:5000/admin`

En local, les réponses sont enregistrées dans `instance/mariage.db`.

# Déploiement sur Render

## 1. Créer un dépôt GitHub privé

Créer un nouveau dépôt privé, puis déposer tout le contenu de ce dossier à la racine du dépôt.

## 2. Créer le service avec le Blueprint

1. Créer un compte Render.
2. Dans le tableau de bord Render, choisir **New > Blueprint**.
3. Connecter le dépôt GitHub.
4. Render détecte automatiquement le fichier `render.yaml`.
5. Lancer la création du service et de la base PostgreSQL.

## 3. Créer le mot de passe administrateur

Sur un ordinateur, exécuter :

```powershell
python generer_mot_de_passe.py
```

Copier la valeur obtenue.

Dans Render, ouvrir le service web, puis **Environment** et renseigner :

```text
ADMIN_PASSWORD_HASH = valeur copiée
```

`ADMIN_USERNAME` vaut déjà `admin`, mais peut être modifié.

## 4. Vérifier l’adresse

Render tentera d’utiliser :

```text
https://mariage-chloe.onrender.com
```

Le nom doit être disponible. Si Render attribue une autre adresse, modifier `APP_BASE_URL` dans les variables d’environnement avant de télécharger le QR code.

## 5. Tester avant diffusion

1. Ouvrir le formulaire sur un téléphone.
2. Envoyer une réponse d’essai.
3. Ouvrir `/admin`.
4. Vérifier les totaux.
5. Télécharger l’Excel.
6. Télécharger le QR code.
7. Scanner le QR code avec plusieurs téléphones.
8. Supprimer les réponses d’essai depuis le tableau de bord.

# Utilisation quotidienne

- Les invités utilisent uniquement l’adresse principale ou le QR code.
- L’administration est disponible sur `/admin`.
- Les boutons **Excel** et **CSV** téléchargent une sauvegarde des réponses.
- Le bouton **QR code** produit un PNG prêt à insérer sur le faire-part.
- Une ligne jaune « Doublon possible » signale plusieurs réponses avec le même numéro.

# Personnalisation

Les informations présentes dans l’en-tête se trouvent dans :

```text
templates/index.html
```

Modifier notamment :

```html
Samedi 24 avril 2027
15 h 30 · 220 rue du Stade · 88220 Hadol
```

Les couleurs sont dans :

```text
static/css/style.css
```

La couleur principale est définie par `--orange` au début du fichier.

# Sauvegarde et confidentialité

- Télécharger régulièrement l’export Excel depuis l’administration.
- Ne jamais envoyer le mot de passe administrateur aux invités.
- Ne jamais publier le fichier `.env` ni la valeur de `ADMIN_PASSWORD_HASH`.
- Les réponses contiennent des numéros de téléphone. Elles doivent être utilisées uniquement pour l’organisation du mariage et supprimées lorsqu’elles ne sont plus nécessaires.

# Vérifications réalisées

- tests automatiques du formulaire présent et absent ;
- contrôle des quantités de repas ;
- connexion administrateur ;
- export Excel ;
- génération du QR code ;
- point de contrôle de santé pour Render ;
- syntaxe Python compilée ;
- rendu HTML vérifié sur plusieurs largeurs par capture automatisée si Chromium est disponible.
