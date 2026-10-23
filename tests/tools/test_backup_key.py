"""Tests de la création de la clé de chiffrement des copies du NAS"""

from cryptography.fernet import Fernet

from tools.backup_key import main


def test_new_key_is_printed_ready_for_the_env(capsys):
    """Vérifie la ligne du .env et une clé utilisable."""

    assert main() == 0

    vLine = next(
        vLine for vLine in capsys.readouterr().out.splitlines() if "=" in vLine
    )
    vKey = vLine.split("=", 1)[1].strip()

    assert vLine.strip().startswith("BACKUP_ENCRYPTION_KEY=")
    assert Fernet(vKey).decrypt(Fernet(vKey).encrypt(b"test")) == b"test"
