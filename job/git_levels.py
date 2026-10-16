"""Niveaux du bac à sable Git : objectif à atteindre et progression

Un niveau part du dépôt obtenu par ses commandes de mise en place ; son objectif
est le dépôt obtenu en jouant ensuite la solution de référence. Deux dépôts sont
comparés par leur forme, pas par les identifiants des nouveaux commits : un
autre chemin qui aboutit au même graphe réussit aussi le niveau.
"""

from dataclasses import dataclass

from job.git_graph import render_graph
from job.git_sandbox import MAX_HISTORY, replay, run_command
from storage.git_levels import get_git_level_results, save_git_level_result


@dataclass(frozen=True)
class GitLevel:
    """Niveau : présentation, mise en place, solution de référence et indice."""

    id: str
    title: str
    series: str
    intro: str
    setup: tuple
    solution: tuple
    hint: str


LEVELS = (
    GitLevel(
        "premiers-commits",
        "Enregistrer son travail",
        "Bases",
        "Un **commit** est un instantané du projet. Chaque commit pointe vers son "
        "parent : l'historique est une chaîne d'instantanés.\n\n"
        "La branche `main` est une simple étiquette posée sur le dernier commit ; "
        "elle avance d'elle-même à chaque `git commit`.\n\n"
        "Objectif : enregistrer deux commits.",
        (),
        ("git commit", "git commit"),
        "git commit, deux fois.",
    ),
    GitLevel(
        "nouvelle-branche",
        "Travailler à côté",
        "Bases",
        "Créer une **branche** ne copie rien : on pose une nouvelle étiquette sur "
        "le commit courant. L'étoile indique la branche où se trouve **HEAD**, "
        "celle qui avancera au prochain commit.\n\n"
        "Objectif : créer la branche `essai`, s'y placer et y enregistrer un commit.",
        ("git commit",),
        ("git switch -c essai", "git commit"),
        "git switch -c crée la branche et s'y place en une seule commande.",
    ),
    GitLevel(
        "fusion",
        "Réunir deux branches",
        "Bases",
        "Quand deux branches ont avancé chacune de leur côté, `git merge` crée un "
        "**commit de fusion** à deux parents, qui réunit les deux historiques.\n\n"
        "Objectif : intégrer `correctif` dans `main`.",
        ("git switch -c correctif", "git commit", "git switch main", "git commit"),
        ("git merge correctif",),
        "Depuis main, git merge correctif.",
    ),
    GitLevel(
        "avance-rapide",
        "Avance rapide",
        "Bases",
        "Si `main` n'a pas bougé depuis la création d'une branche, la fusionner ne "
        "crée aucun commit : l'étiquette `main` avance simplement jusqu'au bout de "
        "la branche. C'est l'**avance rapide** (fast-forward).\n\n"
        "Objectif : amener `main` sur le dernier commit d'`evolution`.",
        (
            "git switch -c evolution",
            "git commit",
            "git commit",
            "git switch main",
        ),
        ("git merge evolution",),
        "Une fusion suffit : observez qu'aucun commit n'est créé.",
    ),
    GitLevel(
        "tete-detachee",
        "Détacher HEAD",
        "Se déplacer",
        "**HEAD** désigne l'endroit où l'on travaille, en général une branche. On "
        "peut aussi le placer directement sur un commit pour l'examiner : HEAD est "
        "alors **détaché**, aucune branche ne le suit.\n\n"
        "Objectif : placer HEAD sur le commit C1.",
        ("git commit", "git commit", "git commit"),
        ("git checkout C1",),
        "git checkout accepte un identifiant de commit.",
    ),
    GitLevel(
        "references-relatives",
        "Remonter l'historique",
        "Se déplacer",
        "Inutile de connaître les identifiants : `HEAD^` désigne le parent de "
        "HEAD, `main~3` le commit situé trois parents avant `main`.\n\n"
        "Objectif : créer la branche `version-1` sur C1 sans écrire C1, puis "
        "placer HEAD sur le parent du commit courant.",
        ("git commit", "git commit", "git commit", "git commit"),
        ("git branch version-1 main~3", "git checkout HEAD^"),
        "git branch accepte une référence de départ ; git checkout HEAD^ remonte d'un "
        "commit.",
    ),
    GitLevel(
        "deplacer-branche",
        "Déplacer une étiquette",
        "Se déplacer",
        "Une branche n'est qu'une étiquette : `git branch -f` la repose sur "
        "n'importe quel commit. Un commit qu'aucune étiquette ne désigne plus "
        "apparaît estompé : il n'est plus visible dans l'historique.\n\n"
        "Objectif : reposer `analyse` sur C1.",
        (
            "git commit",
            "git commit",
            "git switch -c analyse",
            "git commit",
            "git switch main",
        ),
        ("git branch -f analyse C1",),
        "git branch -f <nom> <réf>, depuis une autre branche que celle déplacée.",
    ),
    GitLevel(
        "corriger-commit",
        "Corriger le dernier commit",
        "Réécrire",
        "Un oubli dans le dernier commit ? `git commit --amend` le **remplace** par "
        "une version corrigée, notée avec une apostrophe. L'ancien commit n'est "
        "plus désigné par aucune branche.\n\n"
        "Objectif : remplacer le dernier commit de `main`.",
        ("git commit", "git commit"),
        ("git commit --amend",),
        "git commit --amend.",
    ),
    GitLevel(
        "reset",
        "Revenir en arrière en local",
        "Réécrire",
        "`git reset` ramène la branche courante sur un commit plus ancien : les "
        "commits suivants disparaissent de la branche. À réserver à un travail "
        "qui n'a pas encore été partagé.\n\n"
        "Objectif : ramener `main` deux commits en arrière.",
        ("git commit", "git commit", "git commit"),
        ("git reset HEAD~2",),
        "Une référence relative évite de chercher l'identifiant : HEAD~2.",
    ),
    GitLevel(
        "revert",
        "Annuler un commit partagé",
        "Réécrire",
        "Un commit déjà envoyé à l'équipe ne doit pas disparaître de l'historique. "
        "`git revert` ajoute un **nouveau commit** qui en annule l'effet : "
        "l'historique ne fait qu'avancer.\n\n"
        "Objectif : annuler C1 sans réécrire l'historique de `main`.",
        ("git commit", "git commit"),
        ("git revert C1",),
        "git revert prend le commit à annuler, pas celui où l'on veut revenir.",
    ),
    GitLevel(
        "cherry-pick",
        "Choisir ses commits",
        "Réécrire",
        "`git cherry-pick` recopie des commits précis sur HEAD, dans l'ordre "
        "donné. Les copies portent l'identifiant de l'original suivi d'une "
        "apostrophe.\n\n"
        "Objectif : reprendre sur `main` les commits C1 et C3 de `brouillon`, sans C2.",
        (
            "git switch -c brouillon",
            "git commit",
            "git commit",
            "git commit",
            "git switch main",
        ),
        ("git cherry-pick C1 C3",),
        "Une seule commande accepte plusieurs commits.",
    ),
    GitLevel(
        "second-parent",
        "Le second parent d'une fusion",
        "Se déplacer",
        "Un commit de fusion a deux parents. `^` suit le premier, celui de la "
        "branche où l'on a fusionné ; `^2` suit le second, celui de la branche "
        "intégrée.\n\n"
        "Objectif : créer la branche `retour` sur le second parent de la fusion, "
        "sans écrire d'identifiant.",
        (
            "git switch -c correctif",
            "git commit",
            "git switch main",
            "git commit",
            "git merge correctif",
        ),
        ("git branch retour main^2",),
        "main^2 désigne le second parent du dernier commit de main.",
    ),
    GitLevel(
        "rebase",
        "Rejouer ses commits",
        "Intégrer",
        "`git rebase main` rejoue les commits de la branche courante au bout de "
        "`main`, comme s'ils avaient été écrits après. L'historique devient "
        "linéaire, et `main` peut ensuite avancer par avance rapide.\n\n"
        "Objectif : historique linéaire, `ecran` rejouée sur `main`, puis `main` "
        "amenée au bout de `ecran`, HEAD sur `main`.",
        ("git switch -c ecran", "git commit", "git switch main", "git commit"),
        ("git switch ecran", "git rebase main", "git switch main", "git merge ecran"),
        "Rebase depuis ecran, puis retour sur main et fusion.",
    ),
    GitLevel(
        "grand-menage",
        "Linéariser l'historique",
        "Intégrer",
        "Deux branches partent de `main`, qui a lui-même avancé. On veut un "
        "historique sur une seule ligne : `ihm` rejouée sur `main`, puis `api` "
        "rejouée sur `ihm`, et enfin `main` amenée au bout.\n\n"
        "Objectif : `main`, `ihm` et `api` alignées sur une seule ligne, dans cet "
        "ordre, HEAD sur `main`.",
        (
            "git switch -c ihm",
            "git commit",
            "git switch main",
            "git switch -c api",
            "git commit",
            "git commit",
            "git switch main",
            "git commit",
        ),
        (
            "git switch ihm",
            "git rebase main",
            "git switch api",
            "git rebase ihm",
            "git switch main",
            "git merge api",
        ),
        "Chaque branche se rejoue sur la précédente ; la fusion finale est une "
        "avance rapide.",
    ),
    GitLevel(
        "push",
        "Partager son travail",
        "Travailler à plusieurs",
        "Le dépôt a été cloné depuis le serveur **origin**. L'étiquette "
        "`origin/main` indique où se trouvait `main` sur le serveur lors du "
        "dernier échange : elle ne bouge pas toute seule.\n\n"
        "`git push` envoie la branche courante au serveur ; `origin/main` la "
        "suit.\n\n"
        "Objectif : envoyer le nouveau commit de `main` au serveur.",
        ("git commit", "@clone", "git commit"),
        ("git push",),
        "Une seule commande, depuis main.",
    ),
    GitLevel(
        "fetch",
        "Voir le travail de l'équipe",
        "Travailler à plusieurs",
        "Un collègue a envoyé deux commits sur le serveur. Votre dépôt ne le sait "
        "pas encore : `git fetch` les récupère et avance `origin/main`, sans "
        "toucher à vos branches.\n\n"
        "Objectif : récupérer les commits du serveur, `main` restant en place.",
        ("git commit", "@clone", "@equipe main 2"),
        ("git fetch",),
        "fetch ne modifie que les étiquettes origin/….",
    ),
    GitLevel(
        "pull",
        "Se mettre à jour",
        "Travailler à plusieurs",
        "`git pull` enchaîne `git fetch` et la fusion de `origin/main` dans "
        "`main`. Sans travail local, la fusion est une avance rapide.\n\n"
        "Objectif : amener `main` au niveau du serveur.",
        ("git commit", "@clone", "@equipe main"),
        ("git pull",),
        "git pull fait le fetch et la fusion en une fois.",
    ),
    GitLevel(
        "push-refuse",
        "Envoi refusé",
        "Travailler à plusieurs",
        "Vous avez un commit local, et un collègue en a envoyé un autre entre-"
        "temps : le serveur refuse votre envoi, il perdrait son commit. Essayez "
        "`git push` pour voir.\n\n"
        "`git pull --rebase` récupère son commit et rejoue le vôtre par-dessus : "
        "l'historique reste linéaire et l'envoi passe.\n\n"
        "Objectif : votre commit rejoué après celui du collègue, sur le serveur.",
        ("git commit", "@clone", "git commit", "@equipe main"),
        ("git pull --rebase", "git push"),
        "Rejouer d'abord votre commit sur origin/main, puis envoyer.",
    ),
    GitLevel(
        "branche-distante",
        "Publier une branche",
        "Travailler à plusieurs",
        "Une branche créée localement n'existe pas sur le serveur tant qu'on ne "
        "l'y envoie pas : `git push origin <branche>` la crée là-bas, avec son "
        "étiquette `origin/<branche>`.\n\n"
        "Objectif : créer la branche `revue` avec un commit, puis la publier.",
        ("git commit", "@clone"),
        ("git switch -c revue", "git commit", "git push origin revue"),
        "Trois commandes : créer et se placer, valider, envoyer.",
    ),
)


