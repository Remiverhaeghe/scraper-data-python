"""Tests de la carte des récompenses, du son de réussite et de l'accent du thème"""

import wave

from PySide6.QtWidgets import QPushButton

from gui.rewards_card import RewardsCard
from gui.sounds import NOTES, SAMPLE_RATE, build_chime, write_chime
from gui.theme import COLORS, apply_theme
from job.cosmetics import build_cosmetics_view, load_cosmetics
from storage.database import initialize_database


def test_card_shows_locked_rewards_and_saves_choices(qt_application, tmp_path):
    """Vérifie les récompenses verrouillées, un choix refusé, le son coupé."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vCard = RewardsCard(vDatabaseFile)
    vChanged = []
    vCard.changed.connect(lambda: vChanged.append(True))
    vCard.set_view(build_cosmetics_view(vDatabaseFile, 1))
    vButtons = {vButton.text(): vButton for vButton in vCard.findChildren(QPushButton)}

    assert vButtons["✓ Bleu atelier"].isEnabled()
    assert not vButtons["Vert sécurité · niveau 2"].isEnabled()

    vCard.choose("accent", "vert")

    assert vCard.message_label.text() == "Débloqué au niveau 2." and vChanged == []

    vCard.choose("accent", "bleu")
    vCard.sounds_check.setChecked(False)

    assert vChanged == [True]
    assert load_cosmetics(vDatabaseFile)["sounds"] is False


def test_chime_is_written_once_as_a_short_wav(tmp_path):
    """Vérifie le carillon : WAV mono 16 bits, durée des deux notes."""

    vPath = write_chime(tmp_path / "chime.wav")

    with wave.open(str(vPath)) as vFile:
        assert (vFile.getnchannels(), vFile.getsampwidth()) == (1, 2)
        assert vFile.getnframes() == len(build_chime()) // 2
        assert vFile.getnframes() == sum(
            int(SAMPLE_RATE * vDuration) for _, vDuration in NOTES
        )

    assert write_chime(vPath) == vPath


def test_accent_recolours_the_theme(qt_application):
    """Vérifie que l'accent remplace la couleur principale, puis le retour au bleu."""

    apply_theme(qt_application, "light", pAccent="orange")

    assert COLORS["primary"] == "#C2410C"

    apply_theme(qt_application, "light")

    assert COLORS["primary"] == "#155FCC"
