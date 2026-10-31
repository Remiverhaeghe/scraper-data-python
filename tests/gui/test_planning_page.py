"""Tests de la page Planning"""

from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt

from gui.planning_page import PlanningPage
from job.weekly_planning import load_planned_revisions
from storage.database import initialize_database


def test_revision_is_added_moved_then_removed(qt_application, tmp_path):
    """Vérifie l'ajout d'une révision, son déplacement, son retrait et les semaines."""

    vDatabaseFile = tmp_path / "scraper.db"
    initialize_database(vDatabaseFile)
    vPage = PlanningPage(vDatabaseFile)
    vPage.refresh()
    vMonday = date.today() - timedelta(days=date.today().weekday())

    assert len(vPage.lists) == 7
    assert vPage.week_label.text().startswith(f"Semaine du {vMonday:%d/%m}")

    vPage.add()

    assert vPage.message_label.text() == "Indiquez ce que vous comptez réviser."

    vPage.date_edit.setDate(QDate(vMonday.year, vMonday.month, vMonday.day))
    vPage.label_edit.setText("Schémas électriques")
    vPage.add()

    assert vPage.lists[0].item(0).text() == "Réviser : Schémas électriques"

    vRevisionId = vPage.lists[0].item(0).data(Qt.ItemDataRole.UserRole)
    vPage.lists[2].moved.emit(vRevisionId, vMonday + timedelta(days=2))

    assert vPage.lists[0].count() == 0 and vPage.lists[2].count() == 1
    assert load_planned_revisions(vDatabaseFile)[0]["day"] == str(
        vMonday + timedelta(days=2)
    )

    vOpened = []
    vPage.navigation_requested.connect(vOpened.append)
    vPage.lists[2].itemDoubleClicked.emit(vPage.lists[2].item(0))

    assert vOpened == ["quiz"]

    vPage.remove_selected()

    assert vPage.message_label.text().startswith("Choisissez d'abord")

    vPage.lists[2].setCurrentRow(0)
    vPage.remove_selected()

    assert load_planned_revisions(vDatabaseFile) == []

    vPage.change_week(7)

    assert vPage.week_label.text().startswith(
        f"Semaine du {vMonday + timedelta(days=7):%d/%m}"
    )

    vPage.change_week(None)

    assert vPage.day == date.today()