def get_level(pLevelId):
    """Retourne le niveau demandé, ou None s'il n'existe pas."""

    rLevel = next((vLevel for vLevel in LEVELS if vLevel.id == pLevelId), None)

    return rLevel


def build_signatures(pRepository, pBaseCommits):
    """Retourne la forme de chaque commit, indépendante des nouveaux identifiants.

    Un commit de la mise en place garde son identifiant ; un nouveau commit est
    décrit par sa nature, son original s'il en est une copie, et ses parents.
    """

    rSignatures = {}

    for vCommit, vData in pRepository.commits.items():
        if vCommit in pBaseCommits:
            rSignatures[vCommit] = vCommit
        else:
            rSignatures[vCommit] = (
                vData.kind,
                rSignatures.get(vData.origin, ""),
                tuple(rSignatures[vParent] for vParent in vData.parents),
            )

    return rSignatures


def sign_references(pReferences, pSignatures):
    """Retourne la forme du commit désigné par chaque étiquette."""

    rSigned = {vName: pSignatures[vCommit] for vName, vCommit in pReferences.items()}

    return rSigned


def describe(pRepository, pBaseCommits):
    """Retourne ce qui définit l'état d'un dépôt : branches, serveur et HEAD."""

    vSignatures = build_signatures(pRepository, pBaseCommits)

    rState = (
        sign_references(pRepository.branches, vSignatures),
        sign_references(pRepository.remote, vSignatures),
        sign_references(pRepository.tracking, vSignatures),
        (
            ("détaché", vSignatures[pRepository.head])
            if pRepository.detached
            else ("branche", pRepository.head)
        ),
    )

    return rState


