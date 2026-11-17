"""Migrations du schéma SQLite à partir de la version 21

Suite de storage/migrations.py, séparée pour garder des fichiers courts ;
MIGRATIONS, dans storage/migrations.py, les range dans l'ordre. Une nouvelle
version s'ajoute à la fin de ce fichier.
"""

from utils.logger import get_logger

logger = get_logger(__name__)


def migrate_to_v21(pConnection):
    """Retire les anciennes offres que la collecte actuelle écarterait.

    Hacker News : messages sans forme d'offre (réponses, remarques sur le fil),
    reconnus à leur en-tête sans séparateur, rangé à la fois en titre et en
    entreprise. Findwork : offres sans titre. Une offre suivie (candidature,
    relance, pièce jointe, journal d'entretien) est toujours gardée.
    """

    # pylint: disable=import-outside-toplevel
    from job.sources.hackernews.parser import is_job_post

    vUntouched = """
        NOT EXISTS (SELECT 1 FROM job_application AS a
                    WHERE a.source = o.source AND a.source_id = o.source_id)
        AND NOT EXISTS (SELECT 1 FROM job_follow_up AS f
                        WHERE f.source = o.source AND f.source_id = o.source_id)
        AND NOT EXISTS (SELECT 1 FROM job_attachment AS j
                        WHERE j.source = o.source AND j.source_id = o.source_id)
        AND NOT EXISTS (SELECT 1 FROM interview_note AS n
                        WHERE n.source = o.source AND n.source_id = o.source_id)
        """

    vHeaderRows = pConnection.execute(f"""
        SELECT source_id, title, company FROM job_offer AS o
        WHERE source = 'hackernews'
        AND (title IS NULL OR company IS NULL OR title = company)
        AND {vUntouched}
        """).fetchall()  # nosec B608

    vRejected = []
    vKept = []

    for vSourceId, vTitle, vCompany in vHeaderRows:
        if not is_job_post({"text": vTitle or vCompany or ""}):
            vRejected.append((vSourceId,))
        elif vTitle and vTitle == vCompany:
            vKept.append((vSourceId,))

    pConnection.executemany(
        "DELETE FROM job_offer WHERE source = 'hackernews' AND source_id = ?",
        vRejected,
    )
    pConnection.executemany(
        "UPDATE job_offer SET company = NULL "
        "WHERE source = 'hackernews' AND source_id = ?",
        vKept,
    )

    vFindwork = pConnection.execute(f"""
        DELETE FROM job_offer AS o
        WHERE source = 'findwork' AND (title IS NULL OR title = '')
        AND {vUntouched}
        """).rowcount  # nosec B608

    logger.info(
        "Nettoyage des offres : %s message(s) Hacker News sans forme d'offre et "
        "%s offre(s) Findwork sans titre retirés, %s entreprise(s) répétant le "
        "titre vidée(s)",
        len(vRejected),
        vFindwork,
        len(vKept),
    )


def migrate_to_v22(pConnection):
    """Décode les entités HTML (&eacute;) des offres Adzuna déjà enregistrées.

    Sans ce décodage, une recherche « électricien » ne trouvait pas
    « &Eacute;lectricien ». L'entreprise absente est retrouvée dans le texte,
    où les agences d'intérim se nomment.
    """

    # pylint: disable=import-outside-toplevel
    from job.sources.adzuna.parser import find_agency, read_text

    vRows = pConnection.execute("""
        SELECT source_id, title, company, description
        FROM job_offer
        WHERE source = 'adzuna'
        AND (title LIKE '%&%;%' OR description LIKE '%&%;%' OR company IS NULL)
        """).fetchall()

    vUpdates = []
    vCompanies = 0

    for vSourceId, vTitle, vCompany, vDescription in vRows:
        vText = read_text(vDescription)
        vFound = vCompany or find_agency(vText)
        vCompanies += vFound is not None and vCompany is None
        vUpdates.append((read_text(vTitle), vFound, vText, vSourceId))

    pConnection.executemany(
        """
        UPDATE job_offer SET title = ?, company = ?, description = ?
        WHERE source = 'adzuna' AND source_id = ?
        """,
        vUpdates,
    )

    logger.info(
        "Offres Adzuna relues : %s texte(s) décodé(s), %s entreprise(s) retrouvée(s)",
        len(vUpdates),
        vCompanies,
    )


def migrate_to_v23(pConnection):
    """Ajoute le cache des traductions : une description traduite ne l'est qu'une fois."""

    pConnection.execute("""
        CREATE TABLE translation_cache (
            text_key TEXT PRIMARY KEY,
            translation TEXT NOT NULL,
            translated_at TEXT NOT NULL
        )
        """)


