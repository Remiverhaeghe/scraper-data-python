"""Fenêtres d'information : mentions légales et licence"""

from html import escape

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

from config import APPLICATION_NAME
from job.presentation import build_legal_sections, read_license


def show_text_dialog(pParent, pTitle, pHtml=None, pText=None):
    """Affiche un texte long dans une fenêtre défilante."""

    vBrowser = QTextBrowser()

    if pHtml is not None:
        vBrowser.setHtml(pHtml)
    else:
        vBrowser.setPlainText(pText)

    vButtons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)

    vDialog = QDialog(pParent)
    vDialog.setWindowTitle(pTitle)
    vDialog.resize(760, 560)
    vButtons.rejected.connect(vDialog.reject)

    vLayout = QVBoxLayout(vDialog)
    vLayout.addWidget(vBrowser)
    vLayout.addWidget(vButtons)

    vDialog.exec()


def show_legal_notice(pParent):
    """Affiche les mentions légales, avec le même texte que sur le web."""

    show_text_dialog(
        pParent,
        "Mentions légales",
        pHtml="".join(
            f"<h3>{escape(vTitle)}</h3><p>{escape(vText)}</p>"
            for vTitle, vText in build_legal_sections(APPLICATION_NAME)
        ),
    )


def show_license(pParent):
    """Affiche la licence du projet, lue dans le fichier LICENSE."""

    show_text_dialog(pParent, "Licence", pText=read_license())
