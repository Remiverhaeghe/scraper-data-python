"""Mise en forme des offres, commune au tableau de bord web et à l'interface"""

import json
import re
from datetime import datetime, timedelta
from urllib.parse import quote

import pandas as pd

from config import (
    AUTHOR_NAME,
    ICONS_LICENSE_FILE,
    ICONS_URL,
    LICENSE_FILE,
    EXPIRY_DAYS,
    LICENSE_NAME,
    NEW_OFFER_DAYS,
)
from job.benefits import BENEFIT_LABELS
from job.contract import CONTRACT_TYPES
from job.geocoding import DISTANCE_FILTERS
from job.location import FRANCE, detect_location
from job.sources.registry import SOURCES
from storage.job_applications import APPLICATION_STATUSES

STATUS_LABELS = {
    "INTERESTED": "Intéressé",
    "APPLIED": "Postulé",
    "INTERVIEW": "Entretien",
    "ACCEPTED": "Accepté",
    "REJECTED": "Refusé",
    "CLOSED": "Clôturé",
    "IGNORED": "Ignorée",
}

# Tonalité de couleur des contrats et des statuts de suivi, communes au bureau
# (couleur du texte) et au web (badges) ; ces tonalités existent dans les deux.
CONTRACT_TONES = {"CDI": "success", "CDD": "warning", "FREELANCE": "primary"}
STATUS_TONES = {
    "INTERESTED": "primary",
    "APPLIED": "primary",
    "INTERVIEW": "warning",
    "ACCEPTED": "success",
    "REJECTED": "danger",
    "CLOSED": "muted",
    "IGNORED": "muted",
}

# Nombre d'avantages affichés en badges dans une liste, pour garder des lignes courtes
MAX_BENEFIT_BADGES = 2

EXECUTION_STATUS_LABELS = {
    "success": "Réussie",
    "partial": "Partielle",
    "error": "En échec",
}

# Couleurs des séries et des parts de graphique, lisibles dans les deux thèmes
CHART_PALETTE = (
    "#3B82F6",
    "#F59E0B",
    "#8B5CF6",
    "#10B981",
    "#EC4899",
    "#06B6D4",
    "#94A3B8",
)

# Tonalité d'affichage de chaque statut d'exécution ; tout autre statut est un échec
EXECUTION_TONES = {"success": "success", "partial": "warning"}

# Texte des exécutions antérieures à l'enregistrement des critères
UNKNOWN_SEARCH = "Critères non enregistrés"

# Au-delà, une ligne d'activité résume les sources par leur nombre
MAX_LISTED_SOURCES = 3

# Déclencheur noté dans l'historique pour les recherches du planificateur
SCHEDULED_TRIGGER = "scheduled"

# Périodes proposées par le filtre de date de publication, en jours
PUBLISHED_PERIODS = {
    None: "Toutes les dates",
    1: "Publiées depuis 24 h",
    7: "Publiées depuis 7 jours",
    30: "Publiées depuis 30 jours",
}

# Filtre de disponibilité ; par défaut, les offres probablement expirées sont masquées
AVAILABILITY_FILTERS = {
    "available": "Offres disponibles",
    "expired": "Probablement expirées",
    "all": "Disponibles et expirées",
}
DEFAULT_AVAILABILITY = "available"

# Résultat de la vérification du lien d'une offre, tel qu'affiché
AVAILABILITY_LABELS = {"available": "disponible", "expired": "retirée"}
# Couleur du résultat de la vérification, partagée par le bureau et le web
AVAILABILITY_TONES = {"available": "success", "expired": "danger", None: "warning"}

AVAILABILITY_HELP = (
    "Ouvre le lien de l'offre pour savoir si elle est toujours en ligne ; une offre "
    "retirée est ensuite masquée de la liste"
)

# Traduction gratuite, sans clé : le texte est passé dans l'adresse, à sa limite.
TRANSLATE_URL = "https://translate.google.com/?sl=auto&tl=fr&op=translate&text="
MAX_TRANSLATE_LENGTH = 4000

# Mots outils du français : leur part dans un texte trahit sa langue.
FRENCH_WORDS = frozenset(
    "le la les des du un une et est pour dans avec vous nous sur au aux qui que "
    "en de votre nos vos ce cette être sont par".split()
)
WORD_PATTERN = re.compile(r"[a-zàâçéèêëîïôûùüÿœ']+", re.IGNORECASE)
MIN_FRENCH_RATIO = 0.08
# Un texte plus court ne permet pas de juger sa langue : pas de traduction proposée.
MIN_TRANSLATE_WORDS = 8

