"""Journal d'entretien : questions posées à reprendre en révision et en réponses STAR"""

from job.presentation import format_date
from storage.interview_notes import add_interview_note, get_interview_notes
from utils.logger import get_logger

logger = get_logger(__name__)

# Au-delà, une saisie est probablement une erreur de copier-coller.
MAX_JOURNAL_LENGTH = 5000


def split_questions(pText):
    """Retourne les questions saisies, une par ligne, sans puces ni doublons."""

    rQuestions = []

    for vLine in (pText or "").splitlines():
        vQuestion = vLine.strip().lstrip("-•*").strip()

        if vQuestion and vQuestion not in rQuestions:
            rQuestions.append(vQuestion)

    return rQuestions


def record_interview(
    pDatabaseFile, pSource, pSourceId, pInterviewedAt, pQuestions, pImpressions
):
    """Ajoute au journal les questions posées et les impressions d'un entretien.

    Lève ValueError si rien n'est saisi ou si une saisie est trop longue.
    """

    vQuestions = "\n".join(split_questions(pQuestions))
    vImpressions = (pImpressions or "").strip()

    if not (vQuestions or vImpressions):
        raise ValueError("Notez au moins une question posée ou une impression.")

    if max(len(vQuestions), len(vImpressions)) > MAX_JOURNAL_LENGTH:
        raise ValueError(
            f"Saisie trop longue : {MAX_JOURNAL_LENGTH} caractères au plus."
        )

    rNoteId = add_interview_note(
        pDatabaseFile, pSource, pSourceId, pInterviewedAt, vQuestions, vImpressions
    )

    return rNoteId


def describe_note(pNote):
    """Retourne la date et l'offre d'une entrée, pour son titre."""

    rText = " · ".join(
        vPart
        for vPart in (
            format_date(pNote["interviewed_at"]),
            pNote.get("title"),
            pNote.get("company"),
        )
        if vPart
    )

    return rText


def collect_asked_questions(pDatabaseFile):
    """Retourne chaque question posée en entretien avec l'offre où elle l'a été."""

    rQuestions = [
        {"question": vQuestion, "context": describe_note(vNote)}
        for vNote in get_interview_notes(pDatabaseFile)
        for vQuestion in split_questions(vNote["questions"])
    ]

    return rQuestions
