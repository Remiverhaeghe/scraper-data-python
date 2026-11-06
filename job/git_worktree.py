"""Bac à sable Git : commandes sur les fichiers, l'index et la remise"""

import re

from job.git_repository import (
    MARKERS,
    OPERATION_HINTS,
    OPERATION_LABELS,
    check_file_name,
    enter_conflict,
    expect_values,
    get_unresolved,
    snapshot,
    split_options,
)

STASH_PATTERN = re.compile(r"stash@\{(\d+)\}")


def run_edit(pRepository, pFile):
    """Simule la modification d'un fichier ; en conflit, garde les deux versions."""

    check_file_name(pFile)
    vConflict = pRepository.conflict

    if vConflict and pFile in vConflict["files"]:
        vSides = vConflict["files"][pFile]
        pRepository.changes[pFile] = "+".join(
            vSide for vSide in (vSides["ours"], vSides["theirs"]) if vSide
        )

        return f"{pFile} corrigé à la main : les deux modifications sont gardées"

    vCurrent = pRepository.working_tree().get(pFile)
    pRepository.changes[pFile] = f"{vCurrent}+modif" if vCurrent else "nouveau"

    rMessage = f"{pFile} modifié" + ("" if vCurrent else " (nouveau fichier)")

    return rMessage


def run_add(pRepository, pArguments):
    """Indexe des modifications ; pendant un conflit, marque les fichiers résolus."""

    vOptions, vValues = split_options(pArguments)
    vAll = "." in vValues or bool({"-A", "--all"} & set(vOptions))

    if not vAll:
        expect_values(vValues, 1, 10, "git add <fichier>… ou git add .")

    vFiles = sorted(pRepository.changes) if vAll else vValues

    for vFile in vFiles:
        if vFile not in pRepository.changes:
            raise ValueError(f"Aucune modification de {vFile} à indexer")

    vConflict = pRepository.conflict
    vMarkers = []

    for vFile in vFiles:
        pRepository.staged.add(vFile)

        if vConflict and vFile in vConflict["files"]:
            vConflict["resolved"][vFile] = pRepository.changes[vFile]

        if pRepository.changes[vFile] == MARKERS:
            vMarkers.append(vFile)

    rMessage = "Indexé : " + ", ".join(vFiles) if vFiles else "Rien à indexer"

    if vMarkers:
        rMessage += (
            f". Attention : {', '.join(vMarkers)} contient encore les marqueurs "
            "<<<<<<< ======= >>>>>>>"
        )

    if (
        vConflict
        and vConflict["operation"] == "stash"
        and not get_unresolved(pRepository)
    ):
        vTree = {**vConflict["tree"], **vConflict["resolved"]}
        pRepository.conflict = None
        pRepository.changes.update(vTree)
        rMessage += ". Conflit résolu ; la remise reste dans la liste (git stash drop)"

    return rMessage


def run_restore(pRepository, pArguments):
    """Annule la modification d'un fichier, ou la retire seulement de l'index."""

    vOptions, vValues = split_options(pArguments)
    expect_values(vValues, 1, 10, "git restore [--staged] <fichier>…")

    for vFile in vValues:
        if vFile not in pRepository.changes:
            raise ValueError(f"Aucune modification de {vFile}")

        if pRepository.conflict and vFile in pRepository.conflict["files"]:
            raise ValueError(
                f"{vFile} est en conflit : modifiez-le, ou git checkout --ours "
                "ou --theirs"
            )

    for vFile in vValues:
        pRepository.staged.discard(vFile)

        if "--staged" not in vOptions:
            pRepository.changes.pop(vFile)

    rMessage = (
        "Retiré de l'index : " if "--staged" in vOptions else "Modification annulée : "
    ) + ", ".join(vValues)

    return rMessage


