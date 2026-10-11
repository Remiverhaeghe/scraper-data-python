"""Ajout manuel d'une offre et import d'offres depuis un fichier"""

import json
import uuid

import pandas as pd

from job.completion import complete_offers
from job.contract import CONTRACT_TYPES
from job.csv_schema import JOB_COLUMNS
from job.exchange_rates import get_exchange_rates
from job.export import EXPORT_COLUMNS, FORMULA_PREFIXES
from job.presentation import (
    ADDED_SOURCE_LABELS,
    IMPORT_SOURCE,
    MANUAL_SOURCE,
    safe_url,
)
from job.settings import get_net_ratio, get_tax_rate, load_settings
from storage.job_offers import get_fingerprints, save_offers
from utils.logger import get_logger

logger = get_logger(__name__)

IMPORT_FORMATS = {".csv": "CSV", ".xlsx": "Excel", ".json": "JSON"}

# Garde-fous contre un fichier démesuré ou un texte collé par erreur
MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 5000
MAX_FIELD_LENGTHS = {"title": 300, "company": 200, "description": 20000}
DEFAULT_MAX_LENGTH = 1000

# Champs saisis à la main ou lus dans un fichier ; les autres colonnes sont ignorées.
OFFER_FIELDS = {
    "title": "titre",
    "company": "entreprise",
    "url": "lien",
    "description": "description",
    "location": "lieu",
    "contract": "contrat",
    "salary_label": "salaire",
    "remote": "télétravail",
    "published_at": "date de publication",
}

# Intitulés du CSV et de l'Excel exportés, ramenés aux noms techniques
LABEL_COLUMNS = {vLabel: vName for vName, vLabel in EXPORT_COLUMNS.items()}

REMOTE_VALUES = {"oui": 1, "true": 1, "1": 1, "non": 0, "false": 0, "0": 0}


def clean_text(pValue):
    """Retourne un texte sans espaces superflus, ou None s'il est vide."""

    rText = None

    if pValue is not None and not (isinstance(pValue, float) and pd.isna(pValue)):
        vText = str(pValue).strip()

        # Une cellule protégée à l'export (« '=… ») retrouve sa valeur d'origine.
        if vText.startswith("'") and vText[1:].startswith(FORMULA_PREFIXES):
            vText = vText[1:]

        rText = vText or None

    return rText


def normalize_offer(pFields):
    """Ramène les champs saisis ou importés aux valeurs attendues en base."""

    rOffer = {vName: clean_text(pFields.get(vName)) for vName in OFFER_FIELDS}

    if rOffer["remote"] is not None:
        rOffer["remote"] = REMOTE_VALUES.get(rOffer["remote"].lower())

    if rOffer["contract"] is not None:
        rOffer["contract"] = rOffer["contract"].upper()

    return rOffer


def find_offer_errors(pOffer):
    """Retourne les problèmes qui empêchent de créer l'offre, vide si elle est valide."""

    rErrors = []

    if not pOffer["title"]:
        rErrors.append("titre manquant")

    if not pOffer["company"]:
        rErrors.append("entreprise manquante")

    if not pOffer["url"] and not pOffer["description"]:
        rErrors.append("lien ou description manquant")

    if pOffer["url"] and safe_url(pOffer["url"]) == "#":
        rErrors.append("lien invalide, http:// ou https:// attendu")

    if pOffer["contract"] and pOffer["contract"] not in CONTRACT_TYPES:
        rErrors.append(f"contrat inconnu, {', '.join(CONTRACT_TYPES)} attendu")

    for vName, vLabel in OFFER_FIELDS.items():
        vValue = pOffer[vName]
        vMaximum = MAX_FIELD_LENGTHS.get(vName, DEFAULT_MAX_LENGTH)

        if isinstance(vValue, str) and len(vValue) > vMaximum:
            rErrors.append(f"{vLabel} trop long, {vMaximum} caractères au maximum")

    return rErrors


def add_offers(pDatabaseFile, pRows, pSource, pNow):
    """Valide, complète et enregistre des offres ; retourne le bilan de l'ajout.

    pRows est une liste de couples (numéro de ligne, champs). Les offres
    invalides sont listées dans « rejected » ; celles déjà en base, ou en double
    dans le lot, dans « duplicates », sans être enregistrées.
    """

    vValid = []
    rReport = {"added": 0, "source_ids": [], "duplicates": [], "rejected": []}

    for vLine, vFields in pRows:
        vOffer = normalize_offer(vFields)
        vErrors = find_offer_errors(vOffer)

        if vErrors:
            rReport["rejected"].append((vLine, ", ".join(vErrors)))
        else:
            vValid.append((vLine, vOffer))

    if vValid:
        vSettings = load_settings(pDatabaseFile)

        vItems = pd.DataFrame(
            [
                {**vOffer, "source": pSource, "source_id": uuid.uuid4().hex}
                for _, vOffer in vValid
            ]
        ).reindex(columns=JOB_COLUMNS)

        # Les offres validées ont un titre : aucune n'est écartée à cette étape.
        vItems, _ = complete_offers(
            vItems,
            get_net_ratio(vSettings),
            get_tax_rate(vSettings),
            get_exchange_rates(pDatabaseFile, pNow),
        )

        vKnown = get_fingerprints(pDatabaseFile)
        vKeep = []

        for (vLine, vOffer), vFingerprint in zip(vValid, vItems["fingerprint"]):
            vKeep.append(vFingerprint not in vKnown)

            if vFingerprint in vKnown:
                rReport["duplicates"].append((vLine, vOffer["title"]))

            vKnown.add(vFingerprint)

        vItems = vItems[vKeep]

        if not vItems.empty:
            save_offers(pDatabaseFile, vItems, pNow)

        rReport["added"] = len(vItems)
        rReport["source_ids"] = list(vItems["source_id"])

    logger.info(
        "Ajout d'offres (%s) : %s ajoutée(s), %s doublon(s), %s rejetée(s)",
        ADDED_SOURCE_LABELS.get(pSource, pSource),
        rReport["added"],
        len(rReport["duplicates"]),
        len(rReport["rejected"]),
    )

    return rReport


