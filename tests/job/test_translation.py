"""Tests de la traduction hors ligne des descriptions"""

from types import SimpleNamespace

import pytest

import job.translation as translation
from job.translation import can_translate, detect_language, translate_to_french
from storage.database import initialize_database

GERMAN = "Wir suchen dich für unser Team.\n\nDu arbeitest mit Java."


class FakeArgos:
    """Remplace Argos : préfixe chaque paragraphe par sa paire de langues."""

    def __init__(self, pCodes):
        self.codes = pCodes
        self.calls = []

    def get_installed_languages(self):
        """Retourne les langues installées, comme Argos."""
        rLanguages = [SimpleNamespace(code=vCode) for vCode in self.codes]

        return rLanguages

    def translate(self, pText, pFrom, pTo):
        """Simule la traduction d'un paragraphe."""
        self.calls.append(pText)

        rText = f"[{pFrom}>{pTo}] {pText}"

        return rText


@pytest.fixture(name="fake_argos")
def fixture_fake_argos(monkeypatch):
    """Installe un faux Argos avec les modèles allemand, anglais et français."""

    vArgos = FakeArgos({"de", "en", "fr"})
    monkeypatch.setattr(translation, "load_argos", lambda: vArgos)
    translation.get_installed_codes.cache_clear()
    translation.translate_to_french.cache_clear()

    yield vArgos

    translation.get_installed_codes.cache_clear()
    translation.translate_to_french.cache_clear()


@pytest.mark.parametrize(
    "pText, pLanguage",
    [
        (GERMAN, "de"),
        ("We are looking for a developer to join our team", "en"),
        ("12 345", None),
    ],
)
def test_detect_language(pText, pLanguage):
    """Vérifie la reconnaissance de la langue par ses mots fréquents."""

    assert detect_language(pText) == pLanguage


def test_translation_keeps_paragraphs(fake_argos):
    """Vérifie la traduction paragraphe par paragraphe, lignes vides gardées."""

    assert can_translate(GERMAN)
    assert translate_to_french(GERMAN) == (
        "[de>fr] Wir suchen dich für unser Team.\n\n[de>fr] Du arbeitest mit Java."
    )
    assert len(fake_argos.calls) == 2


def test_translation_unavailable_without_models(monkeypatch):
    """Vérifie le refus clair quand Argos ou le modèle de la langue manque."""

    monkeypatch.setattr(translation, "load_argos", lambda: None)
    translation.get_installed_codes.cache_clear()

    assert not can_translate(GERMAN)

    with pytest.raises(ValueError, match="indisponible"):
        translate_to_french(GERMAN)

    translation.get_installed_codes.cache_clear()


def test_german_needs_the_english_model(monkeypatch):
    """Vérifie que l'allemand exige aussi l'anglais, langue de passage."""

    monkeypatch.setattr(translation, "load_argos", lambda: FakeArgos({"de", "fr"}))
    translation.get_installed_codes.cache_clear()

    assert not can_translate(GERMAN)

    translation.get_installed_codes.cache_clear()


def test_translation_is_kept_in_the_database(fake_argos, tmp_path):
    """Vérifie qu'une description traduite une fois n'est plus recalculée."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vFirst = translation.translate_with_cache(vDatabaseFile, GERMAN)
    translation.translate_to_french.cache_clear()
    vSecond = translation.translate_with_cache(vDatabaseFile, GERMAN)

    assert vFirst == vSecond
    assert len(fake_argos.calls) == 2
