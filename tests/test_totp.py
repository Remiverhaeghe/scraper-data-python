"""Tests des codes à usage unique de la double authentification"""

import base64

from utils.totp import (
    build_provisioning_uri,
    compute_code,
    find_code_step,
    generate_secret,
)

# Secret des vecteurs de test de la RFC 6238 (SHA-1)
RFC_SECRET = base64.b32encode(b"12345678901234567890").decode("ascii")


def test_codes_match_the_rfc_vectors():
    """Vérifie les codes des vecteurs officiels, sur 6 chiffres."""

    assert compute_code(RFC_SECRET, 59 // 30) == "287082"
    assert compute_code(RFC_SECRET, 1111111109 // 30) == "081804"
    assert compute_code(RFC_SECRET, 1234567890 // 30) == "005924"


def test_code_is_accepted_around_its_period_only():
    """Vérifie la tolérance d'un pas de 30 secondes, et le refus au-delà."""

    vCode = compute_code(RFC_SECRET, 1000)

    assert find_code_step(RFC_SECRET, vCode, 1000 * 30 + 10) == 1000
    assert find_code_step(RFC_SECRET, vCode[:3] + " " + vCode[3:], 1001 * 30) == 1000
    assert find_code_step(RFC_SECRET, vCode, 1003 * 30) is None
    assert find_code_step(RFC_SECRET, "000000", 1000 * 30) is None


def test_secret_and_uri_for_the_application():
    """Vérifie le secret en base 32 et l'adresse lue par l'application."""

    vSecret = generate_secret()

    assert len(vSecret) == 32
    assert build_provisioning_uri(vSecret, "admin", "JobBoard Perso").startswith(
        "otpauth://totp/JobBoard%20Perso:admin?secret="
    )
