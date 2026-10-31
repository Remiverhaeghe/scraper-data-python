"""Tests de recrutement : questions générées, parties chronométrées et scores

Beaucoup d'industriels font passer des tests psychotechniques avant
l'entretien : suites logiques, calcul, raisonnement mécanique, attention,
lecture de plans. Chaque question est tirée d'un modèle avec des valeurs au
hasard : les parties ne se répètent pas. Une graine rend une partie
reproductible, ce qui permet de la corriger après coup.
"""

import random
import string

from job.progress import APTITUDE_XP_PER_RIGHT, XP_RULES
from storage.aptitude_sessions import add_aptitude_session, get_aptitude_sessions

# Catégorie : (libellé, description, icône)
CATEGORIES = {
    "suites": (
        "Suites logiques",
        "Trouver le terme suivant d'une suite de nombres ou de lettres",
        "trending-up",
    ),
    "calcul": (
        "Calcul et proportions",
        "Pourcentages, règle de trois, durées et conversions, sans calculatrice",
        "scale",
    ),
    "mecanique": (
        "Raisonnement mécanique",
        "Engrenages, courroies, leviers, palans et vérins",
        "settings",
    ),
    "attention": (
        "Attention",
        "Repérer une différence ou compter vite et sans erreur",
        "search",
    ),
    "plans": (
        "Lecture de plans",
        "Échelles, cotes et tolérances d'un dessin technique",
        "pencil",
    ),
}

QUESTIONS_PER_SESSION = 10

# Temps d'une partie : environ quinze secondes par question, comme en vrai
SESSION_SECONDS = 150

# Score à partir duquel une catégorie est jugée prête pour un vrai test
READY_SCORE = 80

# Parties prises en compte pour la moyenne récente d'une catégorie
RECENT_SESSIONS = 5

ROTATIONS = ("Sens horaire", "Sens antihoraire")

# Caractères proches qu'un œil pressé confond, pour les tests d'attention
LOOKALIKES = {
    "0": "O",
    "O": "0",
    "1": "I",
    "I": "1",
    "5": "S",
    "S": "5",
    "8": "B",
    "B": "8",
    "2": "Z",
    "Z": "2",
    "6": "G",
    "G": "6",
    "M": "N",
    "N": "M",
    "E": "F",
    "F": "E",
}
CODE_CHARACTERS = "ABEFGHKMNPRSTXZ0125689"


def format_number(pValue):
    """Retourne un nombre à la française : virgule décimale, sans zéro inutile."""

    if float(pValue).is_integer():
        rText = str(int(pValue))
    else:
        rText = f"{pValue:.2f}".rstrip("0").replace(".", ",")

    return rText


def build_question(pRandom, pText, pRight, pWrongs, pExplanation):
    """Retourne une question à 4 choix, la bonne réponse placée au hasard."""

    vWrongs = []

    for vWrong in pWrongs:
        if vWrong != pRight and vWrong not in vWrongs:
            vWrongs.append(vWrong)

    vChoices = vWrongs[:3]
    vAnswer = pRandom.randrange(len(vChoices) + 1)
    vChoices.insert(vAnswer, pRight)

    rQuestion = {
        "question": pText,
        "choices": vChoices,
        "answer": vAnswer,
        "explanation": pExplanation,
    }

    return rQuestion


def build_numeric_question(pRandom, pText, pRight, pWrongs, pExplanation, pUnit=""):
    """Retourne une question dont les choix sont des nombres, unité comprise."""

    vSuffix = f" {pUnit}" if pUnit else ""

    # Écarts de secours si des distracteurs se confondent avec la réponse
    vWrongs = [
        vWrong
        for vWrong in (*pWrongs, pRight + 1, pRight + 2, pRight + 3)
        if vWrong >= 0
    ]

    rQuestion = build_question(
        pRandom,
        pText,
        format_number(pRight) + vSuffix,
        [format_number(vWrong) + vSuffix for vWrong in vWrongs],
        pExplanation,
    )

    return rQuestion


def create_arithmetic_sequence(pRandom):
    """Suite à pas constant."""

    vStep = pRandom.choice((2, 3, 4, 5, 6, 7, 8, 9, 11, 12))
    vStart = pRandom.randint(1, 30)
    vTerms = [vStart + vIndex * vStep for vIndex in range(6)]

    return (
        vTerms[:5],
        vTerms[5],
        [vTerms[5] + 1, vTerms[5] - 1, vTerms[5] + vStep],
        (f"On ajoute {vStep} à chaque terme."),
    )