def run_stash(pRepository, pArguments):
    """Met de côté les modifications en cours, puis les réapplique."""

    _, vValues = split_options(pArguments)
    vAction = vValues[0] if vValues else "push"
    vStash = pRepository.stash

    if vAction in ("push", "save"):
        if not pRepository.changes:
            return "Aucune modification à mettre de côté"

        vStash.insert(
            0,
            {
                "changes": dict(pRepository.changes),
                "base": {
                    vFile: pRepository.head_tree().get(vFile)
                    for vFile in pRepository.changes
                },
                "where": pRepository.head,
            },
        )
        vFiles = ", ".join(sorted(pRepository.changes))
        pRepository.changes = {}
        pRepository.staged = set()

        return f"Modifications mises de côté dans stash@{{0}} : {vFiles}"

    if vAction == "list":
        return (
            " · ".join(
                f"stash@{{{vIndex}}} : sur {vEntry['where']}, "
                f"{', '.join(sorted(vEntry['changes']))}"
                for vIndex, vEntry in enumerate(vStash)
            )
            or "Remise vide"
        )

    vIndex = 0

    if len(vValues) == 2:
        vMatch = STASH_PATTERN.fullmatch(vValues[1])

        if not vMatch:
            raise ValueError("Désignez une entrée comme stash@{0}")

        vIndex = int(vMatch.group(1))

    if vIndex >= len(vStash):
        raise ValueError(
            "Cette entrée de la remise n'existe pas" if vStash else "Remise vide"
        )

    if vAction == "drop":
        del vStash[vIndex]

        return f"stash@{{{vIndex}}} supprimée"

    if vAction not in ("pop", "apply"):
        raise ValueError("Usage : git stash [push | pop | apply | list | drop]")

    vEntry = vStash[vIndex]
    vOverlap = sorted(set(vEntry["changes"]) & set(pRepository.changes))

    if vOverlap:
        raise ValueError(
            f"Vos modifications locales de {', '.join(vOverlap)} seraient écrasées : "
            "validez-les ou mettez-les aussi de côté"
        )

    vSaved = snapshot(pRepository)
    vHead = pRepository.head_tree()
    vConflicts = {}

    for vFile, vVersion in vEntry["changes"].items():
        vCurrent = vHead.get(vFile)

        if vCurrent == vEntry["base"].get(vFile):
            pRepository.changes[vFile] = vVersion
        elif vCurrent != vVersion:
            vConflicts[vFile] = {"ours": vCurrent, "theirs": vVersion}

    if vConflicts:
        return enter_conflict(pRepository, "stash", vConflicts, {}, vSaved) + (
            ". La remise est conservée"
        )

    if vAction == "pop":
        del vStash[vIndex]

    rMessage = f"Modifications réappliquées : {', '.join(sorted(vEntry['changes']))}"

    return rMessage


def describe_worktree(pRepository):
    """Retourne l'état du répertoire de travail, ligne par ligne, pour l'affichage."""

    rLines = []
    vConflict = pRepository.conflict

    if vConflict:
        rLines.append(
            f"{OPERATION_LABELS[vConflict['operation']]} en cours, conflit dans "
            + ", ".join(
                f"{vFile} ({'résolu' if vFile in vConflict['resolved'] else 'à résoudre'})"
                for vFile in sorted(vConflict["files"])
            )
        )

    vStaged = sorted(pRepository.staged)
    vModified = sorted(set(pRepository.changes) - pRepository.staged)

    if vStaged:
        rLines.append("Indexé : " + ", ".join(vStaged))

    if vModified:
        rLines.append("Modifié, non indexé : " + ", ".join(vModified))

    if pRepository.stash:
        rLines.append(f"Remise : {len(pRepository.stash)} entrée(s)")

    return rLines


def run_status(pRepository, pArguments):
    """Indique la position de HEAD, les modifications, la remise et les conflits."""

    expect_values(pArguments, 0, 0, "git status")

    if pRepository.detached:
        vPosition = f"HEAD détaché sur {pRepository.head}"
    else:
        vPosition = (
            f"Sur la branche {pRepository.head}, "
            f"commit {pRepository.branches[pRepository.head]}"
        )

    rMessage = " · ".join([vPosition] + describe_worktree(pRepository))

    if pRepository.conflict:
        rMessage += (
            f" · Pour finir : {OPERATION_HINTS[pRepository.conflict['operation']]}"
        )

    return rMessage


def run_diff(pRepository, pArguments):
    """Liste les fichiers modifiés depuis HEAD et ceux qui sont indexés."""

    expect_values(split_options(pArguments)[1], 0, 1, "git diff [--staged]")

    rMessage = " · ".join(describe_worktree(pRepository)[-3:]) or "Aucune modification"

    return rMessage
