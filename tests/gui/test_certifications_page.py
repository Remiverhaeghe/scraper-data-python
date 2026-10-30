"""Tests de la page Certifications et de la fenêtre d'une certification"""

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QMessageBox

import gui.certifications_page as certifications_page
from gui.certification_dialog import CertificationDialog
from gui.certifications_page import COLUMNS, OWNED_COLUMN, CertificationsPage
from job.certifications import CATALOG, load_details, load_owned
from storage.database import initialize_database


def find_row(pPage, pId):
    """Retourne l'index de la ligne affichant une certification."""

    rIndex = next(
        vIndex
        for vIndex in range(pPage.table.rowCount())
        if pPage.get_row(vIndex)["id"] == pId
    )

    return rIndex


def test_page_lists_and_toggles_certifications(qt_application, tmp_path, monkeypatch):
    """Vérifie le tableau, la case « Je l'ai » et l'ouverture de la fenêtre."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)

    vPage = CertificationsPage(vDatabaseFile)
    vPage.refresh()

    assert vPage.table.rowCount() == len(CATALOG)
    assert vPage.table.columnCount() == len(COLUMNS)

    vIndex = find_row(vPage, "sst")
    vPage.table.item(vIndex, OWNED_COLUMN).setCheckState(Qt.CheckState.Checked)

    assert load_owned(vDatabaseFile) == {"sst": date.today().isoformat()}
    assert (
        "Valide jusqu"
        in vPage.table.item(find_row(vPage, "sst"), len(COLUMNS) - 1).text()
    )

    vOpened = []
    monkeypatch.setattr(
        certifications_page.CertificationDialog,
        "exec",
        lambda pDialog: vOpened.append(pDialog.row["id"]) or 0,
    )
    vPage.open_details(find_row(vPage, "sst"), 0)

    assert vOpened == ["sst"]


def test_dialog_saves_details_and_refuses_bad_link(
    qt_application, tmp_path, monkeypatch
):
    """Vérifie l'enregistrement de l'organisme, de l'expiration et le lien refusé."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = CertificationsPage(vDatabaseFile)
    vPage.refresh()
    vRow = vPage.get_row(find_row(vPage, "caces-r489"))

    vDialog = CertificationDialog(vDatabaseFile, vRow)
    vDialog.owned_check.setChecked(True)
    vDialog.obtained_edit.setDate(QDate(2025, 3, 4))
    vDialog.expires_check.setChecked(True)
    vDialog.expires_edit.setDate(QDate(2030, 3, 4))
    vDialog.fields["organism"].setText("Afpa")
    vDialog.fields["level"].setText("Catégories 1A et 3")
    vDialog.save()

    assert load_owned(vDatabaseFile) == {"caces-r489": "2025-03-04"}
    assert load_details(vDatabaseFile)["caces-r489"] == {
        "organism": "Afpa",
        "level": "Catégories 1A et 3",
        "expires": "2030-03-04",
    }

    vWarnings = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *pArgs: vWarnings.append(pArgs[2])
    )
    vDialog.fields["verify_link"].setText("javascript:alert(1)")
    vDialog.save()

    assert vWarnings == ["Le lien de vérification doit commencer par https://."]