def add_manual_offer(pDatabaseFile, pFields, pNow):
    """Crée une offre saisie à la main ; retourne son identifiant.

    Lève ValueError avec un message lisible si l'offre est incomplète ou déjà présente.
    """

    vReport = add_offers(pDatabaseFile, [(1, pFields)], MANUAL_SOURCE, pNow)

    if vReport["rejected"]:
        raise ValueError(f"Offre non créée : {vReport['rejected'][0][1]}.")

    if vReport["duplicates"]:
        raise ValueError("Offre non créée : elle est déjà dans la liste des offres.")

    rSourceId = vReport["source_ids"][0]

    return rSourceId


def read_records(pFile, pSuffix):
    """Lit les offres d'un fichier et le numéro de ligne de la première."""

    if pSuffix == ".json":
        if hasattr(pFile, "read"):
            vData = json.loads(pFile.read().decode("utf-8-sig"))
        else:
            with open(pFile, encoding="utf-8-sig") as vFile:
                vData = json.load(vFile)

        rResult = (vData, 1)

    else:
        if pSuffix == ".csv":
            # sep=None reconnaît le point-virgule de l'export comme la virgule.
            vFrame = pd.read_csv(
                pFile, sep=None, engine="python", dtype=str, encoding="utf-8-sig"
            )
        else:
            vFrame = pd.read_excel(pFile, dtype=str)

        # Ligne 1 : les intitulés de colonnes
        rResult = (vFrame.to_dict("records"), 2)

    return rResult


def read_offers_file(pFile, pSuffix):
    """Lit un fichier au format de l'export ; retourne ses lignes numérotées.

    pFile est un chemin ou un fichier ouvert en binaire.
    """

    vSuffix = pSuffix.lower()

    if vSuffix not in IMPORT_FORMATS:
        raise ValueError(f"Format non pris en charge : {vSuffix or 'aucun'}.")

    try:
        vRecords, vFirstLine = read_records(pFile, vSuffix)

    except Exception as vError:
        # Fichier corrompu, mauvais encodage ou contenu qui n'est pas un tableau
        logger.warning("Fichier d'import illisible (%s) : %s", vSuffix, vError)
        raise ValueError(
            f"Fichier illisible : vérifiez qu'il s'agit bien d'un {IMPORT_FORMATS[vSuffix]}."
        ) from vError

    if not isinstance(vRecords, list) or not all(
        isinstance(vRecord, dict) for vRecord in vRecords
    ):
        raise ValueError("Le fichier doit contenir une liste d'offres.")

    if len(vRecords) > MAX_IMPORT_ROWS:
        raise ValueError(f"Fichier trop long : {MAX_IMPORT_ROWS} offres au maximum.")

    # Les intitulés de l'export (« Titre ») sont ramenés aux noms techniques.
    rRows = [
        (
            vLine,
            {
                LABEL_COLUMNS.get(str(vKey), str(vKey)): vValue
                for vKey, vValue in vRecord.items()
            },
        )
        for vLine, vRecord in enumerate(vRecords, start=vFirstLine)
    ]

    return rRows


def import_offers_file(pDatabaseFile, pFile, pSuffix, pNow):
    """Importe les offres d'un fichier ; retourne le bilan de l'import."""

    vRows = read_offers_file(pFile, pSuffix)

    rReport = add_offers(pDatabaseFile, vRows, IMPORT_SOURCE, pNow)
    rReport["read"] = len(vRows)

    return rReport


def describe_import(pReport):
    """Résume le bilan d'un import en une phrase."""

    rText = (
        f"{pReport['added']} offre(s) importée(s) sur {pReport['read']}, "
        f"{len(pReport['duplicates'])} doublon(s) écarté(s), "
        f"{len(pReport['rejected'])} ligne(s) rejetée(s)."
    )

    return rText


def list_import_problems(pReport):
    """Liste les lignes non importées et leur raison, dans l'ordre du fichier."""

    vProblems = [(vLine, vReason) for vLine, vReason in pReport["rejected"]]
    vProblems += [
        (vLine, f"déjà présente ({vTitle})") for vLine, vTitle in pReport["duplicates"]
    ]

    rProblems = [f"Ligne {vLine} : {vReason}" for vLine, vReason in sorted(vProblems)]

    return rProblems