AVAILABILITY_MESSAGES = {
    "available": "L'offre est toujours en ligne.",
    "expired": "L'offre a été retirée : elle est désormais masquée par défaut.",
    None: "Le site de l'offre n'a pas permis de conclure (accès refusé ou erreur).",
}

# Valeur du filtre de statut affichant les candidatures à relancer
FOLLOW_UP_FILTER = "FOLLOW_UP"

# Offres ajoutées par l'utilisateur plutôt que trouvées par une recherche
MANUAL_SOURCE = "manual"
IMPORT_SOURCE = "import"
ADDED_SOURCE_LABELS = {
    MANUAL_SOURCE: "Saisie manuelle",
    IMPORT_SOURCE: "Import de fichier",
}


def format_euros(pAmount):
    """Formate un montant en euros avec un espace comme séparateur de milliers."""

    rText = ""

    if pAmount is not None:
        rText = f"{round(pAmount):,} €".replace(",", "\u202f")

    return rText


def format_date(pValue):
    """Formate une date ISO au format français, ou renvoie la valeur d'origine."""

    rText = ""

    if pValue:
        try:
            rText = datetime.fromisoformat(str(pValue)).strftime("%d/%m/%Y")

        except ValueError:
            rText = str(pValue)

    return rText


def get_source_label(pName):
    """Retourne le libellé d'une source, ou son nom si elle est inconnue."""

    vSource = SOURCES.get(pName)

    rLabel = vSource.label if vSource else ADDED_SOURCE_LABELS.get(pName, pName)

    return rLabel


def safe_url(pUrl):
    """Retourne l'URL si elle est en http ou https, sinon un lien neutre.

    L'échappement HTML ne protège pas un attribut href : une URL
    « javascript: » fournie par une source serait exécutée au clic.
    """

    rUrl = "#"

    if pUrl and str(pUrl).lower().startswith(("http://", "https://")):
        rUrl = str(pUrl)

    return rUrl


def to_list(pValue):
    """Convertit une liste enregistrée en JSON en liste Python."""

    rValues = []

    # Les offres d'une recherche en cours portent déjà des listes.
    if isinstance(pValue, list):
        rValues = pValue
    elif pValue:
        try:
            vValues = json.loads(pValue)
            rValues = vValues if isinstance(vValues, list) else [pValue]

        except ValueError:
            rValues = [pValue]

    return rValues


def format_net_salary(pOffer):
    """Formate la fourchette de salaire net mensuel d'une offre."""

    vMinimum = pOffer.get("salary_net_monthly_min")
    vMaximum = pOffer.get("salary_net_monthly_max")

    if vMinimum is not None and vMaximum is not None and vMinimum != vMaximum:
        rText = f"{format_euros(vMinimum)} – {format_euros(vMaximum)}"
    else:
        rText = format_euros(vMinimum if vMinimum is not None else vMaximum)

    vCurrency = pOffer.get("salary_currency")

    # Converti depuis une autre devise au taux de la BCE : une estimation.
    if rText and vCurrency and vCurrency != "EUR":
        rText = f"≈ {rText} ({vCurrency})"

    return rText


def clean_missing_values(pOffer):
    """Remplace les valeurs manquantes de pandas (NaN, NaT) par None."""

    rOffer = {
        vKey: (
            None if not isinstance(vValue, (list, dict)) and pd.isna(vValue) else vValue
        )
        for vKey, vValue in pOffer.items()
    }

    return rOffer


def is_french(pText):
    """Indique si un texte est probablement rédigé en français."""

    vWords = WORD_PATTERN.findall((pText or "").lower())

    rFrench = bool(vWords) and (
        sum(vWord in FRENCH_WORDS for vWord in vWords) / len(vWords) >= MIN_FRENCH_RATIO
    )

    return rFrench


def build_translate_url(pText):
    """Retourne le lien de traduction d'un texte étranger, ou None."""

    vText = (pText or "").strip()

    rUrl = (
        TRANSLATE_URL + quote(vText[:MAX_TRANSLATE_LENGTH])
        if len(WORD_PATTERN.findall(vText)) >= MIN_TRANSLATE_WORDS
        and not is_french(vText)
        else None
    )

    return rUrl


def can_lookup_company(pOffer):
    """Indique si l'annuaire public, limité à la France, peut décrire l'entreprise."""

    # Pays absent des offres enregistrées avant sa détection : déduit du lieu.
    vCountry = pOffer.get("country") or detect_location(pOffer.get("location"))[0]

    rPossible = bool(pOffer.get("company")) and vCountry in (None, FRANCE)

    return rPossible


