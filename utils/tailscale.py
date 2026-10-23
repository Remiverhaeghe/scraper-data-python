"""Certificat Tailscale du tableau de bord : demande et renouvellement

Tailscale délivre gratuitement un certificat Let's Encrypt de 90 jours pour le
nom du poste sur son réseau (serveur.xxx.ts.net), reconnu par tous les appareils.
"""

import json
import shutil

# Lance la seule commande tailscale, trouvée par shutil.which, sans shell.
import subprocess  # nosec B404
from datetime import timedelta

from utils.logger import get_logger
from utils.tls import read_expiry

logger = get_logger(__name__)

COMMAND_TIMEOUT = 120

# Renouvellement un mois avant la fin, comme le conseille Let's Encrypt
RENEWAL_MARGIN = timedelta(days=30)

TAILSCALE_DOMAIN = ".ts.net"


def run_tailscale(pArguments):
    """Lance une commande tailscale ; retourne sa sortie, lève RuntimeError en échec."""

    vExecutable = shutil.which("tailscale")

    if vExecutable is None:
        raise RuntimeError(
            "Tailscale n'est pas installé sur ce poste : https://tailscale.com/download"
        )

    # Arguments en liste, sans shell : rien n'est interprété par un interpréteur.
    try:
        vResult = subprocess.run(  # nosec B603
            [vExecutable, *pArguments],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
            check=False,
        )

    except subprocess.TimeoutExpired as vException:
        raise RuntimeError(f"tailscale {pArguments[0]} ne répond pas") from vException

    if vResult.returncode != 0:
        raise RuntimeError(
            f"tailscale {pArguments[0]} a échoué : {vResult.stderr.strip()}"
        )

    rOutput = vResult.stdout

    return rOutput


def read_server_identity():
    """Retourne le nom de ce poste sur le réseau Tailscale et son adresse IPv4."""

    vSelf = json.loads(run_tailscale(["status", "--json"])).get("Self") or {}
    vName = vSelf.get("DNSName", "").rstrip(".")
    vAddress = next(
        (vIp for vIp in vSelf.get("TailscaleIPs") or [] if "." in vIp), None
    )

    if not vName or not vAddress:
        raise RuntimeError(
            "Nom Tailscale inconnu : connecter ce poste (tailscale up) et activer "
            "MagicDNS dans la console d'administration."
        )

    rIdentity = (vName, vAddress)

    return rIdentity


def request_certificate(pName, pCertificateFile, pKeyFile):
    """Demande à Tailscale le certificat de pName, écrit dans les deux fichiers."""

    run_tailscale(
        [
            "cert",
            "--cert-file",
            str(pCertificateFile),
            "--key-file",
            str(pKeyFile),
            pName,
        ]
    )

    logger.info("Certificat Tailscale reçu pour %s", pName)


def renew_certificate_if_due(pName, pCertificateFile, pKeyFile, pNow):
    """Renouvelle le certificat d'un nom Tailscale à un mois de sa fin.

    Retourne True s'il a été renouvelé. Un échec est journalisé : le certificat
    actuel reste en place et le renouvellement est retenté au tour suivant.
    """

    if not pName or not pName.endswith(TAILSCALE_DOMAIN):
        return False

    try:
        if read_expiry(pCertificateFile) - pNow > RENEWAL_MARGIN:
            return False

    except (OSError, ValueError):
        logger.warning("Certificat du tableau de bord illisible : nouvelle demande")

    try:
        request_certificate(pName, pCertificateFile, pKeyFile)

    except (RuntimeError, OSError) as vException:
        logger.warning("Certificat Tailscale non renouvelé : %s", vException)
        return False

    return True
