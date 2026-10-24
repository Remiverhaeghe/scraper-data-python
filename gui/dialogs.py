"""Fenêtres d'information : mentions légales, licence et préparation de candidature"""

from html import escape
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from config import APPLICATION_NAME
from job.cv_export import build_file_name, write_letter_docx
from job.preparation import describe_missing, describe_score
from job.presentation import (
    LICENSE_SUMMARY,
    LICENSE_SUMMARY_NOTE,
    build_legal_sections,
    read_icons_license,
    read_license,
)


def show_text_dialog(pParent, pTitle, pHtml=None, pText=None):
    """Affiche un texte long dans une fenêtre défilante."""

    vBrowser = QTextBrowser()
    # Un lien s'ouvre dans le navigateur plutôt que dans la fenêtre elle-même.
    vBrowser.setOpenExternalLinks(True)

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
            "<h3>Licence des icônes Lucide (ISC)</h3>"
            f"<pre style='white-space: pre-wrap'>{escape(read_icons_license())}</pre>"
        ),
    )


def describe_preparation(pPreparation):
    """Met en forme la correspondance, le CV et l'entretien en HTML."""

    vMatch = pPreparation["match"]
    vInterview = pPreparation["interview"]

    def items(pValues):
        rHtml = "".join(f"<li>{escape(vValue)}</li>" for vValue in pValues)

        return rHtml

    vScore = (
        f"{vMatch['score']} % des compétences repérées dans l'offre"
        if vMatch["score"] is not None
        else "aucune compétence technique repérée dans l'offre"
    )

    vStrengths = "".join(
        f"<li><b>{escape(vStrength['skill'])}</b>"
        + (f"<ul>{items(vStrength['examples'])}</ul>" if vStrength["examples"] else "")
        + "</li>"
        for vStrength in vInterview["strengths"]
    )

    vAnswers = "".join(
        f"<li><b>{escape(vAnswer['question'])}</b><br>{escape(vAnswer['hint'])}</li>"
        for vAnswer in vInterview["answers"]
    )

    vStar = "".join(
        f"<li><b>{escape(vAnswer['question'])}</b>"
        + (
            f" <i>({escape(', '.join(vAnswer['skills']))})</i>"
            if vAnswer["skills"]
            else ""
        )
        + f"<br>{escape(vAnswer['text']).replace(chr(10), '<br>')}</li>"
        for vAnswer in vInterview.get("star", [])
    )

    rHtml = (
        f"<h3>Correspondance</h3><p>{escape(vScore)}</p>"
        f"<p>Couvertes : {escape(', '.join(vMatch['covered']) or 'aucune')}<br>"
        f"Manquantes : {escape(describe_missing(vMatch))}</p>"
    )

    # Explication du score : poids et maîtrise de chaque compétence
    vScoreLines = describe_score(vMatch)

    if vScoreLines:
        rHtml += (
            "<p><b>Pourquoi ce score</b></p><ul>"
            + "".join(f"<li>{escape(vLine)}</li>" for vLine in vScoreLines)
            + "</ul>"
        )

    if pPreparation["cv"]:
        rHtml += (
            f"<h3>CV conseillé</h3><p>{escape(pPreparation['cv']['name'])} "
            f"({pPreparation['cv']['matching']} compétence(s) de l'offre)</p>"
        )

    rHtml += (
        f"<h3>Points forts à citer</h3><ul>{vStrengths or '<li>À compléter</li>'}</ul>"
        f"<h3>Points à préparer</h3><ul>{items(vInterview['gaps']) or '<li>Aucun</li>'}</ul>"
        + (
            f"<h3>Mon pitch, 30 secondes</h3><p>{escape(vPitch['short'])}</p>"
            f"<h3>Mon pitch, 2 minutes</h3><p>{escape(vPitch['long'])}</p>"
            if (vPitch := vInterview.get("pitch"))
            else ""
        )
        + (
            f"<h3>Questions pièges · {escape(vTricky['employer'])}</h3><ul>"
            + "".join(
                f"<li><b>{escape(vItem['question'])}</b><br>"
                f"{escape(vItem['hint'])}</li>"
                for vItem in vTricky["questions"]
            )
            + "</ul>"
            if (vTricky := vInterview.get("tricky"))
            else ""
        )
        + f"<h3>Questions du recruteur</h3><ul>{vAnswers}</ul>"
        + (
            "<h3>Questions déjà posées en entretien</h3><ul>"
            + "".join(
                f"<li>{escape(vItem['question'])} <i>({escape(vItem['context'])})</i>"
                "</li>"
                for vItem in vInterview["asked"]
            )
            + "</ul>"
            if vInterview.get("asked")
            else ""
        )
        + (
            "<h3>Questions comportementales probables</h3><ul>"
            + "".join(
                f"<li>{escape(vItem['question'])} <i>({escape(vItem['reason'])}"
                + (", réponse préparée" if vItem["prepared"] else ", à préparer")
                + ")</i></li>"
                for vItem in vInterview["likely"]
            )
            + "</ul>"
            if vInterview.get("likely")
            else ""
        )
        + "<h3>Vos réponses STAR</h3><ul>"
        f"{vStar or '<li>À préparer dans la page Profil</li>'}</ul>"
        f"<h3>Questions à poser</h3><ul>{items(vInterview['questions'])}</ul>"
    )

    return rHtml


