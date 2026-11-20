"""Tests de la connexion du téléphone par code à 6 chiffres"""

from datetime import datetime, timedelta

from job.mobile_pairing import (
    PAIRING_MAX_ATTEMPTS,
    create_pairing_code,
    format_pairing_code,
    redeem_pairing_code,
)
from job.mobile_sync import get_mobile_token, renew_mobile_token
from storage.database import initialize_database
from storage.settings_repository import get_setting_values

NOW = datetime(2026, 11, 20, 10, 0)


def build_database(pTmpPath):
    """Crée une base vide."""

    rDatabaseFile = pTmpPath / "scraper.db"
    initialize_database(rDatabaseFile)

    return rDatabaseFile


def test_code_is_six_digits_and_only_its_hash_is_stored(tmp_path):
    vDatabaseFile = build_database(tmp_path)

    vCode = create_pairing_code(vDatabaseFile, NOW)

    assert len(vCode) == 6 and vCode.isdigit()
    assert vCode not in str(get_setting_values(vDatabaseFile))
    assert format_pairing_code("482913") == "482 913"


def test_valid_code_gives_the_existing_token_once(tmp_path):
    vDatabaseFile = build_database(tmp_path)
    vToken = renew_mobile_token(vDatabaseFile)
    vCode = create_pairing_code(vDatabaseFile, NOW)

    # Espaces tapés comme affichés : ils ne comptent pas
    assert redeem_pairing_code(vDatabaseFile, format_pairing_code(vCode), NOW) == vToken
    assert redeem_pairing_code(vDatabaseFile, vCode, NOW) is None


def test_token_is_created_when_none_exists(tmp_path):
    vDatabaseFile = build_database(tmp_path)
    vCode = create_pairing_code(vDatabaseFile, NOW)

    vToken = redeem_pairing_code(vDatabaseFile, vCode, NOW)

    assert vToken and vToken == get_mobile_token(vDatabaseFile)


def test_expired_code_is_refused(tmp_path):
    vDatabaseFile = build_database(tmp_path)
    vCode = create_pairing_code(vDatabaseFile, NOW)

    assert (
        redeem_pairing_code(vDatabaseFile, vCode, NOW + timedelta(minutes=11)) is None
    )


def test_code_falls_after_five_wrong_attempts(tmp_path):
    vDatabaseFile = build_database(tmp_path)
    vCode = create_pairing_code(vDatabaseFile, NOW)
    vWrong = f"{(int(vCode) + 1) % 1000000:06d}"

    for _ in range(PAIRING_MAX_ATTEMPTS):
        assert redeem_pairing_code(vDatabaseFile, vWrong, NOW) is None

    assert redeem_pairing_code(vDatabaseFile, vCode, NOW) is None


def test_new_code_replaces_the_previous_one(tmp_path):
    vDatabaseFile = build_database(tmp_path)
    vFirst = create_pairing_code(vDatabaseFile, NOW)
    vSecond = create_pairing_code(vDatabaseFile, NOW)

    if vFirst != vSecond:
        assert redeem_pairing_code(vDatabaseFile, vFirst, NOW) is None
    assert redeem_pairing_code(vDatabaseFile, vSecond, NOW)