def create_geometric_sequence(pRandom):
    """Suite où chaque terme est multiplié par le même nombre."""

    vRatio = pRandom.choice((2, 3))
    vStart = pRandom.randint(1, 5)
    vTerms = [vStart * vRatio**vIndex for vIndex in range(6)]
    vGap = vTerms[4] - vTerms[3]

    return (
        vTerms[:5],
        vTerms[5],
        [vTerms[4] + vGap, vTerms[5] - vRatio, vTerms[5] + vTerms[4]],
        (f"Chaque terme est multiplié par {vRatio}."),
    )


def create_alternating_sequence(pRandom):
    """Suite qui alterne deux opérations."""

    vUp = pRandom.randint(3, 9)
    vDown = pRandom.randint(1, vUp - 1)
    vTerms = [pRandom.randint(5, 20)]

    for vIndex in range(6):
        vTerms.append(vTerms[-1] + (vUp if vIndex % 2 == 0 else -vDown))

    vRight = vTerms[6]

    return (
        vTerms[:6],
        vRight,
        [vRight + vUp + vDown, vTerms[5] + vUp - 1, vRight + 2],
        (f"On ajoute {vUp} puis on retire {vDown}, en alternance."),
    )


def create_growing_sequence(pRandom):
    """Suite dont l'écart augmente d'un pas constant."""

    vGap = pRandom.randint(1, 4)
    vGrowth = pRandom.randint(1, 3)
    vTerms = [pRandom.randint(1, 10)]

    for vIndex in range(5):
        vTerms.append(vTerms[-1] + vGap + vIndex * vGrowth)

    vLastGap = vTerms[5] - vTerms[4]

    return (
        vTerms[:5],
        vTerms[5],
        [vTerms[4] + vLastGap - vGrowth, vTerms[5] + vGrowth, vTerms[5] - 1],
        (f"L'écart entre deux termes augmente de {vGrowth} à chaque fois."),
    )


def create_fibonacci_sequence(pRandom):
    """Suite où chaque terme est la somme des deux précédents."""

    vTerms = [pRandom.randint(1, 5), pRandom.randint(2, 7)]

    while len(vTerms) < 7:
        vTerms.append(vTerms[-1] + vTerms[-2])

    return (
        vTerms[:6],
        vTerms[6],
        [vTerms[6] + 1, vTerms[5] * 2, vTerms[6] - vTerms[3]],
        ("Chaque terme est la somme des deux précédents."),
    )


SEQUENCES = (
    create_arithmetic_sequence,
    create_geometric_sequence,
    create_alternating_sequence,
    create_growing_sequence,
    create_fibonacci_sequence,
)


def create_suites_question(pRandom):
    """Question de suite logique : nombres le plus souvent, parfois lettres."""

    if pRandom.random() < 0.25:
        vStep = pRandom.randint(2, 4)
        vStart = pRandom.randint(0, 25 - 5 * vStep)
        vLetters = [
            string.ascii_uppercase[vStart + vIndex * vStep] for vIndex in range(6)
        ]
        vNext = vStart + 5 * vStep

        return build_question(
            pRandom,
            f"Quelle lettre complète la suite : {', '.join(vLetters[:5])}, … ?",
            vLetters[5],
            [
                string.ascii_uppercase[vIndex]
                for vIndex in (vNext - 1, vNext + 1, vNext - 2, vNext - 3)
                if 0 <= vIndex < 26
            ],
            f"On avance de {vStep} lettres dans l'alphabet à chaque fois.",
        )

    vTerms, vRight, vWrongs, vExplanation = pRandom.choice(SEQUENCES)(pRandom)

    rQuestion = build_numeric_question(
        pRandom,
        f"Quel nombre complète la suite : {', '.join(map(str, vTerms))}, … ?",
        vRight,
        vWrongs,
        vExplanation,
    )

    return rQuestion


