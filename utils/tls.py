"""Certificat HTTPS du réseau local : création et empreinte

Un certificat auto-signé n'est reconnu par aucune autorité : le téléphone le
reconnaît à son empreinte SHA-256, transmise par le QR code de connexion, et
refuse tout autre certificat (épinglage).
"""

import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

# Durée de validité : au-delà, le certificat est à recréer, avec un nouveau scan.
VALIDITY_DAYS = 825


def build_subject_names(pHost):
    """Retourne les noms couverts : l'adresse du PC, localhost et 127.0.0.1."""

    vNames = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ]

    try:
        vNames.append(x509.IPAddress(ipaddress.ip_address(pHost)))
    except ValueError:
        vNames.append(x509.DNSName(pHost))

    rNames = vNames

    return rNames


def create_certificate(pHost, pCertificateFile, pKeyFile, pNow=None):
    """Crée une clé et un certificat auto-signé pour pHost ; retourne l'empreinte.

    La clé privée est écrite sans mot de passe : le serveur la lit au démarrage.
    Elle reste sur ce poste, dans data/, que git ignore.
    """

    vNow = pNow or datetime.now(timezone.utc)
    vKey = ec.generate_private_key(ec.SECP256R1())
    vName = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "JobBoard Perso")])

    vCertificate = (
        x509.CertificateBuilder()
        .subject_name(vName)
        .issuer_name(vName)
        .public_key(vKey.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(vNow - timedelta(minutes=5))
        .not_valid_after(vNow + timedelta(days=VALIDITY_DAYS))
        .add_extension(
            x509.SubjectAlternativeName(build_subject_names(pHost)), critical=False
        )
        .sign(vKey, hashes.SHA256())
    )

    Path(pCertificateFile).parent.mkdir(parents=True, exist_ok=True)
    Path(pKeyFile).write_bytes(
        vKey.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    Path(pCertificateFile).write_bytes(
        vCertificate.public_bytes(serialization.Encoding.PEM)
    )

    rFingerprint = vCertificate.fingerprint(hashes.SHA256()).hex()

    return rFingerprint


def read_fingerprint(pCertificateFile):
    """Retourne l'empreinte SHA-256 d'un certificat, ou None s'il est illisible."""

    try:
        vCertificate = x509.load_pem_x509_certificate(
            Path(pCertificateFile).read_bytes()
        )
    except (OSError, ValueError):
        return None

    rFingerprint = vCertificate.fingerprint(hashes.SHA256()).hex()

    return rFingerprint


def read_expiry(pCertificateFile):
    """Retourne la date de fin d'un certificat, à l'heure locale.

    Lève OSError ou ValueError si le fichier est absent ou illisible.
    """

    vCertificate = x509.load_pem_x509_certificate(Path(pCertificateFile).read_bytes())

    rExpiry = vCertificate.not_valid_after_utc.astimezone().replace(tzinfo=None)

    return rExpiry