def prepare_offer(pOffer, pNewSince, pNow=None, pExpiryDays=EXPIRY_DAYS):
    """Complète une offre avec les informations utiles à l'affichage."""

    vOffer = clean_missing_values(pOffer)

    vOffer["source_label"] = get_source_label(vOffer["source"])
    vOffer["is_new"] = vOffer["first_seen_at"] >= pNewSince.isoformat()
    vOffer["skills_list"] = to_list(vOffer.get("skills"))
    vOffer["net_salary"] = format_net_salary(vOffer)

    # remote est stocké en texte ('1' ou '0') : la chaîne '0' serait « vraie ».
    if vOffer.get("remote") is not None:
        vOffer["remote"] = str(vOffer["remote"]).lower() in ("1", "true")
    vOffer["is_expired"] = is_offer_expired(vOffer, pNow or datetime.now(), pExpiryDays)
    vOffer["follow_up_due"] = bool(
        vOffer.get("follow_up_date")
        and vOffer.get("application_status") in ("APPLIED", "INTERVIEW")
        and vOffer["follow_up_date"] <= datetime.now().isoformat()
    )
    vOffer["benefits"] = [
        vLabel for vColumn, vLabel in BENEFIT_LABELS.items() if vOffer.get(vColumn)
    ]

    rOffer = vOffer

    return rOffer


def is_offer_expired(pOffer, pNow, pExpiryDays=EXPIRY_DAYS):
    """Applique à une offre la même règle que EXPIRED_CONDITION en base."""

    vCutoff = (pNow - timedelta(days=pExpiryDays)).isoformat()
    vLastSign = pOffer.get("last_seen_at") or ""

    if pOffer.get("availability") == "available":
        vLastSign = max(vLastSign, pOffer.get("availability_checked_at") or "")

    rExpired = (
        pOffer.get("availability") == "expired"
        or bool(pOffer.get("expires_at") and pOffer["expires_at"] < pNow.isoformat())
        or vLastSign < vCutoff
    )

    return rExpired


def build_offer_filters(
    pSearch=None,
    pSource=None,
    pContract=None,
    pRemote=False,
    pMinNetSalary=None,
    pNewOnly=False,
    pStatus=None,
    pNow=None,
    pNewOfferDays=NEW_OFFER_DAYS,
    pMaxNetSalary=None,
    pPublishedDays=None,
    pHasSalary=False,
    pKeys=None,
    pAvailability=DEFAULT_AVAILABILITY,
    pExpiryDays=EXPIRY_DAYS,
    pCompanyKeys=None,
    pPreferredOnly=False,
    pFranceOnly=False,
    pHideAgencies=False,
    pDistanceKm=0,
    pHome=None,
):
    """Traduit les filtres saisis en paramètres de get_offers.

    Les valeurs inconnues sont ignorées. Les offres ignorées restent masquées
    sauf si ce statut est demandé explicitement, comme celles des entreprises
    exclues. pCompanyKeys donne les noms normalisés des listes d'entreprises.
    Le rayon pDistanceKm autour du domicile pHome est ignoré sans domicile.
    """

    vCompanyKeys = pCompanyKeys or {"excluded": [], "preferred": []}

    vNow = pNow or datetime.now()

    rFilters = {
        "pSearch": (pSearch or "").strip() or None,
        "pSource": (
            pSource if pSource in SOURCES or pSource in ADDED_SOURCE_LABELS else None
        ),
        "pContract": pContract if pContract in CONTRACT_TYPES else None,
        "pRemote": bool(pRemote),
        "pMinNetSalary": pMinNetSalary,
        "pSeenSince": vNow - timedelta(days=pNewOfferDays) if pNewOnly else None,
        "pStatus": pStatus if pStatus in APPLICATION_STATUSES else None,
        "pFollowUpBefore": vNow if pStatus == FOLLOW_UP_FILTER else None,
        "pMaxNetSalary": pMaxNetSalary,
        "pPublishedSince": (
            vNow - timedelta(days=pPublishedDays) if pPublishedDays else None
        ),
        "pHasSalary": bool(pHasSalary),
        "pKeys": pKeys,
        "pHideIgnored": True,
        "pAvailability": (
            pAvailability if pAvailability in AVAILABILITY_FILTERS else None
        ),
        "pNow": vNow,
        "pExpiredBefore": vNow - timedelta(days=pExpiryDays),
        "pExcludedCompanies": vCompanyKeys["excluded"],
        "pPreferredCompanies": vCompanyKeys["preferred"] if pPreferredOnly else None,
        "pCountry": FRANCE if pFranceOnly else None,
        "pHideAgencies": bool(pHideAgencies),
        "pNear": (
            {
                "latitude": pHome["latitude"],
                "longitude": pHome["longitude"],
                "radius_km": pDistanceKm,
            }
            if pHome and pDistanceKm in DISTANCE_FILTERS and pDistanceKm
            else None
        ),
    }

    return rFilters


