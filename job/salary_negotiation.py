"""Jeu de négociation salariale : un recruteur à règles, des montants tirés du marché

Les montants partent du marché de l'offre (médiane et quartiles des offres
proches) et du salaire visé des Paramètres, en brut annuel, la base dont on
parle en entretien. Le recruteur a un budget plafond qu'il ne dit pas : il
réagit à chaque réponse selon des règles fixes, et la confiance baisse face à
une exigence hors budget ou à un ultimatum. Le score final mesure la part de la
marge obtenue, la relation préservée et les avantages négociés.
"""

from datetime import datetime

from job.presentation import format_euros
from job.salary_market import find_market_salary, to_gross_yearly
from job.settings import load_settings
from job.suspicious_offers import load_market_median
from storage.settings_repository import load_json_setting, save_json_setting
from utils.logger import get_logger

logger = get_logger(__name__)

# Partie en cours et parties terminées ; lues aussi par job/progress.py pour l'XP
NEGOTIATION_KEY = "salary_negotiation"
MAX_HISTORY = 50
# Budget plafond du recruteur au-delà du haut du marché, et fourchette sans quartiles
CEILING_MARGIN = 0.05
MEDIAN_SPREAD = 0.1
# Part de l'écart que le recruteur concède selon la contre-proposition
ARGUED_SHARE = 0.6
PLAIN_SHARE = 0.3
FULL_TRUST = 3
BENEFIT = "télétravail, prime ou RTT"


def round_hundred(pValue):
    """Retourne un montant arrondi à la centaine, comme on l'annonce à l'oral."""

    rValue = int(round(pValue, -2))

    return rValue


def build_budget(pDatabaseFile, pOffer):
    """Retourne les montants de la partie, en brut annuel ; lève ValueError sans marché.

    Le marché de l'offre sert d'abord ; à défaut, la médiane de toutes les offres
    salariées, avec une fourchette de 10 % de part et d'autre.
    """

    vSettings = load_settings(pDatabaseFile)
    vMarket = find_market_salary(pDatabaseFile, pOffer) if pOffer else None

    if vMarket is None:
        vMedian = load_market_median(pDatabaseFile)

        if vMedian is None:
            raise ValueError(
                "Pas encore assez d'offres avec un salaire pour fixer les montants."
            )

        vMarket = {
            "median": vMedian,
            "low": vMedian * (1 - MEDIAN_SPREAD),
            "high": vMedian * (1 + MEDIAN_SPREAD),
            "target": vSettings["target_net_salary"] or None,
        }

    vGross = {
        vKey: round_hundred(to_gross_yearly(vMarket[vKey], vSettings))
        for vKey in ("median", "low", "high")
    }
    vTarget = (
        round_hundred(to_gross_yearly(vMarket["target"], vSettings))
        if vMarket.get("target")
        else vGross["median"]
    )

    rBudget = {
        **vGross,
        "target": vTarget,
        "ceiling": round_hundred(vGross["high"] * (1 + CEILING_MARGIN)),
    }

    return rBudget


def describe_choices(pGame):
    """Retourne les réponses possibles au tour en cours : (identifiant, texte)."""

    vTarget = pGame["target"]
    vStep = pGame["step"]

    if vStep == "claim":
        return [
            ("let", "Je préfère que vous me fassiez une proposition."),
            (
                "range",
                f"Entre {format_euros(vTarget)} et "
                f"{format_euros(round_hundred(vTarget * 1.08))} brut annuel, selon le "
                "périmètre du poste.",
            ),
            (
                "high",
                f"{format_euros(round_hundred(pGame['high'] * 1.2))} brut annuel.",
            ),
            (
                "low",
                f"{format_euros(round_hundred(pGame['median'] * 0.9))} brut annuel, "
                "je suis flexible.",
            ),
        ]

    if vStep == "offer":
        return [
            ("accept", "J'accepte votre proposition."),
            (
                "argue",
                f"Pour ce poste, le marché est autour de {format_euros(pGame['median'])} "
                f"et mon expérience colle aux compétences demandées : je visais "
                f"{format_euros(vTarget)}.",
            ),
            ("counter", f"Je souhaiterais plutôt {format_euros(vTarget)}."),
            ("benefits", f"Le salaire peut me convenir si l'on parle de {BENEFIT}."),
            ("ultimatum", f"C'est {format_euros(vTarget)} ou je décline."),
        ]

    rChoices = [("accept", "J'accepte."), ("refuse", "Je préfère décliner.")]

    if not pGame["benefits"]:
        rChoices.insert(1, ("benefits", f"D'accord, si l'on ajoute {BENEFIT}."))

    return rChoices


def say_offer(pAmount):
    """Retourne la proposition du recruteur."""

    rText = f"Nous pouvons vous proposer {format_euros(pAmount)} brut annuel."

    return rText


