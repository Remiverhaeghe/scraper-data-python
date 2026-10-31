"""Mascotte : un petit robot de maintenance qui salue et commente la progression

Son humeur et sa phrase se choisissent d'après la progression du jour : il
s'endort après trois jours sans activité, sans reproche, se concentre sur les
quêtes en cours et se montre fier d'une réussite. Les phrases sont écrites à
l'avance ; la même s'affiche toute la journée pour une même situation.
"""

import random
from datetime import date

MOODS = ("happy", "focused", "asleep", "proud")
SLEEP_DAYS = 3

# Couleurs propres au dessin, lisibles sur fond clair comme sombre
BODY = "#f59e0b"
BODY_DARK = "#b45309"
FACE = "#1e293b"
EYES = "#7dd3fc"
METAL = "#94a3b8"

EYES_BY_MOOD = {
    "happy": (
        f'<circle cx="46" cy="50" r="7" fill="{EYES}"/>'
        f'<circle cx="74" cy="50" r="7" fill="{EYES}"/>'
    ),
    "focused": (
        f'<rect x="38" y="48" width="16" height="5" rx="2" fill="{EYES}"/>'
        f'<rect x="66" y="48" width="16" height="5" rx="2" fill="{EYES}"/>'
    ),
    "asleep": (
        f'<path d="M39 52 Q46 57 53 52" fill="none" stroke="{EYES}" stroke-width="3" '
        'stroke-linecap="round"/>'
        f'<path d="M67 52 Q74 57 81 52" fill="none" stroke="{EYES}" stroke-width="3" '
        'stroke-linecap="round"/>'
    ),
    "proud": (
        f'<path d="M39 53 Q46 44 53 53" fill="none" stroke="{EYES}" stroke-width="3" '
        'stroke-linecap="round"/>'
        f'<path d="M67 53 Q74 44 81 53" fill="none" stroke="{EYES}" stroke-width="3" '
        'stroke-linecap="round"/>'
    ),
}
MOUTH_BY_MOOD = {
    "happy": f'<path d="M48 64 Q60 72 72 64" fill="none" stroke="{EYES}" '
    'stroke-width="3" stroke-linecap="round"/>',
    "focused": f'<path d="M50 66 H70" stroke="{EYES}" stroke-width="3" '
    'stroke-linecap="round"/>',
    "asleep": f'<circle cx="60" cy="66" r="3" fill="{EYES}"/>',
    "proud": f'<path d="M46 62 Q60 76 74 62 Z" fill="{EYES}"/>',
}
# Voyant de l'antenne : éteint pendant le sommeil
LIGHT_BY_MOOD = {
    "happy": "#4ade80",
    "focused": "#38bdf8",
    "asleep": "#475569",
    "proud": "#facc15",
}
EXTRA_BY_MOOD = {
    "happy": "",
    "focused": (
        # Clé plate tenue levée : le robot est au travail
        f'<path d="M100 84 L110 64" stroke="{METAL}" stroke-width="5" '
        'stroke-linecap="round"/>'
        f'<circle cx="111" cy="61" r="6" fill="none" stroke="{METAL}" stroke-width="4"/>'
    ),
    "asleep": (
        # « z Z » tracés, sans dépendre d'une police
        f'<path d="M86 30 h8 l-8 9 h8" fill="none" stroke="{METAL}" stroke-width="2.5" '
        'stroke-linejoin="round"/>'
        f'<path d="M98 8 h12 l-12 14 h12" fill="none" stroke="{METAL}" stroke-width="3" '
        'stroke-linejoin="round"/>'
    ),
    "proud": (
        '<path d="M60 92 L63 99 L71 99 L65 104 L67 112 L60 107 L53 112 L55 104 '
        'L49 99 L57 99 Z" fill="#facc15" stroke="#a16207" stroke-width="1"/>'
    ),
}

PHRASES = {
    "welcome": (
        "Bonjour ! Je suis Boulon, ton robot de maintenance. On commence par une "
        "quête du jour ?",
    ),
    "asleep": (
        "Zzz… Oh, te revoilà ! Content de te voir. Une petite révision pour se "
        "remettre en route ?",
        "Je faisais une sieste de maintenance. On reprend doucement, une quête à la fois ?",
        "Tout est resté bien rangé pendant ton absence. Prêt pour une remise en marche ?",
    ),
    "level": (
        "Niveau {level} : {title} ! Je fais briller ma clé en ton honneur.",
        "Te voilà {title}, niveau {level}. Beau travail !",
    ),
    "trophy": (
        "Nouveau trophée : « {trophy} ». Je l'accroche dans l'atelier !",
        "« {trophy} » débloqué. Je suis fier de toi.",
    ),
    "quests_done": (
        "Toutes les quêtes du jour sont faites. Le reste, c'est du bonus !",
        "Quêtes du jour bouclées. Pause méritée, ou on continue sur la lancée ?",
    ),
    "quest": (
        "Plus que {left} pour « {quest} ». On s'y met ?",
        "« {quest} » : {left} à faire, et c'est dans la boîte.",
    ),
    "streak": (
        "{streak} jours d'affilée : la machine tourne rond !",
        "Série de {streak} jours. Régulier comme une horloge.",
    ),
    "morning": (
        "Bonjour ! Le café est prêt, les quêtes aussi.",
        "Bon matin ! On démarre par une petite révision ?",
    ),
    "afternoon": (
        "Bon après-midi ! Une quête rapide entre deux candidatures ?",
        "Me revoilà. On avance une quête du jour ?",
    ),
    "evening": (
        "Bonsoir ! Cinq minutes de révision avant de souffler ?",
        "Belle soirée ! Une dernière quête pour la route ?",
    ),
}


