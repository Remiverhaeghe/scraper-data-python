"""Réglages restant à faire, affichés sur l'accueil jusqu'à ce qu'ils soient faits"""

from config import BACKUP_NAS_DIRECTORY
from job.profile import load_profile
from job.settings import load_settings
from job.sources.registry import SOURCES

# Source dont l'accès se demande sur francetravail.io
FRANCE_TRAVAIL = "france-travail"


def build_setup_checklist(pDatabaseFile, pNasDirectory=BACKUP_NAS_DIRECTORY):
    """Retourne les réglages manquants : texte, conseil et page où les faire.

    La page est la même clé sur le bureau et le web (« /logs » porte la Santé).
    Liste vide quand tout est fait : l'accueil n'affiche alors plus la carte.
    """

    vProfile = load_profile(pDatabaseFile)
    vSettings = load_settings(pDatabaseFile)
    vFranceTravail = SOURCES.get(FRANCE_TRAVAIL)

    vItems = (
        (
            not vProfile.get("skills"),
            "Renseigner vos compétences",
            "Elles calculent le score de chaque offre.",
            "profile",
        ),
        (
            not any((vProfile.get("skill_levels") or {}).values()),
            "Évaluer votre niveau par compétence",
            "Une compétence peu maîtrisée compte moins dans le score.",
            "profile",
        ),
        (
            not vSettings.get("target_net_salary"),
            "Indiquer votre salaire net visé",
            "Il est comparé au salaire du marché sur chaque offre.",
            "settings",
        ),
        (
            vFranceTravail is not None and bool(vFranceTravail.get_missing_settings()),
            "Demander l'accès à l'API France Travail",
            "Sur francetravail.io, puis FRANCE_TRAVAIL_ACCESS_GRANTED dans .env.",
            "logs",
        ),
        (
            not pNasDirectory,
            "Configurer la copie des sauvegardes sur le NAS",
            "BACKUP_NAS_DIRECTORY dans .env, avec BACKUP_ENCRYPTION_KEY.",
            "logs",
        ),
    )

    rChecklist = [
        {"text": vText, "hint": vHint, "page": vPage}
        for vMissing, vText, vHint, vPage in vItems
        if vMissing
    ]

    return rChecklist
