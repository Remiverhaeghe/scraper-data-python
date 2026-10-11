"""Analyse de la qualité des données : remplissage par source et offres à vérifier"""

import csv
import io

from job.export import protect_formula
from job.presentation import clean_missing_values, get_source_label
from storage.history_repository import get_history
from storage.job_offers import QUALITY_COLUMNS, count_filled_fields, get_offers

# Libellé affiché pour chaque colonne mesurée, dans l'ordre de QUALITY_COLUMNS
QUALITY_LABELS = {
    "title": "Titre",
    "company": "Entreprise",
    "location": "Lieu",
    "contract": "Contrat",
    "salary_net_monthly_min": "Salaire",
    "remote": "Télétravail",
    "skills": "Compétences",
    "experience_level": "Expérience",
    "published_at": "Publication",
    "description": "Description",
}

# Seuils de couleur d'un taux de remplissage, en pourcentage
GOOD_RATE = 80
FAIR_RATE = 40

# Colonnes de l'export des offres à vérifier
EXPORT_COLUMNS = (
    "source",
    "source_id",
    "problems",
    "title",
    "company",
    "location",
    "salary_label",
    "url",
)


def get_rate_tone(pRate):
    """Retourne la tonalité de couleur d'un taux de remplissage."""

    if pRate >= GOOD_RATE:
        rTone = "success"
    elif pRate >= FAIR_RATE:
        rTone = "warning"
    else:
        rTone = "danger"

    return rTone


def build_rates(pTotal, pFilled):
    """Calcule le taux de remplissage et la tonalité de chaque colonne."""

    rRates = []

    for vColumn in QUALITY_COLUMNS:
        vRate = round(100 * pFilled[vColumn] / pTotal) if pTotal else 0
        rRates.append({"rate": vRate, "tone": get_rate_tone(vRate)})

    return rRates


def get_quality_report(pDatabaseFile):
    """Retourne le remplissage de chaque colonne, par source puis toutes sources."""

    vCounts = count_filled_fields(pDatabaseFile)

    vRows = [
        {
            "source": get_source_label(vSource),
            "count": vTotal,
            "rates": build_rates(vTotal, vFilled),
        }
        for vSource, vTotal, vFilled in vCounts
    ]

    vTotal = sum(vCount for _, vCount, _ in vCounts)
    vAllFilled = {
        vColumn: sum(vFilled[vColumn] for _, _, vFilled in vCounts)
        for vColumn in QUALITY_COLUMNS
    }

    rReport = {
        "columns": [QUALITY_LABELS[vColumn] for vColumn in QUALITY_COLUMNS],
        "rows": vRows,
        "total": {"count": vTotal, "rates": build_rates(vTotal, vAllFilled)},
        # Offres sans titre ni description, écartées avant l'enregistrement
        "rejected": sum(
            (vEntry.parameters or {}).get("rejected", 0)
            for vEntry in get_history(pDatabaseFile)
        ),
    }

    return rReport


def find_problems(pOffer):
    """Retourne les défauts repérés sur une offre, en clair."""

    rProblems = []

    vTitle = pOffer.get("title") or ""

    if not vTitle.strip():
        rProblems.append("titre absent")
    elif " | " in vTitle:
        rProblems.append("titre en plusieurs segments")

    if not pOffer.get("company"):
        rProblems.append("entreprise absente")

    if not pOffer.get("location") and not pOffer.get("remote"):
        rProblems.append("lieu absent")

    # Un salaire écrit par la source mais sans montant lu montre un format que
    # l'analyse ne sait pas encore lire. Un montant lu dans une autre devise que
    # l'euro n'est pas un défaut : il n'est simplement pas converti en net.
    if (
        pOffer.get("salary_label")
        and pOffer.get("salary_min") is None
        and pOffer.get("salary_max") is None
    ):
        rProblems.append("salaire non interprété")

    if not pOffer.get("description"):
        rProblems.append("description absente")

    return rProblems


def build_quality_export(pDatabaseFile):
    """Construit le CSV des offres qui présentent au moins un défaut.

    Le fichier sert à repérer des motifs communs pour améliorer l'analyse des
    sources : séparateur point-virgule et UTF-8 avec BOM, lisibles par Excel.
    """

    vOutput = io.StringIO()
    vWriter = csv.writer(vOutput, delimiter=";")
    vWriter.writerow(EXPORT_COLUMNS)

    for vOffer in get_offers(pDatabaseFile).to_dict("records"):
        vOffer = clean_missing_values(vOffer)
        vProblems = find_problems(vOffer)

        if vProblems:
            vOffer["problems"] = ", ".join(vProblems)
            vWriter.writerow(
                [
                    protect_formula(vOffer.get(vColumn) or "")
                    for vColumn in EXPORT_COLUMNS
                ]
            )

    rText = "﻿" + vOutput.getvalue()

    return rText
