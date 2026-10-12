"""Pays et ville d'une offre, déduits de son lieu quand la source ne les donne pas

Module sans dépendance au stockage : la migration qui complète les offres déjà
en base peut l'utiliser sans créer d'import circulaire.
"""

import re

from job.fingerprint import normalize

FRANCE = "France"

# Noms et codes de pays, normalisés (minuscules, sans accents), vers leur nom affiché
COUNTRY_ALIASES = {
    "france": FRANCE,
    "fr": FRANCE,
    "fra": FRANCE,
    "frankreich": FRANCE,
    "germany": "Allemagne",
    "deutschland": "Allemagne",
    "allemagne": "Allemagne",
    "de": "Allemagne",
    "united kingdom": "Royaume-Uni",
    "uk": "Royaume-Uni",
    "england": "Royaume-Uni",
    "royaume uni": "Royaume-Uni",
    "united states": "États-Unis",
    "usa": "États-Unis",
    "us": "États-Unis",
    "etats unis": "États-Unis",
    "spain": "Espagne",
    "espana": "Espagne",
    "espagne": "Espagne",
    "italy": "Italie",
    "italia": "Italie",
    "italie": "Italie",
    "belgium": "Belgique",
    "belgique": "Belgique",
    "switzerland": "Suisse",
    "suisse": "Suisse",
    "schweiz": "Suisse",
    "netherlands": "Pays-Bas",
    "pays bas": "Pays-Bas",
    "luxembourg": "Luxembourg",
    "ireland": "Irlande",
    "irlande": "Irlande",
    "portugal": "Portugal",
    "canada": "Canada",
    "austria": "Autriche",
    "osterreich": "Autriche",
    "poland": "Pologne",
    "pologne": "Pologne",
    # Pays fréquents dans les listes multi-pays des sources internationales
    **{
        vName: vName.title()
        for vName in (
            "japan",
            "turkey",
            "vietnam",
            "mexico",
            "norway",
            "sweden",
            "denmark",
            "finland",
            "india",
            "pakistan",
            "philippines",
            "singapore",
            "south korea",
            "australia",
            "new zealand",
            "brazil",
            "argentina",
            "peru",
            "chile",
            "colombia",
            "israel",
            "south africa",
            "nigeria",
            "egypt",
            "morocco",
            "romania",
            "czech republic",
            "greece",
            "ukraine",
        )
    },
}

# Zones de plusieurs pays : l'offre est internationale, aucun pays n'est retenu.
WORLD_REGIONS = {
    "worldwide",
    "anywhere",
    "europe",
    "emea",
    "americas",
    "latam",
    "apac",
    "international",
}

