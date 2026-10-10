"""Export des offres aux formats CSV, Excel et JSON"""

from pathlib import Path

from job.presentation import STATUS_LABELS
from job.sources.registry import SOURCES
from utils.logger import get_logger

logger = get_logger(__name__)

# Colonnes exportées et leur intitulé dans les fichiers destinés à un tableur
EXPORT_COLUMNS = {
    "title": "Titre",
    "company": "Entreprise",
    "location": "Lieu",
    "contract": "Contrat",
    "salary_net_monthly_min": "Net mensuel minimum",
    "salary_net_monthly_max": "Net mensuel maximum",
    "salary_label": "Salaire annoncé",
    "remote": "Télétravail",
    "source": "Source",
    "url": "Lien",
    "published_at": "Publiée le",
    "first_seen_at": "Vue le",
    "application_status": "Suivi",
}

EXPORT_FORMATS = {".csv": "CSV", ".xlsx": "Excel", ".json": "JSON"}

# Un tableur exécute une cellule commençant par l'un de ces caractères comme une
# formule : un texte d'offre malveillant pourrait ainsi déclencher une action.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def protect_formula(pValue):
    """Neutralise une valeur texte qu'un tableur interpréterait comme une formule."""

    rValue = pValue

    if isinstance(pValue, str) and pValue.startswith(FORMULA_PREFIXES):
        rValue = "'" + pValue

    return rValue


def prepare_for_spreadsheet(pOffers):
    """Traduit les codes en libellés, renomme les colonnes et neutralise les formules."""

    vOffers = pOffers.copy()

    vOffers["source"] = vOffers["source"].map(
        lambda pName: SOURCES[pName].label if pName in SOURCES else pName
    )
    vOffers["application_status"] = vOffers["application_status"].map(
        lambda pStatus: STATUS_LABELS.get(pStatus, "")
    )
    vOffers["remote"] = vOffers["remote"].map(
        lambda pRemote: {1: "Oui", 0: "Non"}.get(pRemote, "")
    )

    rOffers = vOffers.rename(columns=EXPORT_COLUMNS).map(protect_formula)

    return rOffers


def export_offers(pOffers, pPath):
    """Écrit les offres dans un fichier dont l'extension fixe le format.

    Le JSON garde les noms et codes techniques, pratiques pour un programme ;
    CSV et Excel utilisent des intitulés lisibles dans un tableur.
    """

    vPath = Path(pPath)
    vSuffix = vPath.suffix.lower()

    if vSuffix not in EXPORT_FORMATS:
        raise ValueError(f"Format d'export non pris en charge : {vSuffix or 'aucun'}")

    vOffers = pOffers.reindex(columns=list(EXPORT_COLUMNS))

    if vSuffix == ".json":
        vOffers.to_json(vPath, orient="records", force_ascii=False, indent=2)

    elif vSuffix == ".csv":
        # Point-virgule et BOM : ouverture directe dans un Excel configuré en français
        prepare_for_spreadsheet(vOffers).to_csv(
            vPath, sep=";", index=False, encoding="utf-8-sig"
        )

    else:
        prepare_for_spreadsheet(vOffers).to_excel(vPath, index=False)

    logger.info("%s offre(s) exportée(s) en %s", len(vOffers), EXPORT_FORMATS[vSuffix])

    rCount = len(vOffers)

    return rCount
