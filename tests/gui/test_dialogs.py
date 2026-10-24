"""Tests des fenêtres communes : préparation d'une candidature et lettre"""

from PySide6.QtWidgets import QPushButton

import gui.dialogs as dialogs

PREPARATION = {
    "match": {"covered": ["Python"], "missing": [], "score": 100, "details": []},
    "cv": None,
    "interview": {
        "strengths": [],
        "gaps": [],
        "answers": [],
        "questions": ["Question ?"],
    },
    "letter": "Madame, Monsieur,",
}


def test_preparation_letter_is_copied_then_saved(qt_application, tmp_path, monkeypatch):
    """Vérifie la lettre copiée puis enregistrée en Word, et l'échec signalé."""

    vTarget = tmp_path / "lettre.docx"
    vOpened = []
    vWarnings = []

    def click_buttons(pDialog):
        for vButton in pDialog.findChildren(QPushButton):
            if vButton.text() in ("Copier la lettre", "Enregistrer en Word"):
                vButton.click()

        return 0

    monkeypatch.setattr(dialogs.QDialog, "exec", click_buttons)
    monkeypatch.setattr(
        dialogs.QFileDialog, "getSaveFileName", lambda *_: (str(vTarget), "")
    )
    monkeypatch.setattr(
        dialogs.QDesktopServices, "openUrl", lambda pUrl: vOpened.append(pUrl)
    )
    monkeypatch.setattr(
        dialogs.QMessageBox, "warning", lambda *pArgs: vWarnings.append(pArgs[2])
    )

    dialogs.show_preparation(None, "Dev Python", PREPARATION)

    assert qt_application.clipboard().text() == "Madame, Monsieur,"
    assert vTarget.read_bytes().startswith(b"PK")
    assert len(vOpened) == 1

    vTarget = tmp_path / "absent" / "lettre.docx"
    dialogs.save_letter(None, "Dev Python", "Texte")

    assert vWarnings[0].startswith("Enregistrement impossible")


def test_letter_is_not_saved_without_a_file(qt_application, monkeypatch, tmp_path):
    """Vérifie qu'annuler le choix du fichier n'écrit rien."""

    monkeypatch.setattr(dialogs.QFileDialog, "getSaveFileName", lambda *_: ("", ""))
    monkeypatch.chdir(tmp_path)

    dialogs.save_letter(None, "Dev", "Texte")

    assert not list(tmp_path.iterdir())


def test_text_dialogs_show_legal_notice_and_license(qt_application, monkeypatch):
    """Vérifie le texte affiché par les mentions légales, la licence et un texte brut."""

    vShown = []

    def remember(pDialog):
        vShown.append(
            (
                pDialog.windowTitle(),
                pDialog.findChild(dialogs.QTextBrowser).toPlainText(),
            )
        )

        return 0

    monkeypatch.setattr(dialogs.QDialog, "exec", remember)

    dialogs.show_legal_notice(None)
    dialogs.show_license(None)
    dialogs.show_text_dialog(None, "Notes", pText="Texte <brut>")

    assert [vTitle for vTitle, _ in vShown] == ["Mentions légales", "Licence", "Notes"]
    assert "Lucide" in vShown[1][1]
    assert vShown[2][1] == "Texte <brut>"