def create_calcul_question(pRandom):
    """Question de calcul : pourcentage, règle de trois, durée, remise ou conversion."""

    vKind = pRandom.randrange(5)

    if vKind == 0:
        vRate = pRandom.choice((5, 10, 15, 20, 25, 30, 40, 75))
        vBase = pRandom.randrange(40, 820, 20)
        vRight = vRate * vBase // 100

        return build_numeric_question(
            pRandom,
            f"Combien font {vRate} % de {vBase} ?",
            vRight,
            [vRight + 10, vRight * 2, vRight - vRate // 5 - 1],
            f"{vRate} % de {vBase} = {vBase} × {vRate} / 100 = {vRight}.",
        )

    if vKind == 1:
        vPerMinute = pRandom.randint(2, 9)
        vMinutes = pRandom.randint(3, 8)
        vTarget = pRandom.randrange(10, 65, 5)
        vRight = vPerMinute * vTarget

        return build_numeric_question(
            pRandom,
            f"Une machine produit {vPerMinute * vMinutes} pièces en {vMinutes} minutes. "
            f"Combien en {vTarget} minutes ?",
            vRight,
            [
                vRight + vPerMinute,
                vRight - vPerMinute,
                vPerMinute * vMinutes * vTarget // 10,
            ],
            f"Elle produit {vPerMinute} pièces par minute, donc {vPerMinute} × {vTarget} = {vRight}.",
            "pièces",
        )

    if vKind == 2:
        vSeconds = pRandom.choice((6, 10, 12, 15, 20, 30))
        vRight = pRandom.randrange(5, 65, 5)
        vPieces = vRight * 60 // vSeconds

        return build_numeric_question(
            pRandom,
            f"Un lot de {vPieces} pièces à {vSeconds} secondes par pièce dure combien de minutes ?",
            vRight,
            [vRight + 5, vRight * 2, vRight - 5 if vRight > 5 else vRight + 10],
            f"{vPieces} × {vSeconds} s = {vPieces * vSeconds} s, soit {vRight} minutes.",
            "min",
        )

    if vKind == 3:
        vPrice = pRandom.randrange(40, 420, 20)
        vDiscount = pRandom.choice((10, 20, 25, 50))
        vRight = vPrice - vPrice * vDiscount // 100

        return build_numeric_question(
            pRandom,
            f"Un article coûte {vPrice} €. Que coûte-t-il après une remise de {vDiscount} % ?",
            vRight,
            [vPrice - vDiscount, vRight - 10, vPrice * vDiscount // 100],
            f"La remise vaut {vPrice * vDiscount // 100} € : {vPrice} − {vPrice * vDiscount // 100} = {vRight} €.",
            "€",
        )

    vMeters = pRandom.choice((0.25, 0.4, 0.75, 1.2, 1.5, 2.05, 3.5))
    vRight = round(vMeters * 1000)

    return build_numeric_question(
        pRandom,
        f"Combien de millimètres y a-t-il dans {format_number(vMeters)} m ?",
        vRight,
        [vRight // 10, vRight * 10, vRight + 100],
        f"1 m = 1 000 mm, donc {format_number(vMeters)} m = {vRight} mm.",
        "mm",
    )


def create_mecanique_question(pRandom):
    """Question de raisonnement mécanique, sur les montages courants en atelier."""

    vKind = pRandom.randrange(6)

    if vKind == 0:
        vCount = pRandom.randint(3, 7)
        vFirst = pRandom.randrange(2)
        vRight = ROTATIONS[(vFirst + vCount - 1) % 2]
        vSame = "comme le" if vCount % 2 else "à l'inverse du"

        return build_question(
            pRandom,
            f"{vCount} engrenages sont alignés, chacun en prise avec le suivant. "
            f"Le premier tourne en {ROTATIONS[vFirst].lower()}. Dans quel sens tourne le dernier ?",
            vRight,
            [ROTATIONS[(vFirst + vCount) % 2], "Il reste immobile", "Il oscille"],
            "Deux engrenages en prise tournent en sens inverse : le sens change à chaque roue. "
            f"Avec {vCount} roues, le dernier tourne {vSame} premier.",
        )

    if vKind == 1:
        vDriver = pRandom.choice((10, 12, 15, 20, 24))
        vRatio = pRandom.choice((2, 3, 4))
        vSpeed = pRandom.choice((300, 600, 900, 1200, 1500))
        vRight = vSpeed // vRatio

        return build_numeric_question(
            pRandom,
            f"Un pignon de {vDriver} dents tournant à {vSpeed} tr/min entraîne une roue de "
            f"{vDriver * vRatio} dents. À quelle vitesse tourne la roue ?",
            vRight,
            [vSpeed * vRatio, vSpeed, vRight + vSpeed // 10],
            f"Le rapport est de {vDriver} / {vDriver * vRatio} = 1/{vRatio} : la grande roue tourne "
            f"{vRatio} fois moins vite, {vRight} tr/min, avec un couple {vRatio} fois plus grand.",
            "tr/min",
        )

    if vKind == 2:
        vCrossed = pRandom.random() < 0.5

        return build_question(
            pRandom,
            f"Deux poulies sont reliées par une courroie {'croisée' if vCrossed else 'droite'}. "
            "La poulie menante tourne en sens horaire. Dans quel sens tourne la menée ?",
            ROTATIONS[1] if vCrossed else ROTATIONS[0],
            [
                ROTATIONS[0] if vCrossed else ROTATIONS[1],
                "Elle reste immobile",
                "Cela dépend des diamètres",
            ],
            "Une courroie droite garde le sens de rotation ; une courroie croisée l'inverse. "
            "Les diamètres changent la vitesse, pas le sens.",
        )

    if vKind == 3:
        vEffortArm = pRandom.choice((2, 3, 4, 6))
        vEffort = pRandom.randrange(10, 65, 5)
        vLoad = vEffort * vEffortArm

        return build_numeric_question(
            pRandom,
            f"Une charge de {vLoad} kg est placée à 1 m de l'appui d'un levier. "
            f"Quelle force faut-il appliquer à {vEffortArm} m de l'appui pour l'équilibrer ?",
            vEffort,
            [vLoad, vLoad // 2, vEffort + vEffortArm * 5],
            f"Équilibre des moments : {vLoad} × 1 = F × {vEffortArm}, donc F = {vEffort} kg.",
            "kg",
        )

    if vKind == 4:
        vStrands = pRandom.choice((2, 3, 4, 6))
        vEffort = pRandom.randrange(10, 85, 5)
        vLoad = vEffort * vStrands

        return build_numeric_question(
            pRandom,
            f"Un palan soulève {vLoad} kg avec {vStrands} brins porteurs. "
            "Quel effort faut-il exercer, frottements négligés ?",
            vEffort,
            [vLoad, vLoad // 2 if vStrands != 2 else vLoad // 4, vEffort * 2],
            f"La charge se répartit sur les {vStrands} brins : {vLoad} / {vStrands} = {vEffort} kg. "
            f"En contrepartie, il faut tirer {vStrands} fois plus de câble.",
            "kg",
        )

    vPressure = pRandom.choice((50, 100, 150, 200))
    vSection = pRandom.choice((10, 20, 25, 40, 50))
    vRight = vPressure * vSection / 100

    return build_numeric_question(
        pRandom,
        f"Un vérin de {vSection} cm² de section est alimenté sous {vPressure} bar. "
        "Quelle force développe-t-il ?",
        vRight,
        [vRight * 10, vRight / 10, vPressure * vSection / 1000 + 1],
        f"1 bar = 10 N/cm² : {vPressure} × 10 × {vSection} = {format_number(vRight * 1000)} N, "
        f"soit {format_number(vRight)} kN.",
        "kN",
    )


def create_code(pRandom, pLength):
    """Retourne une référence au hasard, avec un tiret au milieu."""

    vCharacters = [pRandom.choice(CODE_CHARACTERS) for _ in range(pLength)]

    rCode = (
        "".join(vCharacters[: pLength // 2])
        + "-"
        + "".join(vCharacters[pLength // 2 :])
    )

    return rCode


def alter_code(pRandom, pCode, pChanges):
    """Retourne la référence avec pChanges caractères remplacés par un sosie."""

    vCharacters = list(pCode)
    vPositions = [
        vIndex
        for vIndex, vCharacter in enumerate(vCharacters)
        if vCharacter in LOOKALIKES
    ]

    for vIndex in pRandom.sample(vPositions, min(pChanges, len(vPositions))):
        vCharacters[vIndex] = LOOKALIKES[vCharacters[vIndex]]

    rCode = "".join(vCharacters)

    return rCode


def create_attention_question(pRandom):
    """Question d'attention : différences entre références, intrus ou comptage."""

    vKind = pRandom.randrange(3)

    if vKind == 0:
        vCode = create_code(pRandom, 10)
        vChanges = pRandom.randint(0, 3)
        vCopy = alter_code(pRandom, vCode, vChanges)
        vRight = sum(vLeft != vRight for vLeft, vRight in zip(vCode, vCopy))

        return build_question(
            pRandom,
            f"Combien de caractères diffèrent entre {vCode} et {vCopy} ?",
            str(vRight),
            [str(vValue) for vValue in range(4) if vValue != vRight],
            "Comparez caractère par caractère : 0 et O, 1 et I, 5 et S, 8 et B se confondent "
            "facilement, comme sur une référence de pièce à commander.",
        )

    if vKind == 1:
        vCode = create_code(pRandom, 8)
        vOdd = alter_code(pRandom, vCode, 1)

        while vOdd == vCode:
            vCode = create_code(pRandom, 8)
            vOdd = alter_code(pRandom, vCode, 1)

        # Trois choix identiques : build_question les dédoublonnerait.
        vAnswer = pRandom.randrange(4)
        vChoices = [vCode] * 3
        vChoices.insert(vAnswer, vOdd)

        return {
            "question": "Laquelle de ces références est différente des trois autres ?",
            "choices": vChoices,
            "answer": vAnswer,
            "explanation": "Trois références sont identiques ; l'intruse a un caractère "
            "remplacé par son sosie.",
        }

    vTarget = pRandom.choice("bdpq")
    vText = "".join(pRandom.choice("bdpq") for _ in range(24))
    vRight = vText.count(vTarget)

    return build_numeric_question(
        pRandom,
        f"Combien de fois la lettre « {vTarget} » apparaît-elle dans : {' '.join(vText)} ?",
        vRight,
        [vRight + 1, vRight - 1, vRight + 2],
        "b, d, p et q sont des lettres miroirs : on les compte une à une, sans relire deux fois.",
    )


def create_plans_question(pRandom):
    """Question de lecture de plan : échelle, cote manquante ou tolérance."""

    vKind = pRandom.randrange(4)

    if vKind == 0:
        vScale = pRandom.choice((10, 20, 50, 100, 200))
        vLength = pRandom.randint(2, 12)
        vRight = vLength * vScale / 100

        return build_numeric_question(
            pRandom,
            f"Sur un plan à l'échelle 1:{vScale}, un mur mesure {vLength} cm. "
            "Quelle est sa longueur réelle ?",
            vRight,
            [vRight * 10, vRight / 10, vLength * vScale / 1000 + vLength / 10],
            f"1 cm sur le plan vaut {vScale} cm en réalité : {vLength} × {vScale} = "
            f"{vLength * vScale} cm, soit {format_number(vRight)} m.",
            "m",
        )

    if vKind == 1:
        vParts = [pRandom.randrange(15, 120, 5) for _ in range(3)]
        vTotal = sum(vParts)
        vMissing = pRandom.randrange(3)
        vShown = ", ".join(
            "?" if vIndex == vMissing else str(vPart)
            for vIndex, vPart in enumerate(vParts)
        )
        vRight = vParts[vMissing]

        return build_numeric_question(
            pRandom,
            f"Une pièce de {vTotal} mm de long est cotée en trois tronçons : {vShown} mm. "
            "Que vaut la cote manquante ?",
            vRight,
            [vRight + 5, vRight - 5, vTotal - vRight],
            f"Les tronçons font ensemble la cote totale : {vTotal} − la somme des deux autres = {vRight} mm.",
            "mm",
        )

    vNominal = pRandom.choice((12, 16, 20, 25, 30, 40, 50))
    vTolerance = pRandom.choice((0.05, 0.1, 0.2))

    if vKind == 2:
        vRight = vNominal + vTolerance

        return build_numeric_question(
            pRandom,
            f"Quelle est la cote maximale admise pour Ø{vNominal} ±{format_number(vTolerance)} ?",
            vRight,
            [vNominal - vTolerance, vNominal + 2 * vTolerance, vNominal],
            f"La cote maximale est la cote nominale plus l'écart supérieur : "
            f"{vNominal} + {format_number(vTolerance)} = {format_number(vRight)} mm.",
            "mm",
        )

    vOffset = pRandom.choice((-2, -1, 0, 1, 2)) * vTolerance * 0.75
    vMeasure = round(vNominal + vOffset, 3)

    if abs(vOffset) <= vTolerance:
        vRight = "Conforme"
    elif vOffset > 0:
        vRight = "Non conforme, trop grande"
    else:
        vRight = "Non conforme, trop petite"

    return build_question(
        pRandom,
        f"Une cote Ø{vNominal} ±{format_number(vTolerance)} est mesurée à "
        f"{format_number(vMeasure)} mm. La pièce est-elle conforme ?",
        vRight,
        [
            "Conforme",
            "Non conforme, trop grande",
            "Non conforme, trop petite",
            "On ne peut pas savoir",
        ],
        f"L'intervalle admis va de {format_number(vNominal - vTolerance)} à "
        f"{format_number(vNominal + vTolerance)} mm.",
    )


GENERATORS = {
    "suites": create_suites_question,
    "calcul": create_calcul_question,
    "mecanique": create_mecanique_question,
    "attention": create_attention_question,
    "plans": create_plans_question,
}


def generate_session(pCategory, pSeed):
    """Retourne les questions d'une partie ; la même graine donne la même partie."""

    if pCategory not in GENERATORS:
        raise ValueError(f"Catégorie inconnue : {pCategory}")

    # Tirage reproductible des questions, sans usage cryptographique.
    vRandom = random.Random(f"{pCategory}-{pSeed}")  # nosec B311

    rQuestions = [
        {"category": pCategory, **GENERATORS[pCategory](vRandom)}
        for _ in range(QUESTIONS_PER_SESSION)
    ]

    return rQuestions


def grade_session(pQuestions, pAnswers):
    """Retourne le nombre de bonnes réponses ; une question sans réponse est fausse."""

    rCorrect = sum(
        vAnswer == vQuestion["answer"]
        for vQuestion, vAnswer in zip(pQuestions, pAnswers)
    )

    return rCorrect


def get_score(pCorrect, pTotal):
    """Retourne le score en pourcentage, arrondi."""

    rScore = round(100 * pCorrect / pTotal) if pTotal else 0

    return rScore


def finish_session(pDatabaseFile, pCategory, pSeed, pAnswers, pDurationSeconds, pNow):
    """Corrige une partie à partir de sa graine, l'enregistre et retourne le résultat."""

    vQuestions = generate_session(pCategory, pSeed)
    vCorrect = grade_session(vQuestions, pAnswers)
    vDuration = min(max(int(pDurationSeconds), 0), SESSION_SECONDS)

    add_aptitude_session(
        pDatabaseFile, pCategory, vCorrect, len(vQuestions), vDuration, pNow
    )

    rResult = {
        "category": pCategory,
        "label": CATEGORIES[pCategory][0],
        "correct": vCorrect,
        "total": len(vQuestions),
        "score": get_score(vCorrect, len(vQuestions)),
        "duration": vDuration,
        "xp": get_session_xp(vCorrect),
        "questions": [
            {**vQuestion, "given": vAnswer}
            for vQuestion, vAnswer in zip(vQuestions, pAnswers)
        ],
    }

    return rResult


def get_session_xp(pCorrect):
    """Retourne les points d'une partie : un forfait plus un bonus par bonne réponse."""

    rXp = XP_RULES["aptitude"][1] + APTITUDE_XP_PER_RIGHT * pCorrect

    return rXp


def build_aptitude_overview(pDatabaseFile):
    """Retourne, par catégorie, le nombre de parties, le meilleur et le dernier score."""

    vSessions = get_aptitude_sessions(pDatabaseFile)
    vRows = []

    for vCategory, (vLabel, vDescription, vIcon) in CATEGORIES.items():
        vScores = [
            get_score(vSession["correct"], vSession["total"])
            for vSession in vSessions
            if vSession["category"] == vCategory
        ]
        vRecent = vScores[-RECENT_SESSIONS:]
        vAverage = round(sum(vRecent) / len(vRecent)) if vRecent else None

        vRows.append(
            {
                "category": vCategory,
                "label": vLabel,
                "description": vDescription,
                "icon": vIcon,
                "sessions": len(vScores),
                "best": max(vScores, default=None),
                "last": vScores[-1] if vScores else None,
                "average": vAverage,
                "ready": vAverage is not None and vAverage >= READY_SCORE,
            }
        )

    vPlayed = [vRow for vRow in vRows if vRow["average"] is not None]

    rOverview = {
        "rows": vRows,
        "sessions": len(vSessions),
        "ready": sum(vRow["ready"] for vRow in vRows),
        "weakest": (
            min(vPlayed, key=lambda pRow: pRow["average"])["label"] if vPlayed else None
        ),
        "perfect": sum(
            vSession["correct"] == vSession["total"] for vSession in vSessions
        ),
    }

    return rOverview
