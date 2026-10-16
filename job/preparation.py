"""Préparation d'une candidature : correspondance, CV, entretien et lettre

Tout repose sur des règles et sur le profil saisi : aucune donnée ne quitte
l'application et aucun service payant n'est utilisé.
"""

from job.enrichment import detect_skills
from job.fingerprint import GENDER_MARKERS
from job.presentation import to_list

# Questions toujours utiles en fin d'entretien
GENERAL_QUESTIONS = (
    "Comment l'équipe est-elle organisée, et avec qui travaillerais-je au quotidien ?",
    "Quelles sont les priorités du poste pour les six premiers mois ?",
    "Comment se déroule l'intégration d'un nouveau collaborateur ?",
)

# Nombre de compétences mises en avant dans la lettre
LETTER_SKILLS = 3


def lower_first(pText):
    """Met la première lettre en minuscule, pour insérer un texte dans une phrase."""

    rText = pText[:1].lower() + pText[1:]

    return rText


def get_offer_text(pOffer):
    """Retourne le texte d'une offre où chercher les compétences demandées."""

    rText = " ".join(
        str(pOffer.get(vColumn) or "")
        for vColumn in ("title", "description", "missions", "requirements")
    )

    return rText


def get_offer_skills(pOffer):
    """Retourne les compétences demandées : celles de la source et celles du texte."""

    rSkills = list(
        dict.fromkeys(
            [
                *(to_list(pOffer.get("skills")) or []),
                *detect_skills(get_offer_text(pOffer)),
            ]
        )
    )

    return rSkills


def same_skill(pFirst, pSecond):
    """Compare deux compétences sans tenir compte de la casse ni des espaces."""

    rSame = pFirst.strip().lower() == pSecond.strip().lower()

    return rSame


def contains_skill(pSkills, pSkill):
    """Indique si une liste contient une compétence, à la casse près."""

    rContains = any(same_skill(vSkill, pSkill) for vSkill in pSkills)

    return rContains


def match_profile(pProfile, pOfferSkills):
    """Retourne les compétences couvertes, manquantes et le score de correspondance."""

    vCovered = [
        vSkill for vSkill in pOfferSkills if contains_skill(pProfile["skills"], vSkill)
    ]
    vMissing = [vSkill for vSkill in pOfferSkills if vSkill not in vCovered]

    rMatch = {
        "covered": vCovered,
        "missing": vMissing,
        # Sans compétence identifiée dans l'offre, aucun score n'a de sens.
        "score": (
            round(100 * len(vCovered) / len(pOfferSkills)) if pOfferSkills else None
        ),
    }

    return rMatch


def recommend_cv(pProfile, pOfferSkills):
    """Retourne la variante de CV qui couvre le plus de compétences de l'offre."""

    rCv = None
    vBestCount = -1

    for vCv in pProfile["cv_variants"]:
        vCount = sum(contains_skill(vCv["skills"], vSkill) for vSkill in pOfferSkills)

        if vCount > vBestCount:
            rCv = {"name": vCv["name"], "matching": vCount}
            vBestCount = vCount

    return rCv


def find_experiences(pProfile, pSkill):
    """Retourne les expériences du profil qui illustrent une compétence."""

    rExperiences = [
        vExperience
        for vExperience in pProfile["experiences"]
        if contains_skill(vExperience["skills"], pSkill)
    ]

    return rExperiences


def build_questions(pOffer):
    """Retourne les questions à poser, selon ce que l'offre ne précise pas."""

    rQuestions = []

    if not (pOffer.get("salary_net_monthly_min") or pOffer.get("salary_label")):
        rQuestions.append(
            "Quelle est la fourchette de rémunération prévue pour le poste ?"
        )

    if pOffer.get("remote") is None:
        rQuestions.append("Quelle est la politique de télétravail de l'équipe ?")

    if not pOffer.get("contract"):
        rQuestions.append("Quel est le type de contrat proposé ?")
    elif pOffer.get("contract") == "CDD":
        rQuestions.append("Une suite en CDI est-elle envisagée à l'issue du contrat ?")

    rQuestions += GENERAL_QUESTIONS

    return rQuestions


def build_answers(pProfile, pMatch, pOffer):
    """Retourne des pistes de réponse aux questions classiques du recruteur."""

    vCompany = pOffer.get("company") or "l'entreprise"
    vSkills = ", ".join(pMatch["covered"][:LETTER_SKILLS])
    vExperience = next(
        (
            vExperience
            for vSkill in pMatch["covered"]
            for vExperience in find_experiences(pProfile, vSkill)
            if vExperience["achievement"]
        ),
        None,
    )
    vSalary = pOffer.get("salary_label")

    vPitch = [pProfile["headline"] or "Votre métier et votre niveau en une phrase"]

    if pProfile["experiences"]:
        vPitch.append(
            "parcours : "
            + ", ".join(vItem["title"] for vItem in pProfile["experiences"][:3])
        )

    if vSkills:
        vPitch.append(f"compétences utiles ici : {vSkills}")

    rAnswers = [
        {
            "question": "Présentez-vous.",
            "hint": " ; ".join(vPitch)
            + ". Deux minutes au plus, en finissant par ce qui vous amène à ce poste.",
        },
        {
            "question": f"Pourquoi {vCompany} ?",
            "hint": f"Citez l'activité de {vCompany} (bouton « Infos entreprise »), "
            "un élément précis de l'offre qui vous attire, puis le lien avec votre "
            "parcours. Évitez les réponses valables pour n'importe quelle entreprise.",
        },
        {
            "question": "Parlez-moi d'une réussite.",
            "hint": (
                f"Méthode STAR (situation, tâche, action, résultat) à partir de : "
                f"{vExperience['title']}, {lower_first(vExperience['achievement'])}."
                if vExperience
                else "Méthode STAR (situation, tâche, action, résultat) : "
                "ajoutez une réalisation à vos expériences dans le Profil."
            ),
        },
        {
            "question": "Quel est votre point faible ?",
            "hint": (
                f"{pMatch['missing'][0]} : dites ce que vous avez déjà commencé "
                "pour progresser (formation, projet personnel) et ce qui vous en "
                "rapproche."
                if pMatch["missing"]
                else "Un vrai point d'amélioration, suivi de ce que vous faites "
                "pour progresser."
            ),
        },
        {
            "question": "Quelles sont vos prétentions salariales ?",
            "hint": (
                f"L'offre annonce {vSalary} : donnez une fourchette cohérente avec "
                "ce montant, en brut annuel."
                if vSalary
                else "L'offre ne donne pas de salaire : préparez une fourchette en "
                "brut annuel à partir d'offres comparables de la liste."
            ),
        },
    ]

    return rAnswers


