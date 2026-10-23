"""Tests du rechargement à chaud du certificat du tableau de bord"""

import os
import socket
import ssl
import threading

from cryptography import x509
from cryptography.hazmat.primitives import hashes

from utils.tls import create_certificate
from web.__main__ import reload_certificate


def read_served_fingerprint(pContext):
    """Retourne l'empreinte du certificat présenté par un serveur TLS local."""

    with socket.create_server(("127.0.0.1", 0)) as vServer:
        vPort = vServer.getsockname()[1]

        def answer():
            vConnection, _ = vServer.accept()

            # Le client ferme dès le certificat lu : la fin de connexion est ignorée.
            try:
                with pContext.wrap_socket(vConnection, server_side=True):
                    pass

            except OSError:
                vConnection.close()

        vThread = threading.Thread(target=answer, daemon=True)
        vThread.start()

        vClient = ssl.create_default_context()
        vClient.check_hostname = False
        vClient.verify_mode = ssl.CERT_NONE

        with socket.create_connection(("127.0.0.1", vPort)) as vSocket:
            with vClient.wrap_socket(vSocket) as vSecured:
                vDer = vSecured.getpeercert(binary_form=True)

        vThread.join(timeout=5)

    rFingerprint = (
        x509.load_der_x509_certificate(vDer).fingerprint(hashes.SHA256()).hex()
    )

    return rFingerprint


def test_renewed_certificate_is_served_without_restart(tmp_path):
    """Vérifie que les connexions suivantes reçoivent le certificat renouvelé."""

    vCertificate = tmp_path / "certificate.pem"
    vKey = tmp_path / "key.pem"
    vFirst = create_certificate("127.0.0.1", vCertificate, vKey)
    vContext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    vContext.load_cert_chain(vCertificate, vKey)
    vModified = vCertificate.stat().st_mtime

    assert read_served_fingerprint(vContext) == vFirst
    assert reload_certificate(vContext, vCertificate, vKey, vModified) == vModified

    vSecond = create_certificate("127.0.0.1", vCertificate, vKey)
    os.utime(vCertificate, (vModified + 60, vModified + 60))

    assert reload_certificate(vContext, vCertificate, vKey, vModified) == vModified + 60
    assert read_served_fingerprint(vContext) == vSecond
