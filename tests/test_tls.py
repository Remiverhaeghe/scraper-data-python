"""Tests du certificat HTTPS du réseau local"""

import json

from cryptography import x509

import job.mobile_sync as mobile_sync
from utils.tls import create_certificate, read_fingerprint


def test_certificate_covers_the_pc_address_and_gives_its_fingerprint(tmp_path):
    """Vérifie le certificat créé pour l'adresse du PC et son empreinte relue."""

    vCertificate = tmp_path / "tls" / "certificate.pem"
    vKey = tmp_path / "tls" / "private-key.pem"

    vFingerprint = create_certificate("192.168.1.80", vCertificate, vKey)

    vNames = (
        x509.load_pem_x509_certificate(vCertificate.read_bytes())
        .extensions.get_extension_for_class(x509.SubjectAlternativeName)
        .value
    )

    assert "192.168.1.80" in [
        str(vAddress) for vAddress in vNames.get_values_for_type(x509.IPAddress)
    ]
    assert len(vFingerprint) == 64
    assert read_fingerprint(vCertificate) == vFingerprint
    assert read_fingerprint(tmp_path / "absent.pem") is None
    assert b"PRIVATE KEY" in vKey.read_bytes()


def test_qr_code_carries_the_certificate_fingerprint_in_https(monkeypatch):
    """Vérifie que l'empreinte n'est ajoutée au QR code qu'en HTTPS."""

    vPayloads = []
    monkeypatch.setattr(
        mobile_sync.segno, "make", lambda pData, error: vPayloads.append(pData)
    )

    mobile_sync.build_connection_qr("https://pc:8000/api/v1", "jeton", "ab12")
    mobile_sync.build_connection_qr("http://pc:8000/api/v1", "jeton")

    assert json.loads(vPayloads[0])["certificate_sha256"] == "ab12"
    assert "certificate_sha256" not in json.loads(vPayloads[1])