def is_goal_reached(pLevel, pRepository):
    """Indique si le dépôt a la même forme que l'objectif du niveau."""

    vBaseCommits = set(replay(pLevel.setup).commits)

    rReached = describe(pRepository, vBaseCommits) == describe(
        replay(pLevel.setup + pLevel.solution), vBaseCommits
    )

    return rReached


def build_level_list(pDatabaseFile):
    """Retourne les niveaux à afficher, avec leur meilleur résultat."""

    vResults = get_git_level_results(pDatabaseFile)

    rLevels = [
        {
            "id": vLevel.id,
            "title": vLevel.title,
            "series": vLevel.series,
            "par": len(vLevel.solution),
            "best": vResults.get(vLevel.id),
        }
        for vLevel in LEVELS
    ]

    return rLevels


def require_level(pLevelId):
    """Retourne le niveau demandé ; lève ValueError s'il n'existe pas."""

    rLevel = get_level(pLevelId)

    if rLevel is None:
        raise ValueError("Niveau inconnu.")

    return rLevel


def replay_level(pLevel, pHistory):
    """Retourne le dépôt du niveau après les commandes déjà saisies."""

    if len(pHistory) > MAX_HISTORY:
        raise ValueError(f"Plus de {MAX_HISTORY} commandes : recommencez le niveau.")

    rRepository = replay(pLevel.setup)

    # Les commandes saisies n'ont pas droit à la mise en place (@…).
    for vCommand in pHistory:
        run_command(rRepository, vCommand)

    return rRepository