# Villes reconnues sans pays : grandes villes françaises et villes étrangères
# fréquentes dans les sources. « Paris » désigne ici la capitale française.
CITY_COUNTRIES = {
    **{
        vCity: FRANCE
        for vCity in (
            "paris",
            "marseille",
            "lyon",
            "toulouse",
            "nice",
            "nantes",
            "montpellier",
            "strasbourg",
            "bordeaux",
            "lille",
            "rennes",
            "reims",
            "toulon",
            "saint etienne",
            "le havre",
            "grenoble",
            "dijon",
            "angers",
            "nimes",
            "villeurbanne",
            "clermont ferrand",
            "le mans",
            "aix en provence",
            "brest",
            "tours",
            "amiens",
            "limoges",
            "annecy",
            "perpignan",
            "boulogne billancourt",
            "metz",
            "besancon",
            "orleans",
            "rouen",
            "mulhouse",
            "caen",
            "nancy",
            "argenteuil",
            "montreuil",
            "roubaix",
            "tourcoing",
            "avignon",
            "nanterre",
            "poitiers",
            "versailles",
            "courbevoie",
            "creteil",
            "pau",
            "la rochelle",
            "calais",
            "cannes",
            "antibes",
            "dunkerque",
            "colmar",
            "valence",
            "troyes",
            "chambery",
            "lorient",
            "vannes",
            "niort",
            "quimper",
            "bayonne",
            "ajaccio",
            "bastia",
            "la defense",
            "puteaux",
            "issy les moulineaux",
            "levallois perret",
            "saint denis",
            "massy",
            "sophia antipolis",
            "villeneuve d ascq",
            "marcq en baroeul",
            "lens",
            "douai",
            "valenciennes",
            "arras",
            "beauvais",
            "compiegne",
            "saint quentin",
            "laval",
            "cholet",
            "saint nazaire",
            "saint malo",
            "angouleme",
            "chartres",
            "evry",
            "cergy",
            "melun",
            "saint brieuc",
            "blois",
            "bourges",
            "nevers",
            "auxerre",
            "belfort",
        )
    },
    "berlin": "Allemagne",
    "munich": "Allemagne",
    "munchen": "Allemagne",
    "hamburg": "Allemagne",
    "frankfurt": "Allemagne",
    "cologne": "Allemagne",
    "koln": "Allemagne",
    "stuttgart": "Allemagne",
    "dusseldorf": "Allemagne",
    "leipzig": "Allemagne",
    "london": "Royaume-Uni",
    "londres": "Royaume-Uni",
    "manchester": "Royaume-Uni",
    "madrid": "Espagne",
    "barcelona": "Espagne",
    "barcelone": "Espagne",
    "amsterdam": "Pays-Bas",
    "brussels": "Belgique",
    "bruxelles": "Belgique",
    "geneva": "Suisse",
    "geneve": "Suisse",
    "zurich": "Suisse",
    "dublin": "Irlande",
    "lisbon": "Portugal",
    "lisbonne": "Portugal",
    "montreal": "Canada",
    "toronto": "Canada",
    "new york": "États-Unis",
    "san francisco": "États-Unis",
    "nurnberg": "Allemagne",
    "nuremberg": "Allemagne",
    "augsburg": "Allemagne",
    "mannheim": "Allemagne",
    "karlsruhe": "Allemagne",
    "hannover": "Allemagne",
    "hanover": "Allemagne",
    "bremen": "Allemagne",
    "dresden": "Allemagne",
    "dortmund": "Allemagne",
    "essen": "Allemagne",
    "bonn": "Allemagne",
    "wiesbaden": "Allemagne",
    "mainz": "Allemagne",
    "heidelberg": "Allemagne",
    "freiburg": "Allemagne",
    "munster": "Allemagne",
    "regensburg": "Allemagne",
    "ulm": "Allemagne",
    "kiel": "Allemagne",
    "potsdam": "Allemagne",
    "aachen": "Allemagne",
    "bielefeld": "Allemagne",
    "wurzburg": "Allemagne",
    "ingolstadt": "Allemagne",
    "darmstadt": "Allemagne",
    "wien": "Autriche",
    "vienna": "Autriche",
    "graz": "Autriche",
    "linz": "Autriche",
    "salzburg": "Autriche",
    "innsbruck": "Autriche",
    "lausanne": "Suisse",
    "bern": "Suisse",
    "berne": "Suisse",
    "basel": "Suisse",
    "bale": "Suisse",
    "lugano": "Suisse",
    "lucerne": "Suisse",
    "luzern": "Suisse",
    "edinburgh": "Royaume-Uni",
    "glasgow": "Royaume-Uni",
    "birmingham": "Royaume-Uni",
    "bristol": "Royaume-Uni",
    "cambridge": "Royaume-Uni",
    "oxford": "Royaume-Uni",
    "leeds": "Royaume-Uni",
    "liverpool": "Royaume-Uni",
    "abingdon": "Royaume-Uni",
    "westminster": "Royaume-Uni",
    "belfast": "Royaume-Uni",
    "valencia": "Espagne",
    "valence": "Espagne",
    "seville": "Espagne",
    "sevilla": "Espagne",
    "malaga": "Espagne",
    "bilbao": "Espagne",
    "rotterdam": "Pays-Bas",
    "utrecht": "Pays-Bas",
    "eindhoven": "Pays-Bas",
    "antwerp": "Belgique",
    "anvers": "Belgique",
    "gent": "Belgique",
    "gand": "Belgique",
    "liege": "Belgique",
    "namur": "Belgique",
    "charleroi": "Belgique",
    "milan": "Italie",
    "milano": "Italie",
    "rome": "Italie",
    "roma": "Italie",
    "turin": "Italie",
    "torino": "Italie",
    "warsaw": "Pologne",
    "varsovie": "Pologne",
    "krakow": "Pologne",
    "cracovie": "Pologne",
    "wroclaw": "Pologne",
}