def migrate_to_v24(pConnection):
    """Indexe la date de découverte des offres.

    La liste des offres, triée par cette date, et les comptes par jour lisaient
    toute la table : mesuré sur 3 400 offres, 72 ms ramenés à 17 ms et 6 ms à
    moins d'une milliseconde.
    """

    pConnection.execute(
        "CREATE INDEX idx_job_offer_first_seen ON job_offer(first_seen_at, published_at)"
    )


def migrate_to_v25(pConnection):
    """Ajoute les coordonnées des offres et le cache du géocodage de leurs lieux.

    Un lieu introuvable est gardé sans coordonnées : il n'est pas redemandé.
    """

    pConnection.execute("ALTER TABLE job_offer ADD COLUMN latitude REAL")
    pConnection.execute("ALTER TABLE job_offer ADD COLUMN longitude REAL")
    pConnection.execute("""
        CREATE TABLE geo_cache (
            location_key TEXT PRIMARY KEY,
            latitude REAL,
            longitude REAL,
            label TEXT,
            looked_up_at TEXT NOT NULL
        )
        """)


def migrate_to_v26(pConnection):
    """Ajoute les compétences repérées dans le texte de chaque offre.

    Les chercher à chaque affichage prenait six secondes pour mille offres ; elles
    sont désormais calculées une fois, puis lues (job/skill_cache.py).
    """

    pConnection.execute("ALTER TABLE job_offer ADD COLUMN detected_skills TEXT")


def migrate_to_v27(pConnection):
    """Décode les entités HTML (&amp;) des titres et entreprises déjà enregistrés.

    Findwork, Arbeitnow ou La bonne alternance les envoient encodées ; elles le
    sont désormais à la complétion des offres (job/completion.py). L'empreinte
    est recalculée sur le titre décodé, les compétences le seront au prochain
    passage.
    """

    # pylint: disable=import-outside-toplevel
    from job.completion import decode_text
    from job.fingerprint import build_fingerprint

    vRows = pConnection.execute("""
        SELECT source, source_id, title, company, location
        FROM job_offer
        WHERE title LIKE '%&%;%' OR company LIKE '%&%;%'
        """).fetchall()

    vUpdates = []

    for vSource, vSourceId, vTitle, vCompany, vLocation in vRows:
        vOffer = {
            "title": decode_text(vTitle),
            "company": decode_text(vCompany),
            "location": vLocation,
        }
        vUpdates.append(
            (
                vOffer["title"],
                vOffer["company"],
                build_fingerprint(vOffer),
                vSource,
                vSourceId,
            )
        )

    pConnection.executemany(
        """
        UPDATE job_offer
        SET title = ?, company = ?, fingerprint = ?, detected_skills = NULL
        WHERE source = ? AND source_id = ?
        """,
        vUpdates,
    )

    logger.info("Entités HTML décodées : %s offre(s)", len(vUpdates))


def migrate_to_v28(pConnection):
    """Garde le département des lieux et des offres placées, pour Mon marché par région.

    Les lieux déjà cherchés le reçoivent au prochain placement des offres.
    """

    pConnection.execute("ALTER TABLE geo_cache ADD COLUMN department TEXT")
    pConnection.execute("ALTER TABLE job_offer ADD COLUMN french_department TEXT")


def migrate_to_v29(pConnection):
    """Donne leur nom affiché aux pays enregistrés en code (« FR » devient « France »).

    SmartRecruiters donnait le code : ses offres échappaient au filtre France,
    à Mon marché et au placement sur la carte.
    """

    # pylint: disable=import-outside-toplevel
    from job.location import normalize_country

    vCountries = [
        vRow[0]
        for vRow in pConnection.execute(
            "SELECT DISTINCT country FROM job_offer WHERE country IS NOT NULL"
        )
    ]
    vUpdates = [
        (normalize_country(vCountry), vCountry)
        for vCountry in vCountries
        if normalize_country(vCountry) != vCountry
    ]

    pConnection.executemany(
        "UPDATE job_offer SET country = ? WHERE country = ?", vUpdates
    )

    logger.info(
        "Pays enregistrés en code renommés : %s",
        ", ".join(f"{vOld} -> {vNew}" for vNew, vOld in vUpdates) or "aucun",
    )


