"""Classement des thèmes de révision par domaine et sous-domaine

Le classement repose sur des mots-clés du libellé du thème, puis de ses
compétences : un pack importé n'a rien à préciser pour être rangé.
"""

import re
import unicodedata

OTHER_DOMAIN = ("Autres", "Divers")

# Icône de chaque domaine et sous-domaine, partagée par le bureau et le web
DOMAIN_ICONS = {
    "Informatique": "terminal",
    "Réseau et sécurité": "lock",
    "Industrie": "settings",
    "Développement": "code",
    "Données": "database",
    "Exploitation et DevOps": "server",
    "Outils et méthodes": "list-checks",
    "Réseau": "network",
    "Sécurité et identité": "shield",
    "Maintenance": "wrench",
    "Électricité et énergie": "zap",
    "Mécanique et fluides": "settings",
    "Automatisme": "cpu",
}

# Ordre d'affichage des domaines et de leurs sous-domaines
DOMAIN_ORDER = {
    "Informatique": (
        "Développement",
        "Données",
        "Exploitation et DevOps",
        "Outils et méthodes",
    ),
    "Réseau et sécurité": ("Réseau", "Sécurité et identité"),
    "Industrie": (
        "Maintenance",
        "Électricité et énergie",
        "Mécanique et fluides",
        "Automatisme",
    ),
    OTHER_DOMAIN[0]: (OTHER_DOMAIN[1],),
}

# Ordre d'évaluation : du plus précis au plus général. « Cybersécurité et
# réseau » relève de la sécurité, « Python et automatisation » du développement.
DOMAIN_RULES = (
    (
        "Réseau et sécurité",
        "Sécurité et identité",
        "securite cybersecurite ldap active directory sso saml oauth oauth2 openid "
        "authentification identite",
    ),
    ("Réseau et sécurité", "Réseau", "reseau reseaux tcp dns routage"),
    ("Industrie", "Maintenance", "maintenance"),
    (
        "Industrie",
        "Électricité et énergie",
        "electricite electronique energie metrologie",
    ),
    ("Industrie", "Mécanique et fluides", "mecanique hydraulique pneumatique"),
    (
        "Informatique",
        "Développement",
        "java spring python javascript typescript angular react kotlin php node "
        "backend frontend",
    ),
    ("Industrie", "Automatisme", "automatisme plc"),
    ("Informatique", "Données", "sql base donnees postgresql mysql oracle mongodb"),
    (
        "Informatique",
        "Exploitation et DevOps",
        "docker kubernetes devops cloud deploiement tomcat jvm ram logs depannage "
        "console navigateur linux exploitation",
    ),
    (
        "Informatique",
        "Outils et méthodes",
        "git maven tests qualite pratiques api",
    ),
)

WORD_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_words(pText):
    """Retourne les mots d'un texte, en minuscules et sans accents."""

    vText = unicodedata.normalize("NFKD", str(pText or "")).encode("ascii", "ignore")

    rWords = set(WORD_PATTERN.findall(vText.decode().lower()))

    return rWords


def classify_theme(pLabel, pSkills=()):
    """Retourne le domaine et le sous-domaine d'un thème."""

    rDomain = OTHER_DOMAIN

    # Le libellé décide d'abord ; les compétences départagent un libellé vague.
    for vText in (pLabel, " ".join(pSkills)):
        vWords = normalize_words(vText)

        vMatch = next(
            (
                (vDomain, vSubdomain)
                for vDomain, vSubdomain, vKeywords in DOMAIN_RULES
                if vWords & set(vKeywords.split())
            ),
            None,
        )

        if vMatch:
            rDomain = vMatch
            break

    return rDomain


