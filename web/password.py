"""Génère l'empreinte du mot de passe du tableau de bord : python -m web.password"""

import getpass
import secrets

from web.auth import hash_password

MIN_PASSWORD_LENGTH = 12


def main():
    """Demande le mot de passe et affiche les lignes à copier dans le fichier .env."""

    vPassword = getpass.getpass("Mot de passe du tableau de bord : ")

    if len(vPassword) < MIN_PASSWORD_LENGTH:
        print(f"Mot de passe trop court : {MIN_PASSWORD_LENGTH} caractères au moins.")
        return

    if getpass.getpass("Confirmation : ") != vPassword:
        print("Les deux saisies sont différentes.")
        return

    print("\nÀ copier dans le fichier .env :")
    print(f"WEB_PASSWORD_HASH={hash_password(vPassword)}")
    print(f"WEB_SESSION_SECRET={secrets.token_urlsafe(32)}")


if __name__ == "__main__":
    main()
