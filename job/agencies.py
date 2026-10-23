"""Agences d'intérim et de placement, reconnues pour masquer leurs annonces"""

# Noms normalisés (job.fingerprint.normalize_company) : cherchés comme mot dans
# le nom de l'entreprise, « adecco medical » ou « proman 123 » compris.
INTERIM_AGENCIES = (
    "abalone",
    "actual",
    "adecco",
    "aston interim",
    "atoll interim",
    "camo emploi",
    "crit",
    "domino rh",
    "ergalis",
    "expectra",
    "gojob",
    "groupe fed",
    "id interim",
    "interim nation",
    "kelly services",
    "leader interim",
    "lynx rh",
    "manpower",
    "partnaire",
    "proman",
    "randstad",
    "ressources interim",
    "samsic emploi",
    "staffmatch",
    "start people",
    "supplay",
    "synergie",
    "temporis",
    "triangle interim",
)

# Mentions d'une annonce publiée par une agence pour le compte d'un client
AGENCY_MENTIONS = ("agence d'intérim", "agence d’intérim", "agence d'interim")
