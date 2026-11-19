"""Préparation d'un entretien sur un projet réel : questions probables et pistes

Les recruteurs techniques font souvent parler d'un projet cité dans le CV. Chaque
question est accompagnée de pistes tirées des faits du README
(job/portfolio_projects.py) et des fichiers à montrer. Une question sans fait
pour y répondre n'est pas proposée : mieux vaut ne pas l'anticiper que
d'inventer une réponse.
"""

from job.portfolio_projects import get_facts

# Rappel affiché avec les questions : les chiffres cités doivent pouvoir être
# montrés dans le dépôt.
NUMBERS_NOTICE = (
    "Ne citez que les chiffres de ces pistes, que le dépôt permet de vérifier ; "
    "pour le reste, décrivez ce que vous avez fait sans l'estimer."
)

# Question, raison pour laquelle le recruteur la pose, thèmes de faits qui y
# répondent et conseil de forme. « summary » et « code_tour » désignent le
# résumé et les fichiers du projet plutôt qu'un thème de faits.
QUESTIONS = (
    (
        "Présentez-moi ce projet en deux minutes.",
        "Vérifier que vous savez expliquer simplement à quoi il sert et pour qui.",
        ("summary",),
        "Commencez par le besoin, puis ce que fait l'outil, puis la technique.",
    ),
    (
        "Pourquoi ces technologies ?",
        "Voir si le choix est réfléchi ou subi.",
        ("stack", "interface"),
        "Reliez chaque technologie à une contrainte du projet.",
    ),
    (
        "Comment le code est-il organisé ?",
        "Juger la séparation des responsabilités et la lisibilité.",
        ("architecture", "code_tour"),
        "Ouvrez le dépôt et montrez un dossier ; l'organisation se voit mieux "
        "qu'elle ne s'explique.",
    ),
    (
        "Comment savez-vous que ça marche ?",
        "Mesurer votre rigueur : tests, intégration continue, contrôles.",
        ("tests",),
        "Donnez un exemple de bug qu'un test a évité ou mis au jour, s'il y en a un.",
    ),
    (
        "Où sont les données, et comment les protégez-vous ?",
        "Tester votre sens de la confidentialité et de la sécurité.",
        ("data",),
        "Expliquez le choix fait et ce qu'il vous a coûté en fonctionnalités.",
    ),
    (
        "Comment le projet arrive-t-il chez l'utilisateur ?",
        "Savoir si vous allez jusqu'au livrable, pas seulement jusqu'au code.",
        ("delivery",),
        "Décrivez le chemin d'une modification, du commit à l'installation.",
    ),
    (
        "Quelle a été la principale difficulté technique ?",
        "Évaluer votre façon de résoudre un problème.",
        ("difficulty",),
        "Suivez la méthode STAR : situation, tâche, action, résultat.",
    ),
    (
        "Qu'est-ce qui vient ensuite ?",
        "Voir si vous avez du recul sur le projet et ses limites.",
        ("next",),
        "Parlez d'une limite actuelle et de la façon dont vous la lèveriez.",
    ),
)


def collect_hints(pProject, pThemes):
    """Retourne les pistes d'une question, tirées des faits du projet."""

    rHints = []

    for vTheme in pThemes:
        if vTheme == "summary":
            rHints.append(pProject["summary"])
        elif vTheme == "stack":
            rHints.append("Technologies : " + ", ".join(pProject["stack"]) + ".")
        elif vTheme == "code_tour":
            rHints.extend(
                f"{vPath} : {vRole}." for vPath, vRole in pProject["code_tour"]
            )
        elif vTheme == "next":
            rHints.extend(pProject["next"])
        else:
            rHints.extend(get_facts(pProject, vTheme))

    return rHints


def build_project_questions(pProject):
    """Retourne les questions probables sur un projet, chacune avec ses pistes.

    Une question dont le projet n'a aucun fait à opposer est écartée.
    """

    rQuestions = []

    for vQuestion, vReason, vThemes, vAdvice in QUESTIONS:
        vHints = collect_hints(pProject, vThemes)

        if vHints:
            rQuestions.append(
                {
                    "question": vQuestion,
                    "reason": vReason,
                    "hints": vHints,
                    "advice": vAdvice,
                }
            )

    return rQuestions


def render_questions_text(pProject, pQuestions):
    """Retourne les questions et leurs pistes en texte brut, pour les relire ailleurs."""

    vLines = [f"Entretien : questions probables sur {pProject['name']}", ""]

    for vIndex, vItem in enumerate(pQuestions, start=1):
        vLines.append(f"{vIndex}. {vItem['question']}")
        vLines.append(f"   Pourquoi : {vItem['reason']}")
        vLines.extend(f"   - {vHint}" for vHint in vItem["hints"])
        vLines.append(f"   Conseil : {vItem['advice']}")
        vLines.append("")

    vLines.append(NUMBERS_NOTICE)

    rText = "\n".join(vLines)

    return rText
