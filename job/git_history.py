"""Bac à sable Git : commandes qui écrivent ou déplacent l'historique"""

from job.git_repository import (
    MARKERS,
    OPERATION_HINTS,
    OPERATION_LABELS,
    check_branch_name,
    check_overwrite,
    close_conflict,
    enter_conflict,
    expect_values,
    get_unresolved,
    require_clean,
    restore,
    snapshot,
    split_options,
    three_way,
)


def run_commit(pRepository, pArguments):
    """Enregistre les modifications indexées ; termine aussi une fusion en conflit.

    Sans aucune modification, le commit ne change que l'historique : c'est le
    cas des niveaux qui ne s'intéressent qu'au graphe.
    """

    vOptions, _ = split_options(pArguments)
    vConflict = pRepository.conflict

    if vConflict:
        if vConflict["operation"] != "merge":
            raise ValueError(
                f"{OPERATION_LABELS[vConflict['operation']]} en cours : "
                f"{OPERATION_HINTS[vConflict['operation']]}"
            )

        vMissing = get_unresolved(pRepository)

        if vMissing:
            raise ValueError(
                f"Impossible de valider : {', '.join(vMissing)} encore en conflit "
                "(git add après correction)"
            )

        vParents = vConflict["parents"]
        vTree = close_conflict(pRepository)
        vCommit = pRepository.add_commit(vParents, "merge", pTree=vTree)
        pRepository.move_head(vCommit)

        return f"Commit de fusion {vCommit} créé" + (
            " ; attention, un fichier contient encore les marqueurs de conflit"
            if MARKERS in vTree.values()
            else ""
        )

    if "-a" in vOptions:
        pRepository.staged |= set(pRepository.changes)

    if pRepository.changes and not pRepository.staged:
        raise ValueError(
            "Aucune modification indexée : git add <fichier> d'abord, "
            "ou git commit -a"
        )

    vHead = pRepository.head_commit()
    vFiles = sorted(pRepository.staged)
    vStaged = {vFile: pRepository.changes.pop(vFile) for vFile in vFiles}
    pRepository.staged = set()

    if "--amend" in vOptions:
        if not pRepository.commits[vHead].parents:
            raise ValueError("Le premier commit ne peut pas être modifié")

        vCommit = pRepository.add_commit(
            pRepository.commits[vHead].parents,
            "copy",
            vHead,
            {**pRepository.tree(vHead), **vStaged},
        )
        pRepository.move_head(vCommit)

        return f"Commit {vHead} remplacé par {vCommit}"

    vCommit = pRepository.add_commit(
        (vHead,), pTree={**pRepository.tree(vHead), **vStaged}
    )
    pRepository.move_head(vCommit)

    rMessage = f"Commit {vCommit} enregistré" + (
        f" ({', '.join(vFiles)})" if vFiles else ""
    )

    return rMessage


def run_branch(pRepository, pArguments):
    """Crée, déplace ou supprime une branche."""

    vOptions, vValues = split_options(pArguments)

    if vOptions and vOptions[0] in ("-d", "-D", "--delete"):
        expect_values(vValues, 1, 1, "git branch -d <nom>")
        check_branch_name(pRepository, vValues[0], True)

        if not pRepository.detached and pRepository.head == vValues[0]:
            raise ValueError(f"Impossible de supprimer {vValues[0]} : HEAD s'y trouve")

        del pRepository.branches[vValues[0]]

        return f"Branche {vValues[0]} supprimée"

    if vOptions and vOptions[0] in ("-f", "--force"):
        expect_values(vValues, 2, 2, "git branch -f <nom> <réf>")
        check_branch_name(pRepository, vValues[0], True)

        if not pRepository.detached and pRepository.head == vValues[0]:
            raise ValueError(
                f"Impossible de forcer {vValues[0]} : HEAD s'y trouve (git reset)"
            )

        pRepository.branches[vValues[0]] = pRepository.resolve(vValues[1])

        return f"Branche {vValues[0]} déplacée sur {pRepository.branches[vValues[0]]}"

    if vOptions:
        raise ValueError(f"Option non prise en charge : {vOptions[0]}")

    if not vValues:
        return "Branches : " + ", ".join(sorted(pRepository.branches))

    expect_values(vValues, 1, 2, "git branch <nom> [<réf>]")
    check_branch_name(pRepository, vValues[0], False)

    vCommit = pRepository.resolve(vValues[1] if len(vValues) == 2 else "HEAD")
    pRepository.branches[vValues[0]] = vCommit

    rMessage = f"Branche {vValues[0]} créée sur {vCommit}"

    return rMessage