# Mots sans rapport avec le lieu, retirés avant une seconde recherche :
# « Paris Office », « Zurich HQ », « Remote in Deutschland »
FILLER_WORDS_PATTERN = re.compile(
    r"\b(?:office|hq|headquarters|remote|hybrid|onsite|on site|in|only|area|"
    r"based|preferred)\b",
    re.IGNORECASE,
)

# Code postal français ou département entre parenthèses : « 59000 », « (59) », « (2A) »
FRENCH_POSTAL_PATTERN = re.compile(r"\b\d{5}\b|\((?:\d{2,3}|2[ab])\)", re.IGNORECASE)

# Régions françaises dont le nom contient celui du pays : « Hauts-de-France »
FRENCH_REGION_PATTERN = re.compile(r"france")

SEGMENT_SEPARATORS = re.compile(r"[,;/|]| - ")


def is_known_place(pKey):
    """Indique si un lieu normalisé est une zone, un pays ou une ville connus."""

    rKnown = (
        pKey in WORLD_REGIONS
        or pKey.split()[0] in WORLD_REGIONS
        or pKey in COUNTRY_ALIASES
        or pKey in CITY_COUNTRIES
        or bool(FRENCH_REGION_PATTERN.search(pKey))
    )

    return rKnown


def detect_location(pLocation, pCountry=None):
    """Retourne (pays, ville) déduits du lieu ; None quand ils restent inconnus.

    Une liste de plusieurs pays ou une zone (« Worldwide ») ne donne pas de pays.
    """

    vCountries = set()
    rCity = None

    if pCountry:
        vCountries.add(COUNTRY_ALIASES.get(normalize(pCountry), str(pCountry).strip()))

    vLocation = str(pLocation or "")

    for vSegment in SEGMENT_SEPARATORS.split(vLocation):
        # Sans chiffres ni parenthèses : « 59000 Lille (59) » donne « lille ».
        vKey = normalize(re.sub(r"\(.*?\)|\d+", " ", vSegment))

        if vKey and not is_known_place(vKey):
            vKey = " ".join(FILLER_WORDS_PATTERN.sub(" ", vKey).split())
            vSegment = FILLER_WORDS_PATTERN.sub(" ", vSegment)

        if not vKey:
            continue

        if vKey in WORLD_REGIONS or vKey.split()[0] in WORLD_REGIONS:
            vCountries.add(None)

        elif vKey in COUNTRY_ALIASES:
            vCountries.add(COUNTRY_ALIASES[vKey])

        elif FRENCH_REGION_PATTERN.search(vKey):
            vCountries.add(FRANCE)

        elif vKey in CITY_COUNTRIES:
            vCountries.add(CITY_COUNTRIES[vKey])
            rCity = rCity or vSegment.strip(" ()0123456789").strip()

    # Un code postal à 5 chiffres n'indique la France que faute d'autre indice :
    # « München (81671) » est allemand.
    if not vCountries and FRENCH_POSTAL_PATTERN.search(vLocation):
        vCountries.add(FRANCE)

    rCountry = vCountries.pop() if len(vCountries) == 1 else None

    rLocation = (rCountry, rCity if rCountry else None)

    return rLocation


def add_location(pItems):
    """Complète le pays et la ville des offres qui ne les ont pas."""

    vItems = pItems.copy()

    vColumns = vItems.reindex(columns=["location", "country", "city"])

    vDetected = [
        detect_location(
            None if not isinstance(vLocation, str) else vLocation,
            vCountry if isinstance(vCountry, str) and vCountry else None,
        )
        for vLocation, vCountry, _ in vColumns.itertuples(index=False)
    ]

    vItems["country"] = [
        vCountry if isinstance(vCountry, str) and vCountry else vFound[0]
        for vCountry, vFound in zip(vColumns["country"], vDetected)
    ]
    vItems["city"] = [
        vCity if isinstance(vCity, str) and vCity else vFound[1]
        for vCity, vFound in zip(vColumns["city"], vDetected)
    ]

    rItems = vItems

    return rItems