def group_themes(pThemes, pDomain=None, pSubdomain=None):
    """Regroupe des thèmes par domaine puis sous-domaine, dans l'ordre d'affichage.

    Retourne une liste de (domaine, [(sous-domaine, [thèmes])]) ; pDomain et
    pSubdomain limitent le résultat à un domaine, puis à un sous-domaine.
    """

    rGroups = []

    for vDomain, vSubdomains in DOMAIN_ORDER.items():
        if pDomain and vDomain != pDomain:
            continue

        vSections = [
            (
                vSubdomain,
                [
                    vTheme
                    for vTheme in pThemes
                    if (vTheme["domain"], vTheme["subdomain"]) == (vDomain, vSubdomain)
                ],
            )
            for vSubdomain in vSubdomains
            if not pSubdomain or vSubdomain == pSubdomain
        ]
        vSections = [vSection for vSection in vSections if vSection[1]]

        if vSections:
            rGroups.append((vDomain, vSections))

    return rGroups


def locate_guide(pGuide, pThemes):
    """Retourne le domaine et le sous-domaine d'un guide pratique.

    Un guide rattaché à un thème suit ce thème ; sinon, son titre le classe.
    """

    vTheme = next(
        (vTheme for vTheme in pThemes if vTheme["key"] == pGuide["theme"]), None
    )

    rDomain = (
        (vTheme["domain"], vTheme["subdomain"])
        if vTheme
        else classify_theme(pGuide["title"])
    )

    return rDomain


def filter_guides(pGuides, pThemes, pDomain=None, pSubdomain=None):
    """Garde les guides de la catégorie affichée ; tous sans filtre."""

    rGuides = []

    for vGuide in pGuides:
        vDomain, vSubdomain = locate_guide(vGuide, pThemes)

        if (not pDomain or vDomain == pDomain) and (
            not pSubdomain or vSubdomain == pSubdomain
        ):
            rGuides.append(vGuide)

    return rGuides


def build_category_progress(pThemes):
    """Résume la progression par domaine puis sous-domaine, pour les statistiques.

    Retourne des lignes {label, level (0 domaine, 1 sous-domaine), icon, themes,
    correct, total, score, due}, dans l'ordre d'affichage.
    """

    def summarize(pLabel, pLevel, pThemes):
        vCorrect = sum(vTheme["correct"] for vTheme in pThemes)
        vTotal = sum(vTheme["total"] for vTheme in pThemes)

        rRow = {
            "label": pLabel,
            "level": pLevel,
            "icon": DOMAIN_ICONS.get(pLabel, "tag"),
            "themes": len(pThemes),
            "correct": vCorrect,
            "total": vTotal,
            "score": round(100 * vCorrect / vTotal) if vTotal else 0,
            "due": sum(vTheme["due"] for vTheme in pThemes),
        }

        return rRow

    rRows = []

    for vDomain, vSections in group_themes(pThemes):
        rRows.append(
            summarize(
                vDomain, 0, [vTheme for _, vThemes in vSections for vTheme in vThemes]
            )
        )
        rRows += [
            summarize(vSubdomain, 1, vThemes) for vSubdomain, vThemes in vSections
        ]

    return rRows


def count_categories(pThemes):
    """Compte les thèmes de chaque rubrique, rubriques vides du classement comprises.

    Les clés sont (None, None) pour l'ensemble, (domaine, None) pour un domaine
    et (domaine, sous-domaine), dans l'ordre d'affichage.
    """

    rCounts = {(None, None): len(pThemes)}

    for vDomain, vSubdomains in DOMAIN_ORDER.items():
        vThemes = [vTheme for vTheme in pThemes if vTheme["domain"] == vDomain]

        # « Autres » n'apparaît que s'il contient des thèmes.
        if (vDomain, vSubdomains[0]) == OTHER_DOMAIN and not vThemes:
            continue

        rCounts[(vDomain, None)] = len(vThemes)

        for vSubdomain in vSubdomains:
            rCounts[(vDomain, vSubdomain)] = sum(
                1 for vTheme in vThemes if vTheme["subdomain"] == vSubdomain
            )

    return rCounts
