"""Demandes préparées pour ChatGPT, à coller avec son propre compte

Aucune API n'est appelée : l'API d'OpenAI est payante, séparée de l'abonnement
ChatGPT. L'application assemble le texte, l'utilisateur le relit puis le colle.
"""

from job.fingerprint import GENDER_MARKERS
from job.preparation import get_offer_skills, match_profile, recommend_cv

CHATGPT_URL = "https://chatgpt.com/"

# Une description très longue noierait la demande ; le début suffit.
MAX_DESCRIPTION_LENGTH = 4000

PROMPT_KINDS = {
    "interview": "Questions du recruteur",
    "simulation": "Simulation d'entretien",
    "cv": "CV et lettre adaptés",
    "company": "Comprendre l'entreprise",
}


def describe_offer(pOffer):
    """Présente l'offre : poste, entreprise, lieu, contrat et description."""

    vTitle = " ".join(GENDER_MARKERS.sub(" ", pOffer.get("title") or "").split())
    vDescription = (pOffer.get("description") or "").strip()

    if len(vDescription) > MAX_DESCRIPTION_LENGTH:
        vDescription = vDescription[:MAX_DESCRIPTION_LENGTH] + " […]"

    vLines = [
        f"Poste : {vTitle or 'non précisé'}",
        f"Entreprise : {pOffer.get('company') or 'non précisée'}",
    ]

    for vLabel, vKey in (
        ("Lieu", "location"),
        ("Contrat", "contract"),
        ("Salaire", "salary_label"),
        ("Lien", "url"),
    ):
        if pOffer.get(vKey):
            vLines.append(f"{vLabel} : {pOffer[vKey]}")

    if vDescription:
        vLines += ["Description :", vDescription]

    rText = "\n".join(vLines)

    return rText


def describe_profile(pProfile, pOffer):
    """Présente le candidat : présentation, compétences, expériences et CV conseillé."""

    vOfferSkills = get_offer_skills(pOffer)
    vMatch = match_profile(pProfile, vOfferSkills)
    vCv = recommend_cv(pProfile, vOfferSkills)

    vLines = []

    if pProfile.get("headline"):
        vLines.append(f"Présentation : {pProfile['headline']}")

    if pProfile.get("skills"):
        vLines.append(f"Compétences : {', '.join(pProfile['skills'])}")

    for vExperience in pProfile.get("experiences") or []:
        vLines.append(
            "Expérience : "
            + " | ".join(
                vPart
                for vPart in (
                    vExperience["title"],
                    ", ".join(vExperience["skills"]),
                    vExperience["achievement"],
                )
                if vPart
            )
        )

    if vCv:
        vLines.append(f"CV conseillé pour cette offre : {vCv['name']}")

    if vMatch["missing"]:
        vLines.append(
            "Compétences demandées que je n'ai pas indiquées : "
            + ", ".join(vMatch["missing"])
        )

    rText = "\n".join(vLines) or "Profil non renseigné."

    return rText


def build_prompts(pProfile, pOffer, pCompanySummary=None):
    """Retourne les demandes à coller dans ChatGPT, par type."""

    vOffer = describe_offer(pOffer)
    vProfile = describe_profile(pProfile, pOffer)
    vCompany = (
        f"\n\nInformations publiques déjà trouvées : {pCompanySummary}"
        if pCompanySummary
        else ""
    )

    rPrompts = {
        "interview": (
            "Tu es recruteur pour le poste ci-dessous. Prépare-moi à l'entretien :\n"
            "1. Les 10 questions que tu me poserais, techniques et comportementales.\n"
            "2. Pour chacune, ce que tu attends et une piste de réponse tirée de mon "
            "profil.\n"
            "3. Les points faibles de ma candidature que tu creuserais, et comment "
            "les présenter honnêtement.\n"
            "4. Trois questions pertinentes à poser à la fin de l'entretien.\n"
            "Réponds en français.\n\n"
            f"--- Offre ---\n{vOffer}\n\n--- Mon profil ---\n{vProfile}"
        ),
        "simulation": (
            "Simule un entretien d'embauche pour le poste ci-dessous. Tu es le "
            "recruteur :\n"
            "1. Pose-moi une seule question à la fois, puis attends ma réponse.\n"
            "2. Après chaque réponse, note-la sur 5, dis ce qui était bien, ce qui "
            "manquait, et propose une meilleure formulation tirée de mon profil.\n"
            "3. Alterne questions techniques sur les compétences de l'offre et "
            "questions comportementales.\n"
            "4. Après 8 questions, fais un bilan : points forts, points à "
            "travailler, et les notions techniques à réviser.\n"
            "Ne réponds jamais à ma place. Réponds en français.\n\n"
            f"--- Offre ---\n{vOffer}\n\n--- Mon profil ---\n{vProfile}"
        ),
        "cv": (
            "Aide-moi à adapter ma candidature à cette offre, sans rien inventer :\n"
            "1. Le titre et le résumé de CV à mettre en avant.\n"
            "2. Les expériences et réalisations à placer en premier, reformulées "
            "avec les mots-clés de l'offre.\n"
            "3. Les compétences à ajouter ou à mettre en avant, si je les ai.\n"
            "4. Une lettre de motivation courte (moins de 250 mots), ton "
            "professionnel et direct.\n"
            "Signale ce qui manque dans mon profil plutôt que de l'inventer. "
            "Réponds en français.\n\n"
            f"--- Offre ---\n{vOffer}\n\n--- Mon profil ---\n{vProfile}"
        ),
        "company": (
            "Je postule dans l'entreprise ci-dessous. Aide-moi à la connaître avant "
            "l'entretien :\n"
            "1. Ce qu'elle fait : métiers, produits ou services, clients.\n"
            "2. Sa taille, son histoire et ses actualités récentes, en précisant "
            "la date de tes informations.\n"
            "3. Sa culture et son environnement technique, si tu les connais.\n"
            "4. Pourquoi ce poste peut m'intéresser, au vu de mon profil.\n"
            "5. Les points à vérifier par moi-même avant l'entretien.\n"
            "Distingue ce que tu sais de ce que tu supposes. Réponds en français."
            f"{vCompany}\n\n--- Offre ---\n{vOffer}\n\n--- Mon profil ---\n{vProfile}"
        ),
    }

    return rPrompts
