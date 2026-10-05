from getpass import getpass
from werkzeug.security import generate_password_hash

mot_de_passe = getpass("Saisissez le mot de passe administrateur : ")
confirmation = getpass("Confirmez le mot de passe : ")
if mot_de_passe != confirmation:
    raise SystemExit("Les mots de passe ne correspondent pas.")
if len(mot_de_passe) < 12:
    raise SystemExit("Utilisez au moins 12 caractères.")
print("\nCopiez cette valeur dans ADMIN_PASSWORD_HASH :\n")
print(generate_password_hash(mot_de_passe))