def save_letter(pParent, pTitle, pText):
    """Enregistre la lettre au format Word, à l'endroit choisi, puis l'ouvre."""

    vPath, _ = QFileDialog.getSaveFileName(
        pParent,
        "Enregistrer la lettre",
        str(Path.home() / build_file_name({"title": pTitle}, "Lettre")),
        "Document Word (*.docx)",
    )

    if not vPath:
        return

    try:
        Path(vPath).write_bytes(write_letter_docx(pText))

    except OSError as vException:
        QMessageBox.warning(
            pParent, "Lettre", f"Enregistrement impossible : {vException}"
        )
        return

    QDesktopServices.openUrl(QUrl.fromLocalFile(vPath))


def show_preparation(pParent, pTitle, pPreparation):
    """Affiche la préparation d'une candidature et le brouillon de lettre."""

    vBrowser = QTextBrowser()
    vBrowser.setHtml(describe_preparation(pPreparation))

    # La lettre reste modifiable : c'est un brouillon à personnaliser.
    vLetter = QPlainTextEdit(pPreparation["letter"])

    vCopyButton = QPushButton("Copier la lettre")
    vCopyButton.clicked.connect(
        lambda: QApplication.clipboard().setText(vLetter.toPlainText())
    )

    # La lettre telle que modifiée dans la fenêtre, au format Word
    vSaveButton = QPushButton("Enregistrer en Word")
    vSaveButton.clicked.connect(
        lambda: save_letter(vDialog, pTitle, vLetter.toPlainText())
    )

    vButtons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    vButtons.button(QDialogButtonBox.StandardButton.Close).setText("Fermer")
    vButtons.addButton(vCopyButton, QDialogButtonBox.ButtonRole.ActionRole)
    vButtons.addButton(vSaveButton, QDialogButtonBox.ButtonRole.ActionRole)

    vDialog = QDialog(pParent)
    vDialog.setWindowTitle(f"Préparer ma candidature · {pTitle}")
    vDialog.resize(820, 720)
    vButtons.rejected.connect(vDialog.reject)

    vLayout = QVBoxLayout(vDialog)
    vLayout.addWidget(vBrowser, 3)
    vLayout.addWidget(
        QLabel("Brouillon de lettre de motivation, à relire et compléter")
    )
    vLayout.addWidget(vLetter, 2)
    vLayout.addWidget(vButtons)

    vDialog.exec()