def draw_mascot(pMood):
    """Retourne le SVG du robot dans une humeur donnée, carré de 120 de côté."""

    vMood = pMood if pMood in MOODS else "happy"

    rSvg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" '
        f'height="120" role="img"><title>Boulon, robot de maintenance</title>'
        f'<line x1="60" y1="14" x2="60" y2="28" stroke="{METAL}" stroke-width="3"/>'
        f'<circle cx="60" cy="11" r="5" fill="{LIGHT_BY_MOOD[vMood]}"/>'
        f'<rect x="22" y="28" width="76" height="54" rx="14" fill="{BODY}" '
        f'stroke="{BODY_DARK}" stroke-width="3"/>'
        f'<rect x="32" y="37" width="56" height="37" rx="9" fill="{FACE}"/>'
        f'<rect x="14" y="44" width="8" height="18" rx="3" fill="{METAL}"/>'
        f'<rect x="98" y="44" width="8" height="18" rx="3" fill="{METAL}"/>'
        f'<rect x="36" y="84" width="48" height="30" rx="8" fill="{BODY}" '
        f'stroke="{BODY_DARK}" stroke-width="3"/>'
        f'<path d="M36 92 L16 100" stroke="{METAL}" stroke-width="5" '
        'stroke-linecap="round"/>'
        f'<path d="M84 92 L100 84" stroke="{METAL}" stroke-width="5" '
        'stroke-linecap="round"/>'
        f"{EYES_BY_MOOD[vMood]}{MOUTH_BY_MOOD[vMood]}{EXTRA_BY_MOOD[vMood]}</svg>"
    )

    return rSvg


def count_idle_days(pHistory, pToday):
    """Retourne les jours écoulés depuis le dernier jour avec des points, ou None."""

    vActiveDays = [
        date.fromisoformat(vDay["day"]) for vDay in pHistory if vDay.get("xp")
    ]

    rIdle = (pToday - max(vActiveDays)).days if vActiveDays else None

    return rIdle


def find_situation(pProgress, pNow):
    """Retourne (situation, humeur, valeurs des phrases) d'après la progression."""

    vToday = pNow.date()
    vIdle = count_idle_days(pProgress.get("history", []), vToday)
    vDaily = [vQuest for vQuest in pProgress.get("quests", []) if not vQuest["weekly"]]
    vTrophies = [
        vItem["title"]
        for vItem in pProgress.get("achievements", [])
        if vItem.get("unlocked_on") == vToday.isoformat() and not vItem.get("hidden")
    ]

    if vIdle is None and not pProgress.get("xp"):
        return ("welcome", "happy", {})

    if vIdle is not None and vIdle >= SLEEP_DAYS:
        return ("asleep", "asleep", {})

    if pProgress.get("level_before_today", pProgress["level"]) < pProgress["level"]:
        return (
            "level",
            "proud",
            {"level": pProgress["level"], "title": pProgress["title"]},
        )

    if vTrophies:
        return ("trophy", "proud", {"trophy": vTrophies[0]})

    if vDaily and all(vQuest["done"] for vQuest in vDaily):
        return ("quests_done", "proud", {})

    vStarted = sorted(
        (vQuest for vQuest in vDaily if not vQuest["done"] and vQuest["progress"]),
        key=lambda pQuest: pQuest["target"] - pQuest["progress"],
    )

    if vStarted:
        return (
            "quest",
            "focused",
            {
                "quest": vStarted[0]["label"],
                "left": vStarted[0]["target"] - vStarted[0]["progress"],
            },
        )

    if pProgress.get("streak", 0) >= 3:
        return ("streak", "happy", {"streak": pProgress["streak"]})

    vMoment = (
        "morning" if pNow.hour < 12 else "afternoon" if pNow.hour < 18 else "evening"
    )

    rSituation = (vMoment, "happy", {})

    return rSituation


def build_mascot(pProgress, pNow):
    """Retourne l'humeur, la phrase du jour et le dessin de la mascotte."""

    vSituation, vMood, vValues = find_situation(pProgress, pNow)
    # Même phrase toute la journée pour une même situation, sans usage cryptographique.
    vRandom = random.Random(f"{pNow.date().isoformat()}-{vSituation}")  # nosec B311

    rMascot = {
        "mood": vMood,
        "situation": vSituation,
        "text": vRandom.choice(PHRASES[vSituation]).format(**vValues),
        "svg": draw_mascot(vMood),
    }

    return rMascot