def place_head(pRepository, pReference, pDetach=False):
    """Place HEAD sur une branche, ou le détache sur un commit.

    Les modifications en cours suivent, sauf si le changement les écraserait.
    """

    vTarget = pRepository.resolve(pReference)
    check_overwrite(
        pRepository, pRepository.tree(vTarget), {}, "le changement de branche"
    )

    if pReference in pRepository.branches and not pDetach:
        pRepository.head, pRepository.detached = pReference, False

        return f"Sur la branche {pReference}"

    pRepository.head = vTarget
    pRepository.detached = True

    rMessage = f"HEAD détaché sur {pRepository.head}"

    return rMessage


def take_side(pRepository, pOption, pFiles):
    """Résout un conflit en gardant notre version (--ours) ou l'autre (--theirs)."""

    vConflict = pRepository.conflict

    if not vConflict:
        raise ValueError(f"{pOption} ne sert que pendant un conflit")

    expect_values(pFiles, 1, 10, f"git checkout {pOption} <fichier>")
    vSide = "ours" if pOption == "--ours" else "theirs"

    for vFile in pFiles:
        if vFile not in vConflict["files"]:
            raise ValueError(f"{vFile} n'est pas en conflit")

        vVersion = vConflict["files"][vFile][vSide]

        if vVersion is None:
            raise ValueError(f"{vFile} est supprimé de ce côté")

        pRepository.changes[vFile] = vVersion

    rMessage = f"{', '.join(pFiles)} : " + (
        "version de la branche courante gardée"
        if vSide == "ours"
        else "version de l'autre côté gardée"
    )

    return rMessage


def run_switch(pRepository, pArguments, pCreateOption):
    """Change de branche, en la créant avec -c ou -b."""

    vOptions, vValues = split_options(pArguments)
    vOptions = [vOption for vOption in vOptions if vOption != "--"]

    if vOptions and vOptions[0] in ("--ours", "--theirs") and pCreateOption == "-b":
        return take_side(pRepository, vOptions[0], vValues)

    if vOptions and vOptions[0] in (pCreateOption, "--create"):
        expect_values(vValues, 1, 2, f"git … {pCreateOption} <nom> [<réf>]")
        run_branch(pRepository, vValues)

        return place_head(pRepository, vValues[0])

    if vOptions and vOptions[0] != "--detach":
        raise ValueError(f"Option non prise en charge : {vOptions[0]}")

    expect_values(vValues, 1, 1, "git switch <branche>")

    if (
        pCreateOption == "-c"
        and not vOptions
        and vValues[0] not in pRepository.branches
    ):
        raise ValueError(
            f"La branche {vValues[0]} n'existe pas : git switch -c pour la créer, "
            "ou --detach pour se placer sur un commit"
        )

    rMessage = place_head(pRepository, vValues[0], bool(vOptions))

    return rMessage


def run_merge(pRepository, pArguments):
    """Fusionne une référence dans HEAD, par avance rapide quand c'est possible."""

    vOptions, vValues = split_options(pArguments)

    if "--abort" in vOptions:
        return abort_operation(pRepository, "merge")

    expect_values(vValues, 1, 1, "git merge <réf>")

    vTarget = pRepository.resolve(vValues[0])
    vHead = pRepository.head_commit()

    if vTarget in pRepository.ancestors(vHead):
        return "Déjà à jour"

    if vHead in pRepository.ancestors(vTarget):
        check_overwrite(pRepository, pRepository.tree(vTarget), {}, "la fusion")
        pRepository.move_head(vTarget)

        return f"Avance rapide jusqu'à {vTarget}"

    vTree, vConflicts = three_way(
        pRepository.tree(pRepository.merge_base(vHead, vTarget)),
        pRepository.tree(vHead),
        pRepository.tree(vTarget),
    )
    check_overwrite(pRepository, vTree, vConflicts, "la fusion")

    if vConflicts:
        return "Fusion automatique impossible. " + enter_conflict(
            pRepository,
            "merge",
            vConflicts,
            vTree,
            snapshot(pRepository),
            parents=[vHead, vTarget],
        )

    vCommit = pRepository.add_commit((vHead, vTarget), "merge", pTree=vTree)
    pRepository.move_head(vCommit)

    rMessage = f"Commit de fusion {vCommit} créé"

    return rMessage