def migrate_to_v30(pConnection):
    """Oublie les lieux restés introuvables, cherchés de nouveau au prochain placement.

    « Lyon, Auvergne-Rhône-Alpes, France » échouait tel quel : la ville seule est
    désormais essayée (job/geocoding.py).
    """

    vCount = pConnection.execute(
        "DELETE FROM geo_cache WHERE latitude IS NULL"
    ).rowcount

    logger.info("Lieux introuvables à chercher de nouveau : %s", vCount)


def migrate_to_v31(pConnection):
    """Garde l'historique des statuts de chaque candidature.

    Des déclencheurs l'alimentent à chaque création ou changement de statut,
    quel que soit le chemin (formulaire, téléphone, réponse Gmail). Le statut
    actuel des candidatures existantes en est le premier élément.
    """

    pConnection.execute("""
        CREATE TABLE application_history (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            status TEXT NOT NULL,
            changed_at TEXT NOT NULL
        )
        """)
    pConnection.execute(
        "CREATE INDEX application_history_offer"
        " ON application_history (source, source_id)"
    )
    pConnection.execute("""
        CREATE TRIGGER application_status_created
        AFTER INSERT ON job_application
        BEGIN
            INSERT INTO application_history (source, source_id, status, changed_at)
            VALUES (
                NEW.source,
                NEW.source_id,
                NEW.status,
                strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
            );
        END
        """)
    pConnection.execute("""
        CREATE TRIGGER application_status_changed
        AFTER UPDATE OF status ON job_application
        WHEN NEW.status IS NOT OLD.status
        BEGIN
            INSERT INTO application_history (source, source_id, status, changed_at)
            VALUES (
                NEW.source,
                NEW.source_id,
                NEW.status,
                strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
            );
        END
        """)
    vCount = pConnection.execute("""
        INSERT INTO application_history (source, source_id, status, changed_at)
        SELECT
            source,
            source_id,
            status,
            COALESCE(
                responded_at,
                applied_at,
                strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
            )
        FROM job_application
        """).rowcount

    logger.info("Historique des statuts commencé pour %s candidature(s)", vCount)


def migrate_to_v32(pConnection):
    """Garde l'adresse du recruteur, utilisée pour envoyer les relances."""

    pConnection.execute("ALTER TABLE job_application ADD COLUMN contact_email TEXT")


def migrate_to_v33(pConnection):
    """Relit la période des salaires Adzuna d'après leur montant, puis leur net.

    Présentés comme annuels, des taux horaires (12 €) et salaires mensuels
    étaient écartés comme incohérents : seuls restaient les salaires de cadres.
    """

    from config import NET_SALARY_RATIO
    from job.salary import to_net_monthly
    from job.sources.adzuna.parser import read_salary_period

    vRows = pConnection.execute("""
        SELECT source_id, salary_min, salary_max
        FROM job_offer
        WHERE source = 'adzuna' AND salary_period = 'year'
            AND COALESCE(salary_min, salary_max) IS NOT NULL
        """).fetchall()
    vUpdates = []

    for vSourceId, vMinimum, vMaximum in vRows:
        vPeriod = read_salary_period(max(vMinimum or 0, vMaximum or 0))

        if vPeriod != "year":
            vUpdates.append(
                (
                    vPeriod,
                    to_net_monthly(vMinimum, vPeriod, NET_SALARY_RATIO),
                    to_net_monthly(vMaximum, vPeriod, NET_SALARY_RATIO),
                    vSourceId,
                )
            )

    pConnection.executemany(
        """
        UPDATE job_offer
        SET salary_period = ?, salary_net_monthly_min = ?,
            salary_net_monthly_max = ?
        WHERE source = 'adzuna' AND source_id = ?
        """,
        vUpdates,
    )

    logger.info("Période des salaires Adzuna corrigée : %s offre(s)", len(vUpdates))


def migrate_to_v34(pConnection):
    """Ajoute le diplôme demandé par chaque offre, repéré ensuite en tâche de fond."""

    pConnection.execute("ALTER TABLE job_offer ADD COLUMN education_level INTEGER")


def migrate_to_v35(pConnection):
    """Garde les parties des tests de recrutement : catégorie, score et durée."""

    pConnection.execute("""
        CREATE TABLE aptitude_session (
            id INTEGER PRIMARY KEY,
            category TEXT NOT NULL,
            correct INTEGER NOT NULL,
            total INTEGER NOT NULL,
            duration_seconds INTEGER NOT NULL,
            played_at TEXT NOT NULL
        )
        """)
    pConnection.execute(
        "CREATE INDEX aptitude_session_category ON aptitude_session (category)"
    )
