"""Fenêtres d'information : mentions légales et licence"""

from html import escape

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

from config import APPLICATION_NAME
from job.presentation import (
    LICENSE_SUMMARY,
    LICENSE_SUMMARY_NOTE,
    build_legal_sections,
    read_license,
)


def show_text_dialog(pParent, pTitle, pHtml=None, pText=None):
    """Affiche un texte long dans une fenêtre défilante."""

    vBrowser = QTextBrowser()

    if pHtml is not None:
        vBrowser.setHtml(pHtml)
    else:
        vBrowser.setPlainText(pText)

    vButtons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    vButtons.button(QDialogButtonBox.StandardButton.Close).setText("Fermer")

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

    vSummary = "".join(f"<li>{escape(vPoint)}</li>" for vPoint in LICENSE_SUMMARY)

    show_text_dialog(
        pParent,
        "Licence",
        pHtml=(
            f"<h3>En résumé</h3><p><i>{escape(LICENSE_SUMMARY_NOTE)}</i></p>"
            f"<ul>{vSummary}</ul><h3>Texte officiel</h3>"
            f"<pre style='white-space: pre-wrap'>{escape(read_license())}</pre>"
        ),
    )
