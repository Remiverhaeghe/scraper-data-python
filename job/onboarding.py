"""Premiers pas : quêtes de démarrage et visite guidée par la mascotte

Les quêtes de démarrage se cochent d'elles-mêmes, d'après ce qui est déjà fait ;
les avoir toutes terminées rapporte des points une seule fois. La visite guidée
parcourt les pages principales, Boulon expliquant chacune en deux phrases.
"""

from datetime import datetime

from job.mascot import draw_mascot
from job.mobile_sync import get_last_phone_sync
from job.profile import load_profile
from job.progress import ONBOARDING_KEY
from storage.database import connect_database
from storage.history_repository import get_history
from storage.saved_searches import get_saved_searches
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Étape de la visite : (page, titre, texte, humeur de la mascotte)
TOUR_STEPS = (
    (
        "home",
        "Bienvenue",
        "Je suis Boulon, ton robot de maintenance. Je te fais visiter l'atelier : "
        "chaque page a son rôle, et l'accueil résume tout ce qui compte aujourd'hui.",
        "happy",
    ),
    (
        "search",
        "Recherche",
        "Ici, tu choisis tes sources et tes mots-clés. Enregistre ta recherche : "
        "le planificateur la relance seul, chaque jour.",
        "focused",
    ),
    (
        "offers",
        "Offres",
        "Toutes les offres trouvées, notées selon ton profil. Les meilleures "
        "remontent en tête, les doublons sont regroupés.",
        "focused",
    ),
    (
        "applications",
        "Candidatures",
        "Le suivi de tes candidatures : relances au bon moment, entretiens, "
        "mission de préparation et jeu de négociation.",
        "focused",
    ),
    (
        "quiz",
        "Révision",
        "Des questions techniques, des schémas à lire et des examens blancs pour "
        "arriver prêt en entretien.",
        "happy",
    ),
    (
        "progress",
        "Progression",
        "Chaque action rapporte des points : niveaux, quêtes du jour et trophées. "
        "Je te dirai quand tu avances bien.",
        "proud",
    ),
    (
        "settings",
        "Paramètres",
        "Le salaire visé, les notifications et le code QR qui connecte le "
        "téléphone pour réviser hors ligne. Bonne recherche !",
        "happy",
    ),
)


def count_answers(pDatabaseFile):
    """Retourne le nombre de réponses de révision enregistrées."""

    vConnection = connect_database(pDatabaseFile)

    try:
        (rCount,) = vConnection.execute("SELECT COUNT(*) FROM quiz_answer").fetchone()

    finally:
        vConnection.close()

    return rCount


def build_start_quests(pDatabaseFile, pNow=None):
    """Retourne les quêtes de démarrage, leur avancée et la date de réussite.

    La première fois que toutes sont faites, la réussite est datée : c'est ce
    qui rapporte les points, une seule fois.
    """

    vQuests = [
        {
            "label": "Renseigner tes compétences",
            "hint": "Elles notent chaque offre selon ton profil.",
            "page": "profile",
            "done": bool(load_profile(pDatabaseFile).get("skills")),
        },
        {
            "label": "Choisir tes sources et enregistrer ta recherche",
            "hint": "Le planificateur la relancera chaque jour.",
            "page": "search",
            "done": bool(get_saved_searches(pDatabaseFile)),
        },
        {
            "label": "Lancer une première recherche",
            "hint": "Les offres trouvées arrivent dans la page Offres.",
            "page": "search",
            "done": bool(get_history(pDatabaseFile, 1)),
        },
        {
            "label": "Répondre à une question de révision",
            "hint": "Un thème au choix, pour prendre la main.",
            "page": "quiz",
            "done": count_answers(pDatabaseFile) > 0,
        },
        {
            "label": "Connecter le téléphone",
            "hint": "Le code QR des Paramètres suffit, sur le même Wi-Fi.",
            "page": "settings",
            "done": get_last_phone_sync(pDatabaseFile) is not None,
        },
    ]
    vDone = sum(vQuest["done"] for vQuest in vQuests)
    vData = load_json_setting(pDatabaseFile, ONBOARDING_KEY, {}, dict)

    if vDone == len(vQuests) and not vData.get("completed_at"):
        vData["completed_at"] = (pNow or datetime.now()).isoformat(timespec="seconds")
        save_json_setting(pDatabaseFile, ONBOARDING_KEY, vData)
        logger.info("Premiers pas terminés")

    rStart = {
        "quests": vQuests,
        "done": vDone,
        "total": len(vQuests),
        "completed_at": vData.get("completed_at"),
    }

    return rStart


def build_tour():
    """Retourne les étapes de la visite guidée, avec le dessin de la mascotte."""

    rTour = [
        {
            "page": vPage,
            "title": vTitle,
            "text": vText,
            "svg": draw_mascot(vMood),
            "position": vIndex + 1,
            "count": len(TOUR_STEPS),
        }
        for vIndex, (vPage, vTitle, vText, vMood) in enumerate(TOUR_STEPS)
    ]

    return rTour
