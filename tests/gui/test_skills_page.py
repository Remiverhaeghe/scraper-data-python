"""Tests de la page des compétences"""

from datetime import datetime

import pandas as pd
from PySide6.QtWidgets import QPushButton

from gui.skills_page import SkillsPage
from storage.database import initialize_database
from storage.job_offers import save_offers


def test_skills_page_shows_rows_and_actions(qt_application, tmp_path):
    """Vérifie le tableau, les chiffres clés et les signaux des actions."""

    vDatabaseFile = tmp_path / "scraper.db"

    initialize_database(vDatabaseFile)
    save_offers(
        vDatabaseFile,
        pd.DataFrame(
            [
                {
                    "source": "a",
                    "source_id": "1",
                    "title": "Dev",
                    "skills": '["python"]',
                },
                {"source": "a", "source_id": "2", "title": "Dev", "skills": '["AWS"]'},
            ]
        ),
        datetime(2026, 10, 16),
    )

    vPage = SkillsPage(vDatabaseFile)
    vRevised = []
    vPrepared = []
    vPage.revise_requested.connect(vRevised.append)
    vPage.generation_requested.connect(vPrepared.append)
    vPage.refresh()

    vSkills = {vPage.table.item(vRow, 0).text(): vRow for vRow in range(2)}

    assert set(vSkills) == {"Python", "AWS"}
    assert vPage.statistic_cards["covered"].value_label.text() == "1 / 2"

    for vSkill in ("Python", "AWS"):
        vPage.table.cellWidget(vSkills[vSkill], 6).findChild(QPushButton).click()

    assert vRevised == ["python"]
    assert vPrepared == ["Cloud et infrastructure (AWS, Azure)"]
