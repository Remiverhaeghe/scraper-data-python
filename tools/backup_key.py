"""Création de la clé de chiffrement des copies du NAS

    python -m tools.backup_key

Affiche une nouvelle clé à copier dans le .env (BACKUP_ENCRYPTION_KEY). Gardez-la
aussi hors du PC et du NAS, dans un gestionnaire de mots de passe : sans elle,
les copies chiffrées ne peuvent plus être restaurées.
"""

import sys

from cryptography.fernet import Fernet


def main():
    """Affiche une clé neuve et la ligne à ajouter au .env."""

    print(
        "Ajouter au .env, puis la garder aussi dans un gestionnaire de mots de passe :"
    )
    print(f"  BACKUP_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
    print("Une copie chiffrée ne se restaure qu'avec cette clé.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