def play_sequence(pRepository, pOperation, pTodo, pTip, pSaved, pBranch):
    """Recopie des commits un à un sur pTip ; s'arrête au premier conflit.

    Retourne (copies faites, message de conflit ou chaîne vide). À la fin, la
    branche d'un rebase est déplacée sur la dernière copie.
    """

    vTodo = list(pTodo)
    vTip = pTip
    vCopies = []

    while vTodo:
        vCommit = vTodo.pop(0)
        vParents = pRepository.commits[vCommit].parents
        vTree, vConflicts = three_way(
            pRepository.tree(vParents[0]) if vParents else {},
            pRepository.tree(vTip),
            pRepository.tree(vCommit),
        )

        if vConflicts:
            if pOperation == "rebase":
                pRepository.head, pRepository.detached = vTip, True
            else:
                pRepository.move_head(vTip)

            return (
                vCopies,
                f"Arrêt sur {vCommit}. "
                + enter_conflict(
                    pRepository,
                    pOperation,
                    vConflicts,
                    vTree,
                    pSaved,
                    current=vCommit,
                    todo=vTodo,
                    tip=vTip,
                    branch=pBranch,
                ),
            )

        vTip = pRepository.add_commit((vTip,), "copy", vCommit, vTree)
        vCopies.append(vTip)

    if pOperation == "rebase" and pBranch:
        pRepository.branches[pBranch] = vTip
        pRepository.head, pRepository.detached = pBranch, False
    elif pOperation == "rebase":
        pRepository.head, pRepository.detached = vTip, True
    else:
        pRepository.move_head(vTip)

    rResult = (vCopies, "")

    return rResult


def describe_sequence(pOperation, pCopies, pMessage, pBase=""):
    """Retourne le message d'un rebase ou d'un cherry-pick, terminé ou arrêté."""

    if pMessage:
        return (f"{len(pCopies)} commit(s) recopié(s). " if pCopies else "") + pMessage

    if pOperation == "rebase":
        return f"{len(pCopies)} commit(s) rejoué(s)" + (
            f" sur {pBase}" if pBase else ""
        )

    rMessage = "Commit(s) recopié(s) : " + ", ".join(pCopies)

    return rMessage


def continue_operation(pRepository, pOperation, pSkip=False):
    """Poursuit un rebase ou un cherry-pick arrêté sur un conflit."""

    vConflict = pRepository.conflict

    if not vConflict or vConflict["operation"] != pOperation:
        raise ValueError(f"Aucun {pOperation} en cours")

    if not pSkip and get_unresolved(pRepository):
        raise ValueError(
            f"{', '.join(get_unresolved(pRepository))} encore en conflit "
            "(git add après correction)"
        )

    vTip = vConflict["tip"]
    vCurrent = vConflict["current"]
    vTodo = vConflict["todo"]
    vSaved = vConflict["saved"]
    vBranch = vConflict["branch"]
    vTree = close_conflict(pRepository)
    vCopies = []

    if not pSkip:
        vTip = pRepository.add_commit((vTip,), "copy", vCurrent, vTree)
        vCopies.append(vTip)

    vMore, vMessage = play_sequence(
        pRepository, pOperation, vTodo, vTip, vSaved, vBranch
    )

    rMessage = describe_sequence(pOperation, vCopies + vMore, vMessage)

    return rMessage


def abort_operation(pRepository, pOperation):
    """Abandonne l'opération en conflit : le dépôt revient à l'état d'avant."""

    vConflict = pRepository.conflict

    if not vConflict or vConflict["operation"] != pOperation:
        raise ValueError(f"Aucun {pOperation} en cours à abandonner")

    restore(pRepository, vConflict["saved"])

    rMessage = f"{OPERATION_LABELS[pOperation]} abandonné(e) : retour à l'état d'avant"

    return rMessage


def run_rebase(pRepository, pArguments):
    """Rejoue sur une référence les commits propres à la branche courante."""

    vOptions, vValues = split_options(pArguments)

    if "--continue" in vOptions or "--skip" in vOptions:
        return continue_operation(pRepository, "rebase", "--skip" in vOptions)

    if "--abort" in vOptions:
        return abort_operation(pRepository, "rebase")

    expect_values(vValues, 1, 1, "git rebase <réf>")
    require_clean(pRepository, "un rebase")

    vBase = pRepository.resolve(vValues[0])
    vHead = pRepository.head_commit()
    vBaseAncestors = pRepository.ancestors(vBase)

    if vHead in vBaseAncestors:
        pRepository.move_head(vBase)

        return f"Avance rapide jusqu'à {vBase}"

    if vBase in pRepository.ancestors(vHead):
        return "Déjà à jour"

    # Comme git : les fusions ne sont pas rejouées, ni un commit déjà recopié
    # sur la base (même commit d'origine).
    vUpstreamOrigins = {pRepository.root_origin(vCommit) for vCommit in vBaseAncestors}
    vOwnCommits = pRepository.ancestors(vHead) - vBaseAncestors
    vToCopy = [
        vCommit
        for vCommit, vData in pRepository.commits.items()
        if vCommit in vOwnCommits
        and vData.kind != "merge"
        and pRepository.root_origin(vCommit) not in vUpstreamOrigins
    ]

    vCopies, vMessage = play_sequence(
        pRepository,
        "rebase",
        vToCopy,
        vBase,
        snapshot(pRepository),
        None if pRepository.detached else pRepository.head,
    )

    rMessage = describe_sequence("rebase", vCopies, vMessage, vBase)

    return rMessage


