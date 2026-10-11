"""Tests de la page des logs"""

import gui.logs_page as logs_page
from gui.logs_page import LogsPage
from gui.theme import COLORS

ENTRIES = [
    {
        "time": "2026-10-10 09:00:00",
        "level": "ERROR",
        "level_label": "Erreur",
        "module": "web.app",
        "message": "Erreur inattendue\nTraceback détaillé",
    },
    {
        "time": "2026-10-10 08:00:00",
        "level": "INFO",
        "level_label": "Information",
        "module": "job.application",
        "message": "Début du traitement",
    },
]


def test_logs_page_shows_filtered_entries(qt_application, monkeypatch):
    """Vérifie les filtres transmis, l'affichage et la trace en infobulle."""

    vCalls = []

    def fake_read(pLevel=None, pSearch=None):
        vCalls.append((pLevel, pSearch))
        return ENTRIES

    monkeypatch.setattr(logs_page, "read_log_entries", fake_read)

    vPage = LogsPage()
    vPage.level_combo.setCurrentIndex(vPage.level_combo.findData("ERROR"))
    vPage.search_edit.setText("  web  ")
    vPage.refresh()

    vMessage = vPage.table.item(0, 3)

    assert vCalls[-1] == ("ERROR", "web")
    assert vPage.table.rowCount() == 2
    assert vMessage.text() == "Erreur inattendue"
    assert vMessage.toolTip() == "Erreur inattendue\nTraceback détaillé"
    assert (
        vPage.table.item(0, 1).foreground().color().name() == COLORS["danger"].lower()
    )
    assert vPage.message_label.text().startswith("2 entrée(s)")


def test_logs_page_reports_unreadable_files(qt_application, monkeypatch):
    """Vérifie le message affiché lorsque les fichiers ne peuvent être lus."""

    def refuse(**pArgs):
        raise OSError("accès refusé")

    monkeypatch.setattr(logs_page, "read_log_entries", refuse)

    vPage = LogsPage()
    vPage.refresh()

    assert vPage.table.rowCount() == 0
    assert "n'ont pas pu être lus" in vPage.message_label.text()
