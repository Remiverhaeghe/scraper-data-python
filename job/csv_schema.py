"""Colonnes communes des offres d'emploi"""

JOB_COLUMNS = [
    # ------------------------------------------------------------------------
    # Identification de l'offre
    # ------------------------------------------------------------------------
    # Intitulé du poste
    "title",
    # Nom de l'entreprise
    "company",
    # Identifiant de l'entreprise fourni par la source, lorsqu'il existe
    "company_id",
    # Source ayant fourni l'offre : france_travail, greenhouse, lever, etc.
    "source",
    # Identifiant unique de l'offre chez la source
    # L'identification technique d'une offre repose sur source + source_id
    "source_id",
    # URL permettant d'accéder à l'offre sur le site source
    "url",
    # ------------------------------------------------------------------------
    # Localisation
    # ------------------------------------------------------------------------
    # Localisation complète telle que fournie par la source
    "location",
    # Ville de l'offre lorsque l'information est disponible
    "city",
    # Code postal de l'offre lorsque l'information est disponible
    "postal_code",
    # Pays de l'offre
    "country",
    # Distance entre la localisation recherchée et l'offre, en kilomètres
    "distance_km",
    # ------------------------------------------------------------------------
    # Contrat et type d'emploi
    # ------------------------------------------------------------------------
    # Libellé du contrat : CDI, CDD, alternance, etc.
    "contract",
    # Code ou type de contrat fourni par la source
    "contract_type",
    # Type d'emploi : temps plein, temps partiel, etc.
    "employment_type",
    # ------------------------------------------------------------------------
    # Rémunération
    # ------------------------------------------------------------------------
    # Rémunération minimale proposée
    "salary_min",
    # Rémunération maximale proposée
    "salary_max",
    # Devise de la rémunération : EUR, USD, etc.
    "salary_currency",
    # Période de référence : heure, mois, année, etc.
    "salary_period",
    # ------------------------------------------------------------------------
    # Télétravail
    # ------------------------------------------------------------------------
    # Indique si le télétravail est proposé
    "remote",
    # Nombre de jours de télétravail possibles
    "remote_days",
    # Type de télétravail : hybride, complet, occasionnel, etc.
    "remote_type",
    # ------------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------------
    # Station de métro la plus proche
    "nearest_metro",
    # Distance entre l'offre et la station de métro, en kilomètres
    "metro_distance_km",
    # ------------------------------------------------------------------------
    # Dates fournies par la source
    # ------------------------------------------------------------------------
    # Date métier principale fournie par la source
    "date",
    # Date de publication de l'offre
    "published_at",
    # Date de dernière modification connue par la source
    "updated_at",
    # ------------------------------------------------------------------------
    # Dates gérées par notre scraper
    # ------------------------------------------------------------------------
    # Date et heure de la dernière récupération de l'offre par notre scraper
    "scraped_at",
    # Date et heure de la première découverte de l'offre par notre scraper
    "first_seen_at",
    # ------------------------------------------------------------------------
    # Contenu de l'offre
    # ------------------------------------------------------------------------
    # Description générale du poste
    "description",
    # Missions principales du poste
    "missions",
    # Compétences ou prérequis demandés par l'entreprise
    "requirements",
    # Formation ou niveau d'études demandé
    "education",
    # Compétences techniques ou professionnelles recherchées
    "skills",
    # ------------------------------------------------------------------------
    # Informations complémentaires
    # ------------------------------------------------------------------------
    # Département ou service auquel le poste est rattaché
    "department",
    # Niveau d'expérience demandé
    "experience_level",
    # Type ou catégorie de poste
    "job_type",
]
