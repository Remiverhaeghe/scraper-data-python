"""Classement des thèmes de révision par domaine et sous-domaine

Le classement repose sur des mots-clés du libellé du thème, puis de ses
compétences : un pack importé n'a rien à préciser pour être rangé.
"""

import re
import unicodedata

OTHER_DOMAIN = ("Autres", "Divers")

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


def group_themes(pThemes, pDomain=None):
    """Regroupe des thèmes par domaine puis sous-domaine, dans l'ordre d'affichage.

    Retourne une liste de (domaine, [(sous-domaine, [thèmes])]) ; pDomain limite
    le résultat à un domaine.
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
        ]
        vSections = [vSection for vSection in vSections if vSection[1]]

        if vSections:
            rGroups.append((vDomain, vSections))

    return rGroups