def build_interview(pProfile, pMatch, pOffer):
    """Prépare l'entretien : expériences à citer, points à préparer, questions."""

    vStrengths = []

    for vSkill in pMatch["covered"]:
        vExperiences = find_experiences(pProfile, vSkill)

        vStrengths.append(
            {
                "skill": vSkill,
                "examples": [
                    f"{vExperience['title']} : {vExperience['achievement']}".rstrip(
                        " :"
                    )
                    for vExperience in vExperiences
                ],
            }
        )

    rInterview = {
        "strengths": vStrengths,
        # Une compétence manquante se prépare plutôt qu'elle ne se cache.
        "gaps": [
            f"{vSkill} : expliquer comment vous comptez vous y former, ou citer une "
            "compétence proche déjà pratiquée."
            for vSkill in pMatch["missing"]
        ],
        "answers": build_answers(pProfile, pMatch, pOffer),
        "questions": build_questions(pOffer),
    }

    return rInterview


def build_letter(pProfile, pMatch, pOffer):
    """Assemble un brouillon de lettre de motivation à relire et personnaliser."""

    vCompany = pOffer.get("company") or "votre entreprise"
    # « Développeur H/F » devient « Développeur » : la mention n'a pas sa place
    # dans une lettre.
    vTitle = " ".join(GENDER_MARKERS.sub(" ", pOffer.get("title") or "").split())
    vTitle = vTitle or "le poste proposé"
    vSkills = pMatch["covered"][:LETTER_SKILLS]

    vExperience = next(
        (
            vExperience
            for vSkill in vSkills
            for vExperience in find_experiences(pProfile, vSkill)
        ),
        None,
    )

    vParagraphs = [
        "Madame, Monsieur,",
        f"Votre offre « {vTitle} » chez {vCompany} a retenu toute mon attention.",
    ]

    if pProfile["headline"]:
        vParagraphs.append(pProfile["headline"])

    if vSkills:
        vParagraphs.append(
            "Je maîtrise notamment " + ", ".join(vSkills) + ", que vous recherchez."
        )

    if vExperience and vExperience["achievement"]:
        vParagraphs.append(
            f"En tant que {lower_first(vExperience['title'])}, j'ai par exemple "
            f"{lower_first(vExperience['achievement'])}.".replace("..", ".")
        )

    vParagraphs += [
        f"Rejoindre {vCompany} me permettrait de mettre ces compétences au service "
        "de vos projets. Je me tiens à votre disposition pour en échanger lors "
        "d'un entretien.",
        "Je vous prie d'agréer, Madame, Monsieur, mes salutations distinguées.",
    ]

    if pProfile["name"]:
        vParagraphs.append(pProfile["name"])

    rLetter = "\n\n".join(vParagraphs)

    return rLetter


def prepare_application(pProfile, pOffer):
    """Prépare tous les éléments d'une candidature pour une offre."""

    vOfferSkills = get_offer_skills(pOffer)
    vMatch = match_profile(pProfile, vOfferSkills)

    rPreparation = {
        "offer_skills": vOfferSkills,
        "match": vMatch,
        "cv": recommend_cv(pProfile, vOfferSkills),
        "interview": build_interview(pProfile, vMatch, pOffer),
        "letter": build_letter(pProfile, vMatch, pOffer),
    }

    return rPreparation


def score_offers(pOffers, pProfile):
    """Ajoute à chaque offre son score de correspondance avec le profil, ou None.

    Sans profil renseigné, aucun score n'est calculé.
    """

    vEmpty = not pProfile.get("skills")

    for vOffer in pOffers:
        vOffer["match_score"] = (
            None
            if vEmpty
            else match_profile(pProfile, get_offer_skills(vOffer))["score"]
        )


# Filtre de la liste des offres : correspondance minimale avec le profil
MATCH_FILTERS = {
    0: "Toute correspondance",
    30: "Correspondance 30 % et +",
    50: "Correspondance 50 % et +",
    70: "Correspondance 70 % et +",
    90: "Correspondance 90 % et +",
}


def filter_by_match(pOffers, pMinScore):
    """Garde les offres au moins aussi proches du profil que pMinScore.

    Sans compétence dans le profil, aucune offre n'a de score : le filtre est
    alors ignoré plutôt que de vider la liste.
    """

    vScored = any(vOffer.get("match_score") is not None for vOffer in pOffers)

    rOffers = (
        [
            vOffer
            for vOffer in pOffers
            if vOffer.get("match_score") is not None
            and vOffer["match_score"] >= pMinScore
        ]
        if pMinScore and vScored
        else pOffers
    )

    return rOffers