def run_level_command(pDatabaseFile, pLevelId, pHistory, pCommand, pNow):
    """Joue une commande dans un niveau ; retourne (historique, message, couleur).

    L'historique n'est complété qu'en cas de succès. Un niveau réussi enregistre
    son nombre de commandes. Lève ValueError si le niveau ou l'historique est
    invalide.
    """

    vLevel = require_level(pLevelId)
    vRepository = replay_level(vLevel, pHistory)

    if is_goal_reached(vLevel, vRepository):
        return (list(pHistory), "Niveau déjà réussi : recommencez-le.", "warning")

    vCommand = " ".join(str(pCommand or "").split())

    try:
        vMessage = run_command(vRepository, vCommand)

    except ValueError as vException:
        return (list(pHistory), str(vException), "danger")

    vHistory = [*pHistory, vCommand]

    if len(vHistory) > MAX_HISTORY:
        return (
            list(pHistory),
            f"Limite de {MAX_HISTORY} commandes atteinte.",
            "warning",
        )

    if is_goal_reached(vLevel, vRepository):
        save_git_level_result(pDatabaseFile, pLevelId, len(vHistory), pNow)

        vPar = len(vLevel.solution)
        vMessage = f"Niveau réussi en {len(vHistory)} commande(s)" + (
            " : parcours optimal."
            if len(vHistory) <= vPar
            else f", la solution de référence en utilise {vPar}."
        )

        return (vHistory, vMessage, "success")

    rResult = (vHistory, vMessage, "info")

    return rResult


def build_level_view(pLevelId, pHistory):
    """Retourne l'affichage d'un niveau : textes, graphes et état de réussite.

    Lève ValueError si le niveau ou l'historique est invalide.
    """

    vLevel = require_level(pLevelId)
    vRepository = replay_level(vLevel, pHistory)
    vGoal = replay(vLevel.setup + vLevel.solution)
    vIndex = LEVELS.index(vLevel)

    rView = {
        "id": vLevel.id,
        "title": vLevel.title,
        "series": vLevel.series,
        "intro": vLevel.intro,
        "hint": vLevel.hint,
        "solution": vLevel.solution,
        "par": len(vLevel.solution),
        "history": list(pHistory),
        "done": is_goal_reached(vLevel, vRepository),
        "next_id": LEVELS[vIndex + 1].id if vIndex + 1 < len(LEVELS) else None,
        "graph": render_graph(vRepository.local_view(), "Votre dépôt"),
        "goal": render_graph(vGoal.local_view(), "Objectif"),
        "server": (
            render_graph(vRepository.server_view(), "Serveur", pShowHead=False)
            if vRepository.remote
            else ""
        ),
        "goal_server": (
            render_graph(vGoal.server_view(), "Serveur attendu", pShowHead=False)
            if vGoal.remote
            else ""
        ),
    }

    return rView