def play_claim(pGame, pChoice):
    """Joue l'annonce des prétentions ; retourne la réaction du recruteur."""

    vTarget = pGame["target"]
    vCeiling = pGame["ceiling"]

    if pChoice == "let":
        pGame["flags"].append("no_anchor")
        pGame["offer"] = pGame["low"]
        rReply = say_offer(pGame["offer"])
    elif pChoice == "range":
        pGame["flags"].append("anchor")
        pGame["offer"] = min(
            vCeiling, max(pGame["low"], round_hundred(vTarget * 1.04 * 0.95))
        )
        rReply = "C'est noté. " + say_offer(pGame["offer"])
    elif pChoice == "high":
        pGame["flags"].append("too_high")
        pGame["trust"] -= 1
        pGame["offer"] = round_hundred(vCeiling * 0.9)
        rReply = "C'est nettement au-delà de notre budget pour ce poste. " + say_offer(
            pGame["offer"]
        )
    else:
        pGame["flags"].append("too_low")
        pGame["offer"] = round_hundred(pGame["median"] * 0.9)
        rReply = "Ça nous convient tout à fait. " + say_offer(pGame["offer"])

    pGame["step"] = "offer"

    return rReply


def concede(pGame, pShare):
    """Rapproche la proposition de la demande, sans dépasser le plafond."""

    vAsked = min(pGame["target"], pGame["ceiling"])

    if vAsked > pGame["offer"]:
        pGame["offer"] = round_hundred(
            pGame["offer"] + pShare * (vAsked - pGame["offer"])
        )


def play_offer(pGame, pChoice):
    """Joue la réponse à la proposition ; retourne la réaction du recruteur."""

    if pChoice == "accept":
        return finish(pGame, True, "Parfait, je vous envoie la promesse d'embauche.")

    if pChoice == "argue":
        pGame["flags"].append("argued")
        concede(pGame, ARGUED_SHARE)
        rReply = (
            "Vos arguments se tiennent. Je peux aller jusqu'à "
            f"{format_euros(pGame['offer'])}."
        )
    elif pChoice == "counter":
        pGame["flags"].append("unargued")
        concede(pGame, PLAIN_SHARE)
        rReply = f"Je peux faire un effort : {format_euros(pGame['offer'])}."
    elif pChoice == "benefits":
        pGame["benefits"] = True
        rReply = (
            f"Nous pouvons ajouter {BENEFIT}, au même salaire : "
            f"{format_euros(pGame['offer'])}."
        )
    elif pGame["target"] <= pGame["ceiling"]:
        pGame["flags"].append("ultimatum")
        pGame["trust"] -= 1
        pGame["offer"] = pGame["target"]
        rReply = (
            f"Bien… nous acceptons {format_euros(pGame['offer'])}, "
            "mais la discussion a été tendue."
        )
    else:
        pGame["flags"].append("ultimatum")
        pGame["trust"] -= 2

        return finish(pGame, False, "Dans ce cas, restons-en là.")

    pGame["step"] = "last"

    return rReply


def play_last(pGame, pChoice):
    """Joue la réponse à la dernière proposition ; retourne la réaction du recruteur."""

    if pChoice == "benefits":
        pGame["benefits"] = True

        return finish(
            pGame,
            True,
            f"Entendu pour {BENEFIT}. Je vous envoie la promesse d'embauche.",
        )

    if pChoice == "refuse":
        return finish(pGame, False, "Dommage. Je vous souhaite une bonne continuation.")

    rReply = finish(pGame, True, "Parfait, je vous envoie la promesse d'embauche.")

    return rReply


def finish(pGame, pDeal, pReply):
    """Clôt la partie : accord ou non, score et conseils."""

    pGame["step"] = "done"
    pGame["deal"] = pDeal
    pGame["score"] = compute_score(pGame)
    pGame["advice"] = build_advice(pGame)

    return pReply


def compute_score(pGame):
    """Retourne le score sur 100 : salaire obtenu, relation préservée, avantages, ancrage."""

    if not pGame["deal"]:
        # Refuser une offre basse se défend ; refuser le salaire visé, non.
        return 40 if pGame["offer"] < pGame["target"] * 0.95 else 10

    # Obtenir son salaire visé, dans la limite du budget, vaut la note pleine
    vRoom = max(min(pGame["target"], pGame["ceiling"]) - pGame["low"], 1)
    vCaptured = min(max((pGame["offer"] - pGame["low"]) / vRoom, 0), 1)

    rScore = round(
        60 * vCaptured
        + 20 * max(pGame["trust"], 0) / FULL_TRUST
        + (10 if pGame["benefits"] else 0)
        + (10 if "anchor" in pGame["flags"] else 0)
    )

    return rScore


