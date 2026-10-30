"""Export de vos données personnelles, lisible sans l'application (droit d'accès)

L'archive .zip contient un fichier JSON par type de données, vos réglages
personnels et vos pièces jointes. Contrairement à la sauvegarde complète, elle
se lit avec n'importe quel éditeur, et n'emporte ni secret ni jeton d'accès.
"""

import json
import re
import zipfile

from storage.attachments import get_attachment_directory
from storage.personal_data import read_attachment_files, read_personal_data
from storage.settings_repository import get_setting_values
from utils.logger import get_logger

logger = get_logger(__name__)

# Réglages exportés : liste fermée, pour qu'un jeton ajouté plus tard ne parte
# jamais par mégarde dans l'export.
EXPORTED_SETTINGS = (
    "candidate_profile",
    "star_answers",
    "home_location",
    "notification_email",
    "notification_min_score",
    "company_rules",
    "excluded_title_words",
    "interim_agencies",
    "schedule_search",
    "schedule_extra_searches",
    "interview_simulation_history",
    "interview_simulation_scores",
    "quiz_exam_results",
    "certifications_owned",
    "certifications_details",
    "troubleshooting_results",
    "ladder_progress",
    "sql_progress",
    "circuit_progress",
)

ATTACHMENT_PREFIX = "pieces_jointes/"
UNSAFE_NAME_PATTERN = re.compile(r"[^\w .-]")
MAX_NAME_LENGTH = 100

README_TEXT = """Vos données JobBoard Perso, exportées le {date}.

Chaque fichier .json se lit avec un éditeur de texte ou un navigateur :
- candidatures.json : vos candidatures, avec l'offre, les notes et l'adresse du recruteur
- historique_des_statuts.json, relances.json : le suivi de chaque candidature
- journal_entretien.json : les questions posées et vos impressions
- reglages.json : profil, CV, réponses STAR, domicile, e-mail, règles personnelles
  et certifications obtenues
- recherches_enregistrees.json, historique_recherches.json : vos recherches
- reponses_revision.json, defis.json, niveaux_git.json : votre révision
- tests_recrutement.json : vos parties de tests de recrutement ; les pannes
  résolues, vos programmes d'automate, vos requêtes SQL et vos schémas électriques
  sont dans reglages.json
- pieces_jointes/ : les CV et lettres joints aux candidatures, les certificats

Les offres publiées par les sites d'emploi et les jetons d'accès n'y figurent pas.
"""


def read_setting(pValue):
    """Retourne la valeur d'un réglage, décodée si elle est écrite en JSON."""

    try:
        rValue = json.loads(pValue)

    except (TypeError, ValueError):
        rValue = pValue

    return rValue


def build_attachment_name(pId, pFileName):
    """Retourne le nom d'une pièce jointe dans l'archive, sans caractère risqué."""

    vName = UNSAFE_NAME_PATTERN.sub("_", pFileName or "piece-jointe")[:MAX_NAME_LENGTH]

    rName = f"{ATTACHMENT_PREFIX}{pId}-{vName}"

    return rName


def export_personal_data(pDatabaseFile, pTarget, pNow):
    """Écrit vos données dans l'archive pTarget ; retourne le nombre de fichiers.

    pTarget est un chemin ou un fichier binaire ouvert en écriture.
    """

    vData = read_personal_data(pDatabaseFile)
    vValues = get_setting_values(pDatabaseFile)
    vSettings = {
        vKey: read_setting(vValues[vKey])
        for vKey in EXPORTED_SETTINGS
        if vKey in vValues
    }
    vDirectory = get_attachment_directory(pDatabaseFile)

    rCount = 0

    with zipfile.ZipFile(pTarget, "w", zipfile.ZIP_DEFLATED) as vArchive:
        vArchive.writestr("LISEZMOI.txt", README_TEXT.format(date=f"{pNow:%d/%m/%Y}"))

        for vName, vRows in {**vData, "reglages": vSettings}.items():
            vArchive.writestr(
                f"{vName}.json", json.dumps(vRows, ensure_ascii=False, indent=2)
            )
            rCount += 1

        for vId, vFileName, vStoredName in read_attachment_files(pDatabaseFile):
            vFile = vDirectory / vStoredName

            if vFile.is_file():
                vArchive.write(vFile, build_attachment_name(vId, vFileName))
                rCount += 1
            else:
                logger.warning("Pièce jointe absente du disque : %s", vStoredName)

    logger.info("Données personnelles exportées : %s fichier(s)", rCount)

    return rCount
