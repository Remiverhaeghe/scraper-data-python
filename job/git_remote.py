"""Bac à sable Git : échanges avec le serveur origin"""

from job.git_history import run_merge, run_rebase
from job.git_repository import (
    REMOTE_NAME,
    check_branch_name,
    expect_values,
    split_options,
)


def require_remote(pRepository):
    """Vérifie que le niveau a un serveur."""

    if not pRepository.remote:
        raise ValueError(f"Aucun dépôt distant {REMOTE_NAME} dans ce niveau")


def run_fetch(pRepository, pArguments):
    """Récupère les branches du serveur dans origin/…, sans toucher aux branches."""

    require_remote(pRepository)
    expect_values(split_options(pArguments)[1], 0, 1, "git fetch [origin]")

    vBefore = dict(pRepository.tracking)
    vCount = len(pRepository.unknown)
    pRepository.tracking = {
        f"{REMOTE_NAME}/{vName}": vCommit
        for vName, vCommit in pRepository.remote.items()
    }
    pRepository.unknown = set()

    if pRepository.tracking == vBefore:
        return "Déjà à jour"

    rMessage = f"{vCount} commit(s) récupéré(s) du serveur"

    return rMessage


def run_pull(pRepository, pArguments):
    """Enchaîne fetch puis la fusion, ou le rebase, de origin/<branche courante>."""

    vOptions, _ = split_options(pArguments)

    if pRepository.detached:
        raise ValueError("HEAD détaché : placez-vous d'abord sur une branche")

    vFetch = run_fetch(pRepository, [])
    vTracked = f"{REMOTE_NAME}/{pRepository.head}"

    if vTracked not in pRepository.tracking:
        raise ValueError(f"{vTracked} n'existe pas sur le serveur")

    vIntegrate = run_rebase if "--rebase" in vOptions else run_merge

    rMessage = f"{vFetch}. {vIntegrate(pRepository, [vTracked])}"

    return rMessage


def run_push(pRepository, pArguments):
    """Envoie une branche au serveur, refusé si le serveur a avancé entre-temps."""

    require_remote(pRepository)
    _, vValues = split_options(pArguments)
    expect_values(vValues, 0, 2, "git push [origin [<branche>]]")

    if vValues and vValues[0] != REMOTE_NAME:
        raise ValueError(f"Dépôt distant inconnu : {vValues[0]}")

    if len(vValues) == 2:
        vBranch = vValues[1]
    elif pRepository.detached:
        raise ValueError("HEAD détaché : précisez la branche à envoyer")
    else:
        vBranch = pRepository.head

    check_branch_name(pRepository, vBranch, True)

    vCommit = pRepository.branches[vBranch]
    vServer = pRepository.remote.get(vBranch)

    if vServer == vCommit:
        return "Déjà à jour"

    if vServer and vServer not in pRepository.ancestors(vCommit):
        raise ValueError(
            "Envoi refusé : le serveur contient des commits que vous n'avez pas. "
            "Récupérez-les d'abord (git pull)"
        )

    pRepository.remote[vBranch] = vCommit
    pRepository.tracking[f"{REMOTE_NAME}/{vBranch}"] = vCommit

    rMessage = f"{vBranch} envoyée : {REMOTE_NAME}/{vBranch} sur {vCommit}"

    return rMessage
