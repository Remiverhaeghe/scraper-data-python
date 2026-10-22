"""Indices qui trahissent la bonne réponse d'un QCM sans connaître le sujet

Trois indices classiques des QCM rédigés à la main ou par ChatGPT : la bonne
réponse est la plus longue, ou la plus courte, et les mauvaises seules portent
un mot absolu (« toujours », « jamais »). Les lots importés sont contrôlés par
job/quiz_generation.py ; le contenu livré, par les tests, avec measure_bias.
"""

import re

# Part au-delà de laquelle un indice rapporte des points dans le contenu livré :
# le hasard donne 25 % avec quatre choix pour la plus longue comme pour la plus
# courte. Plus strict que pour un lot importé, relu à la main.
MAX_LENGTH_SHARE = 0.35

# Part des QCM dont seules les mauvaises réponses portent un mot absolu
MAX_ABSOLUTE_SHARE = 0.20

# En dessous, un thème est trop petit pour qu'une part ait un sens.
MIN_QUESTIONS = 8

ABSOLUTE_WORDS = re.compile(
    r"\b(toujours|jamais|aucun|aucune|seulement|uniquement|tous|toutes|rien"
    r"|obligatoire|impossible|always|never|only|none)\b",
    re.IGNORECASE,
)


def is_longest_answer(pQuestion):
    """Indique si la bonne réponse est strictement plus longue que les autres choix."""

    vLengths = [len(vChoice) for vChoice in pQuestion["choices"]]
    vRight = vLengths.pop(pQuestion["answer"])

    rLongest = all(vRight > vLength for vLength in vLengths)

    return rLongest


def is_shortest_answer(pQuestion):
    """Indique si la bonne réponse est strictement plus courte que les autres choix."""

    vLengths = [len(vChoice) for vChoice in pQuestion["choices"]]
    vRight = vLengths.pop(pQuestion["answer"])

    rShortest = all(vRight < vLength for vLength in vLengths)

    return rShortest


def has_absolute_tell(pQuestion):
    """Indique si seules des mauvaises réponses portent un mot absolu.

    « Toujours », « jamais », « aucun » signalent souvent un piège : les écarter
    suffit alors à éliminer des choix sans connaître le sujet.
    """

    vChoices = [str(vChoice) for vChoice in pQuestion["choices"]]
    vRight = pQuestion["answer"]

    rTell = not ABSOLUTE_WORDS.search(vChoices[vRight]) and any(
        ABSOLUTE_WORDS.search(vChoice)
        for vIndex, vChoice in enumerate(vChoices)
        if vIndex != vRight
    )

    return rTell


def measure_bias(pQuestions):
    """Compte, parmi les QCM, ceux dont la bonne réponse se devine sans le sujet."""

    vQcms = [
        vQuestion
        for vQuestion in pQuestions
        if isinstance(vQuestion.get("choices"), list)
        and isinstance(vQuestion.get("answer"), int)
        and len(vQuestion["choices"]) > 1
    ]

    rBias = {
        "total": len(vQcms),
        "longest": sum(is_longest_answer(vQuestion) for vQuestion in vQcms),
        "shortest": sum(is_shortest_answer(vQuestion) for vQuestion in vQcms),
        "absolute": sum(has_absolute_tell(vQuestion) for vQuestion in vQcms),
    }

    return rBias


def describe_bias(pBias):
    """Retourne les indices trop fréquents, en clair ; vide si le thème est équilibré."""

    vTotal = pBias["total"]
    rProblems = []

    if vTotal >= MIN_QUESTIONS:
        if pBias["longest"] > MAX_LENGTH_SHARE * vTotal:
            rProblems.append(
                f"bonne réponse la plus longue dans {pBias['longest']} QCM sur {vTotal}"
            )

        if pBias["shortest"] > MAX_LENGTH_SHARE * vTotal:
            rProblems.append(
                f"bonne réponse la plus courte dans {pBias['shortest']} QCM sur {vTotal}"
            )

        if pBias["absolute"] > MAX_ABSOLUTE_SHARE * vTotal:
            rProblems.append(
                f"mot absolu (« toujours », « jamais »…) dans les seules mauvaises "
                f"réponses de {pBias['absolute']} QCM sur {vTotal}"
            )

    return rProblems