def run_reset(pRepository, pArguments):
    """Déplace la branche courante ; --hard efface aussi les modifications en cours."""

    vOptions, vValues = split_options(pArguments)

    for vOption in vOptions:
        if vOption not in ("--hard", "--soft", "--mixed"):
            raise ValueError(f"Option non prise en charge : {vOption}")

    expect_values(vValues, 1, 1, "git reset <réf>")

    vCommit = pRepository.resolve(vValues[0])
    vWorking = pRepository.working_tree()
    pRepository.move_head(vCommit)

    if "--hard" in vOptions:
        pRepository.changes = {}
        pRepository.staged = set()
    else:
        vTree = pRepository.tree(vCommit)
        pRepository.changes = {
            vFile: vVersion
            for vFile, vVersion in vWorking.items()
            if vTree.get(vFile) != vVersion
        }
        pRepository.staged = set(pRepository.changes) if "--soft" in vOptions else set()

    rMessage = f"HEAD ramené sur {vCommit}"

    return rMessage


def run_revert(pRepository, pArguments):
    """Ajoute un commit qui annule le commit désigné."""

    _, vValues = split_options(pArguments)
    expect_values(vValues, 1, 1, "git revert <réf>")

    vTarget = pRepository.resolve(vValues[0])
    vParents = pRepository.commits[vTarget].parents

    if not vParents:
        raise ValueError("Le premier commit ne peut pas être annulé")

    vTree, vConflicts = three_way(
        pRepository.tree(vTarget),
        pRepository.head_tree(),
        pRepository.tree(vParents[0]),
    )

    if vConflicts:
        raise ValueError(
            f"L'annulation de {vTarget} entre en conflit avec des modifications "
            "plus récentes : non simulé ici"
        )

    check_overwrite(pRepository, vTree, {}, "l'annulation")
    vCommit = pRepository.add_commit(
        (pRepository.head_commit(),), "revert", vTarget, vTree
    )
    pRepository.move_head(vCommit)

    rMessage = f"Commit {vCommit} : annulation de {vTarget}"

    return rMessage


def run_cherry_pick(pRepository, pArguments):
    """Recopie un ou plusieurs commits, dans l'ordre donné, sur HEAD."""

    vOptions, vValues = split_options(pArguments)

    if "--continue" in vOptions:
        return continue_operation(pRepository, "cherry-pick")

    if "--abort" in vOptions:
        return abort_operation(pRepository, "cherry-pick")

    expect_values(vValues, 1, 10, "git cherry-pick <réf>…")
    require_clean(pRepository, "un cherry-pick")

    vTargets = [pRepository.resolve(vValue) for vValue in vValues]
    vHeadAncestors = pRepository.ancestors(pRepository.head_commit())

    for vTarget in vTargets:
        if vTarget in vHeadAncestors:
            raise ValueError(f"{vTarget} est déjà présent sous HEAD")

        if pRepository.commits[vTarget].kind == "merge":
            raise ValueError(f"{vTarget} est une fusion : non pris en charge")

    vCopies, vMessage = play_sequence(
        pRepository,
        "cherry-pick",
        vTargets,
        pRepository.head_commit(),
        snapshot(pRepository),
        None,
    )

    rMessage = describe_sequence("cherry-pick", vCopies, vMessage)

    return rMessage


def run_log(pRepository, pArguments):
    """Liste les commits sous HEAD, du plus récent, avec les fichiers changés."""

    expect_values(split_options(pArguments)[1], 0, 1, "git log [--oneline]")
    vAncestors = pRepository.ancestors(pRepository.head_commit())
    vLines = []

    for vCommit in reversed(list(pRepository.commits)):
        if vCommit not in vAncestors:
            continue

        vData = pRepository.commits[vCommit]
        vBefore = pRepository.tree(vData.parents[0]) if vData.parents else {}
        vChanged = [
            f"{vFile}={vVersion}"
            for vFile, vVersion in vData.tree
            if vBefore.get(vFile) != vVersion
        ]
        vLines.append(vCommit + (f" ({', '.join(vChanged)})" if vChanged else ""))

    rMessage = " · ".join(vLines[:12])

    return rMessage