ADVICE = {
    "no_anchor": "Laisser le recruteur annoncer en premier lui donne l'ancrage : "
    "annoncez une fourchette dont le bas est votre salaire visé.",
    "too_high": "Une demande très au-dessus du marché entame la confiance : restez "
    "dans le haut de la fourchette du marché, chiffres à l'appui.",
    "too_low": "Une demande sous la médiane est acceptée sans discussion : "
    "c'est de l'argent laissé sur la table.",
    "unargued": "Une contre-proposition sans argument obtient peu : citez le marché "
    "et ce que vous apportez au poste.",
    "ultimatum": "L'ultimatum braque l'interlocuteur : gardez-le pour une offre "
    "vraiment inacceptable.",
    "anchor": "Annoncer une fourchette ancrée sur votre salaire visé cadre la "
    "discussion : bonne pratique.",
    "argued": "Argumenter avec le marché et vos compétences fait bouger l'offre : "
    "bonne pratique.",
}


def build_advice(pGame):
    """Retourne les conseils tirés des réponses choisies, puis du résultat."""

    rAdvice = [ADVICE[vFlag] for vFlag in pGame["flags"] if vFlag in ADVICE]

    if pGame["deal"] and not pGame["benefits"] and pGame["offer"] < pGame["target"]:
        rAdvice.append(
            "Sous votre salaire visé, demandez au moins une contrepartie : "
            f"{BENEFIT}."
        )

    if pGame["deal"] and pGame["offer"] < pGame["ceiling"] * 0.9:
        rAdvice.append(
            f"Le budget allait jusqu'à {format_euros(pGame['ceiling'])} : "
            "il restait de la marge."
        )

    return rAdvice


def load_negotiation(pDatabaseFile):
    """Retourne la partie en cours et l'historique."""

    vData = load_json_setting(pDatabaseFile, NEGOTIATION_KEY, {}, dict)

    rData = {
        "current": (
            vData.get("current") if isinstance(vData.get("current"), dict) else None
        ),
        "history": (
            vData.get("history") if isinstance(vData.get("history"), list) else []
        ),
    }

    return rData


def start_negotiation(pDatabaseFile, pOffer=None):
    """Commence une partie sur l'offre donnée, ou sur le marché de toutes les offres."""

    vBudget = build_budget(pDatabaseFile, pOffer)
    vData = load_negotiation(pDatabaseFile)
    vData["current"] = {
        **vBudget,
        "title": (
            f"{(pOffer or {}).get('title') or 'Poste'}"
            + (f" chez {pOffer['company']}" if (pOffer or {}).get("company") else "")
        ),
        "source": (pOffer or {}).get("source"),
        "source_id": (pOffer or {}).get("source_id"),
        "step": "claim",
        "offer": None,
        "trust": FULL_TRUST,
        "benefits": False,
        "flags": [],
        "transcript": [
            [
                "recruiter",
                "Avant d'aller plus loin : quelles sont vos prétentions salariales ?",
            ]
        ],
    }
    save_json_setting(pDatabaseFile, NEGOTIATION_KEY, vData)
    logger.info("Négociation commencée : %s", vData["current"]["title"])


def play_negotiation(pDatabaseFile, pChoice, pNow=None):
    """Joue une réponse ; retourne la partie. Lève ValueError hors partie ou hors choix."""

    vData = load_negotiation(pDatabaseFile)
    vGame = vData["current"]

    if vGame is None or vGame["step"] == "done":
        raise ValueError("Aucune négociation en cours : commencez-en une.")

    vChoices = dict(describe_choices(vGame))

    if pChoice not in vChoices:
        raise ValueError("Réponse inconnue.")

    vGame["transcript"].append(["candidate", vChoices[pChoice]])
    vPlay = {"claim": play_claim, "offer": play_offer, "last": play_last}[vGame["step"]]
    vReply = vPlay(vGame, pChoice)
    vGame["transcript"].append(["recruiter", vReply])

    if vGame["step"] == "last":
        vGame["transcript"].append(["recruiter", "C'est notre dernière proposition."])

    if vGame["step"] == "done":
        vData["history"].append(
            {
                "finished_at": (pNow or datetime.now()).isoformat(timespec="seconds"),
                "title": vGame["title"],
                "deal": vGame["deal"],
                "salary": vGame["offer"] if vGame["deal"] else None,
                "target": vGame["target"],
                "score": vGame["score"],
            }
        )
        vData["history"] = vData["history"][-MAX_HISTORY:]
        logger.info("Négociation terminée : score %d", vGame["score"])

    save_json_setting(pDatabaseFile, NEGOTIATION_KEY, vData)

    rGame = {
        **vGame,
        "choices": [] if vGame["step"] == "done" else describe_choices(vGame),
    }

    return rGame


def build_negotiation_view(pDatabaseFile):
    """Retourne la partie en cours avec ses choix, et les meilleurs scores."""

    vData = load_negotiation(pDatabaseFile)
    vGame = vData["current"]

    rView = {
        "game": (
            {
                **vGame,
                "choices": [] if vGame["step"] == "done" else describe_choices(vGame),
            }
            if vGame
            else None
        ),
        "count": len(vData["history"]),
        "best": max((vEntry["score"] for vEntry in vData["history"]), default=None),
    }

    return rView
