"""Mots de l'annonce à reprendre dans le CV et la lettre, repérés par règles

Les logiciels de tri des candidatures et les recruteurs cherchent les termes de
l'annonce tels quels : l'intitulé du poste, les compétences, les qualités et les
conditions demandées. Pour chacun, on indique s'il figure déjà dans le profil.
Rien n'est ajouté au CV : une compétence manquante se prépare pour l'entretien.
"""

import re

from job.fingerprint import GENDER_MARKERS, normalize

# Mentions de contrat ou de lieu accolées à l'intitulé, sans valeur de mot-clé
TITLE_NOISE = re.compile(
    r"\s[-–—|]\s.*$|/\s*[nx]\b|\((?:cdi|cdd|interim|intérim|alternance|[^)]*\d{2}[^)]*)\)",
    re.IGNORECASE,
)

# Qualités : libellé à reprendre, motif cherché dans le texte normalisé
QUALITIES = {
    "Autonomie": r"\bautonom",
    "Rigueur": r"\brigoureu|\brigueur",
    "Réactivité": r"\breacti",
    "Esprit d'équipe": r"\b(?:esprit|travail) d equipe\b",
    "Polyvalence": r"\bpolyvalen",
    "Sens de l'organisation": r"\b(?:sens de l|bonne|esprit d) organisation"
    r"|\bvous etes organise",
    "Curiosité": r"\bcurio",
    "Force de proposition": r"\bforce de proposition",
    "Respect des règles de sécurité": r"\b(?:respect|culture)\b.{0,30}\bsecurite\b",
    "Sens du service": r"\bsens du service|\brelation client",
    "Adaptabilité": r"\badapta(?:bilite|tion)\b|capacite d adaptation",
    "Esprit d'analyse": r"\b(?:esprit|capacite) d analyse|\banalytique",
}

# Conditions du poste : à aborder dans la lettre plutôt que dans le CV
CONDITIONS = {
    "Astreintes": r"\bastreinte",
    "Travail posté": r"\b[235] ?x ?8\b|\bequipes? (?:alternantes|successives)"
    r"|\b(?:travail|horaires) postes?\b",
    "Travail de nuit": r"\bde nuit\b",
    "Week-ends": r"\bweek ?end",
    "Déplacements": r"\bdeplacements?\b",
    "Permis B": r"\bpermis b\b",
    "Anglais": r"\banglais\b",
}


def clean_title(pTitle):
    """Retourne l'intitulé de l'annonce sans mention de genre, de contrat ni de lieu."""

    vTitle = GENDER_MARKERS.sub(" ", str(pTitle or ""))

    rTitle = " ".join(TITLE_NOISE.sub(" ", vTitle).split()).strip(" -–—|,")

    return rTitle


def get_profile_text(pProfile):
    """Retourne le texte normalisé du profil, tel qu'il apparaît dans le CV."""

    rText = normalize(
        " ; ".join(
            [
                pProfile.get("headline") or "",
                *(pProfile.get("skills") or []),
                *(
                    # Les compétences d'une expérience sont un texte ou une liste
                    (
                        " ; ".join(vValue)
                        if isinstance(vValue := vExperience.get(vField), list)
                        else vValue or ""
                    )
                    for vExperience in pProfile.get("experiences") or []
                    for vField in ("title", "skills", "achievement")
                ),
            ]
        )
    )

    return rText


def contains_term(pText, pTerm):
    """Indique si un texte normalisé contient un terme, mot pour mot."""

    vTerm = normalize(pTerm)

    rFound = bool(vTerm) and re.search(rf"\b{re.escape(vTerm)}\b", pText) is not None

    return rFound


def find_terms(pRules, pOfferText, pProfileText):
    """Retourne les termes de règles trouvés dans l'annonce, et s'ils sont dans le profil."""

    rTerms = [
        {"term": vLabel, "in_cv": re.search(vPattern, pProfileText) is not None}
        for vLabel, vPattern in pRules.items()
        if re.search(vPattern, pOfferText)
    ]

    return rTerms


def build_keyword_advice(pProfile, pOffer, pMatch, pOfferText):
    """Retourne les mots de l'annonce à reprendre, chacun marqué présent ou absent du CV.

    pMatch vient de job.preparation.match_offer ; les compétences couvertes mais
    écrites autrement dans le profil sont signalées pour reprendre le terme exact.
    """

    vProfileText = get_profile_text(pProfile)
    vOfferText = normalize(pOfferText)
    vTitle = clean_title(pOffer.get("title"))
    vRequired = set(pMatch.get("required") or [])

    rAdvice = {
        "title": vTitle,
        "title_in_cv": contains_term(vProfileText, vTitle),
        # Compétences exigées d'abord : ce sont elles que le tri cherche en premier
        "skills": sorted(
            (
                {
                    "term": vSkill,
                    "required": vSkill in vRequired,
                    "in_cv": contains_term(vProfileText, vSkill),
                }
                for vSkill in pMatch.get("covered") or []
            ),
            key=lambda pSkill: not pSkill["required"],
        ),
        "qualities": find_terms(QUALITIES, vOfferText, vProfileText),
        "conditions": [
            vTerm["term"] for vTerm in find_terms(CONDITIONS, vOfferText, "")
        ],
        "missing_required": [
            vSkill for vSkill in pMatch.get("missing") or [] if vSkill in vRequired
        ],
    }

    return rAdvice