def describe_search(pParameters):
    """Résume en une ligne les critères d'une recherche enregistrée.

    Une exécution antérieure à l'enregistrement des paramètres renvoie un texte
    vide, à distinguer d'une recherche lancée sans critère.
    """

    rDescription = ""

    if pParameters is not None:
        vParts = [
            pParameters.get("keyword"),
            pParameters.get("location"),
            pParameters.get("contract"),
        ]

        if pParameters.get("min_salary") is not None:
            vParts.append(f"≥ {format_euros(pParameters['min_salary'])} net")

        if pParameters.get("max_salary") is not None:
            vParts.append(f"≤ {format_euros(pParameters['max_salary'])} net")

        if pParameters.get("remote"):
            vParts.append("télétravail")

        if pParameters.get("skills"):
            vParts.append("compétences : " + ", ".join(pParameters["skills"]))

        if pParameters.get("exclude_keywords"):
            vParts.append("sans : " + ", ".join(pParameters["exclude_keywords"]))

        rDescription = " · ".join(vPart for vPart in vParts if vPart) or "Sans critère"

    return rDescription


def describe_sources(pParameters):
    """Retourne les libellés des sources interrogées lors d'une recherche."""

    rLabels = ", ".join(
        get_source_label(vName) for vName in (pParameters or {}).get("sources", [])
    )

    return rLabels


def summarize_history(pSummary):
    """Traduit la synthèse de l'historique en valeurs affichables."""

    vExecutions = pSummary["executions"]

    rValues = {
        "executions": vExecutions,
        "item_count": pSummary["item_count"],
        "average_duration": f"{pSummary['average_duration']:.1f} s",
        "success_rate": (
            f"{round(100 * pSummary['successes'] / vExecutions)} %"
            if vExecutions
            else "-"
        ),
    }

    return rValues


def describe_execution(pEntry):
    """Résume une exécution : tonalité, titre, détail, sources et nombre d'offres."""

    vSources = ""

    if pEntry.scraper_type == "job":
        vTitle = describe_search(pEntry.parameters) or "Recherche d'offres"
        vSources = describe_sources(pEntry.parameters)
        vSourceCount = len((pEntry.parameters or {}).get("sources", []))
        vDetail = (
            f"{vSourceCount} sources" if vSourceCount > MAX_LISTED_SOURCES else vSources
        )
    else:
        # Anciennes exécutions de la partie livres, retirée du projet.
        vTitle = "Scraping de livres"
        vDetail = pEntry.url

    vDate = f"{pEntry.started_at:%d/%m/%Y à %H:%M}"

    if (pEntry.parameters or {}).get("trigger") == SCHEDULED_TRIGGER:
        vDate = f"{vDate} · planifiée"

    rDescription = {
        "tone": EXECUTION_TONES.get(pEntry.status, "danger"),
        "title": vTitle,
        "detail": f"{vDate} · {vDetail}" if vDetail else vDate,
        "sources": vSources,
        "result": f"{pEntry.item_count} offre(s)",
    }

    return rDescription


def build_legal_sections(pApplicationName):
    """Retourne les mentions légales, communes au bureau et au web."""

    rSections = [
        (
            "Édition",
            f"{pApplicationName} est un projet personnel et non commercial, développé "
            f"par {AUTHOR_NAME}, titulaire des droits sur le code publié sur GitHub.",
        ),
        (
            "Hébergement",
            "L'application n'est pas un service en ligne. Elle s'exécute sur le poste "
            "ou le serveur de la personne qui l'installe, qui en assure l'hébergement "
            "et l'usage.",
        ),
        (
            "Contact et signalement",
            "Pour toute question, ou pour demander le retrait d'un contenu, l'auteur "
            "est joignable sur LinkedIn.",
        ),
        (
            "Contenus",
            "Les offres d'emploi proviennent des sources indiquées sur chaque annonce "
            "et restent la propriété de leurs éditeurs. Elles sont présentées telles "
            "que fournies par ces sources, avec un lien vers l'annonce d'origine qui "
            "fait seule foi. L'application n'est ni un recruteur ni un intermédiaire : "
            "elle ne publie aucune offre et n'intervient pas dans les candidatures.",
        ),
        (
            "Sources de données",
            "Les offres sont obtenues par les interfaces de programmation (API) mises "
            "à disposition par chaque source. La personne qui installe l'application "
            "utilise ses propres clés d'accès et s'engage à respecter les conditions "
            "d'utilisation de chaque source, notamment leurs limites de requêtes.",
        ),
        (
            "Limitation de responsabilité",
            "L'application est fournie en l'état, sans garantie d'exactitude, "
            "d'exhaustivité ni de disponibilité. Les informations affichées, dont les "
            "salaires nets estimés selon les règles des paramètres, sont indicatives "
            "et ne constituent pas un conseil juridique, fiscal ou professionnel. "
            "L'auteur ne peut être tenu responsable du contenu des offres, des "
            "décisions prises à partir de ces informations ni de l'usage fait de "
            "l'application.",
        ),
        (
            "Données personnelles",
            "Le suivi des candidatures et les notes sont enregistrés uniquement dans "
            "la base de données locale de l'application et ne sont jamais transmis à "
            "l'auteur. Seuls les critères de recherche sont envoyés aux sources "
            "interrogées. La personne qui installe l'application est responsable des "
            "données qu'elle y enregistre, au sens du RGPD. Si elle active les "
            "notifications, les nouvelles offres lui sont envoyées par e-mail depuis "
            "son propre compte Gmail. Aucun cookie publicitaire ni de mesure "
            "d'audience n'est déposé : le tableau de bord web utilise seulement un "
            "cookie de session, nécessaire à la connexion et supprimé à la "
            "déconnexion, et le choix du thème est conservé sur l'appareil.",
        ),
        (
            "Propriété intellectuelle",
            "Les noms et marques des sources citées appartiennent à leurs titulaires "
            "et servent uniquement à indiquer l'origine des offres. Le logo de "
            "l'application appartient à son auteur.",
        ),
        (
            "Icônes",
            f"Les icônes proviennent de la bibliothèque Lucide ({ICONS_URL}), "
            "distribuée sous licence ISC. Cette licence autorise leur utilisation et "
            "leur modification, à condition de conserver la mention de copyright et "
            "le texte de la licence : il est fourni avec l'application et affiché à "
            "la suite de la licence du projet. Une partie des icônes provient de "
            "Feather, sous licence MIT.",
        ),
        (
            "Licence",
            "Le code peut être consulté et utilisé tel quel à des fins non "
            "commerciales, mais ni modifié ni redistribué, selon les termes de la "
            f"licence {LICENSE_NAME}.",
        ),
        (
            "Droit applicable",
            "Ces mentions sont régies par le droit français.",
        ),
    ]

    return rSections


# La licence n'a de valeur qu'en anglais : ce résumé aide à la lire sans la remplacer.
LICENSE_SUMMARY_NOTE = "Résumé indicatif en français : seul le texte anglais fait foi."
LICENSE_SUMMARY = (
    "Le logiciel peut être utilisé à des fins non commerciales : usage personnel, "
    "recherche, enseignement, associations et organismes publics.",
    "Il ne peut être ni modifié, ni redistribué, ni servir de base à une autre "
    "œuvre.",
    "Une licence de brevet est accordée pour ces mêmes usages.",
    "En cas de manquement, la licence prend fin, sauf mise en conformité dans les "
    "32 jours suivant la notification.",
    "Le logiciel est fourni sans garantie, et son auteur n'est pas responsable des "
    "dommages liés à son utilisation.",
)


def read_license(pFile=LICENSE_FILE):
    """Retourne le texte d'une licence, par défaut celle du projet."""

    try:
        rText = pFile.read_text(encoding="utf-8")

    except OSError:
        rText = "Le fichier de licence est introuvable dans cette installation."

    return rText


def read_icons_license():
    """Retourne le texte de la licence ISC des icônes Lucide."""

    rText = read_license(ICONS_LICENSE_FILE)

    return rText


def describe_backup(pBackup):
    """Décrit une sauvegarde : date, motif et taille."""

    vReason = {"auto": "automatique", "": "manuelle"}.get(
        pBackup["reason"], pBackup["reason"].replace("-", " ")
    )
    vSize = pBackup["size"] / 1_048_576

    rText = (
        f"{pBackup['created_at']:%d/%m/%Y %H:%M} · {vReason} · "
        f"{vSize:.1f} Mo".replace(".", ",")
    )

    return rText


# Seuils de couleur des scores sur 100 : correspondance, fraîcheur et notes
SCORE_GOOD = 70
SCORE_FAIR = 40


def get_score_tone(pScore, pLowTone="muted"):
    """Retourne la couleur d'un score sur 100 : vert, orange, puis pLowTone."""

    if pScore >= SCORE_GOOD:
        rTone = "success"
    elif pScore >= SCORE_FAIR:
        rTone = "warning"
    else:
        rTone = pLowTone

    return rTone
