"""Bac à sable Git : interprétation des commandes saisies

La saisie est découpée comme le ferait un shell, contrôlée, puis confiée au
module qui traite la commande : git_worktree pour les fichiers, l'index et la
remise, git_history pour l'historique, git_remote pour le serveur. Aucune
commande n'est transmise au système, et une commande refusée laisse le dépôt
dans son état précédent.
"""

import re
import shlex

from job.git_history import (
    run_branch,
    run_cherry_pick,
    run_commit,
    run_log,
    run_merge,
    run_rebase,
    run_reset,
    run_revert,
    run_switch,
)
from job.git_remote import run_fetch, run_pull, run_push
from job.git_repository import (
    OPERATION_HINTS,
    OPERATION_LABELS,
    REMOTE_NAME,
    Repository,
    check_file_name,
    expect_values,
    restore,
    snapshot,
    split_options,
)
from job.git_worktree import (
    run_add,
    run_diff,
    run_edit,
    run_restore,
    run_stash,
    run_status,
)

MAX_COMMAND_LENGTH = 120
MAX_HISTORY = 60

# Commandes de mise en place des niveaux, refusées à la saisie
SETUP_PREFIX = "@"

# Commande qui simule la modification d'un fichier dans l'éditeur
EDIT_COMMAND = "modifier"

SUPPORTED_COMMANDS = (
    ("modifier <fichier>", "Simule la modification d'un fichier dans l'éditeur"),
    ("git add <fichier> | .", "Indexe une modification, ou marque un conflit résolu"),
    ("git restore [--staged] <fichier>", "Annule une modification, ou la désindexe"),
    (
        "git commit [-a] [--amend]",
        "Enregistre un commit avec les modifications indexées",
    ),
    ("git status", "Indique la branche, les modifications, la remise et les conflits"),
    ("git diff", "Liste les fichiers modifiés et indexés"),
    ("git log", "Liste les commits sous HEAD et les fichiers qu'ils changent"),
    ("git branch <nom> [<réf>]", "Crée une branche, sur HEAD par défaut"),
    ("git branch -f <nom> <réf>", "Déplace une branche existante"),
    ("git branch -d <nom>", "Supprime une branche"),
    ("git switch <branche>", "Se place sur une branche (-c pour la créer)"),
    ("git checkout <réf>", "Se place sur une branche ou un commit (-b pour créer)"),
    (
        "git checkout --ours | --theirs <fichier>",
        "Garde sa version ou l'autre, en conflit",
    ),
    (
        "git merge <réf> | --abort",
        "Intègre une branche, ou abandonne une fusion en conflit",
    ),
    ("git rebase <réf>", "Rejoue les commits de la branche courante sur la référence"),
    (
        "git rebase --continue | --skip | --abort",
        "Poursuit, saute ou abandonne un rebase",
    ),
    ("git reset [--soft | --hard] <réf>", "Ramène la branche courante sur un commit"),
    ("git revert <réf>", "Ajoute un commit qui annule le commit désigné"),
    ("git cherry-pick <réf>… | --continue | --abort", "Recopie des commits sur HEAD"),
    ("git stash [pop | apply | list | drop]", "Met de côté les modifications en cours"),
    ("git fetch", "Récupère les commits du serveur sans toucher aux branches locales"),
    ("git pull [--rebase]", "fetch puis fusion (ou rebase) de origin/<branche>"),
    ("git push", "Envoie la branche courante au serveur"),
)
# Commandes permises pendant un conflit, en plus des options --continue et --abort
CONFLICT_COMMANDS = ("status", "add", "restore", "diff", "log", "commit")


def read_files(pWords):
    """Retourne les fichiers fichier=étiquette d'une commande de mise en place."""

    rFiles = {}

    for vWord in pWords:
        vFile, vSeparator, vVersion = vWord.partition("=")

        if not vSeparator or not vVersion:
            raise ValueError(f"Mise en place : fichier=étiquette attendu, pas {vWord}")

        check_file_name(vFile)
        rFiles[vFile] = vVersion

    return rFiles


def run_setup(pRepository, pWords):
    """Prépare un niveau : clone, commits de l'équipe, commits ou modifications.

    @clone · @equipe <branche> [n] [fichier=étiquette…] · @commit fichier=étiquette…
    · @modifie fichier=étiquette…
    """

    if pWords == ["@clone"]:
        pRepository.remote = dict(pRepository.branches)
        pRepository.tracking = {
            f"{REMOTE_NAME}/{vName}": vCommit
            for vName, vCommit in pRepository.branches.items()
        }
    elif pWords[0] == "@equipe" and len(pWords) >= 2:
        vBranch = pWords[1]
        vCount = int(pWords[2]) if len(pWords) > 2 and pWords[2].isdigit() else 1
        vFiles = read_files([vWord for vWord in pWords[2:] if not vWord.isdigit()])
        vParent = pRepository.remote.get(vBranch, pRepository.remote.get("main"))

        for _ in range(vCount):
            vParent = pRepository.add_commit(
                (vParent,), pTree={**pRepository.tree(vParent), **vFiles}
            )
            pRepository.unknown.add(vParent)

        pRepository.remote[vBranch] = vParent
    elif pWords[0] == "@commit" and len(pWords) >= 2:
        vHead = pRepository.head_commit()
        vCommit = pRepository.add_commit(
            (vHead,), pTree={**pRepository.tree(vHead), **read_files(pWords[1:])}
        )
        pRepository.move_head(vCommit)
    elif pWords[0] == "@modifie" and len(pWords) >= 2:
        pRepository.changes.update(read_files(pWords[1:]))
    else:
        raise ValueError(f"Mise en place inconnue : {' '.join(pWords)}")


COMMANDS = {
    "add": run_add,
    "restore": run_restore,
    "commit": run_commit,
    "branch": run_branch,
    "switch": lambda pRepository, pArguments: run_switch(pRepository, pArguments, "-c"),
    "checkout": lambda pRepository, pArguments: run_switch(
        pRepository, pArguments, "-b"
    ),
    "merge": run_merge,
    "rebase": run_rebase,
    "reset": run_reset,
    "revert": run_revert,
    "cherry-pick": run_cherry_pick,
    "stash": run_stash,
    "status": run_status,
    "diff": run_diff,
    "log": run_log,
    "fetch": run_fetch,
    "pull": run_pull,
    "push": run_push,
}


def read_commit_options(pArguments):
    """Garde les options utiles de git commit : le message n'a pas d'effet ici."""

    rOptions = []

    for vArgument in pArguments:
        if vArgument in ("--amend", "-a", "--all"):
            rOptions.append("-a" if vArgument == "--all" else vArgument)
        elif re.fullmatch(r"-[a-z]*a[a-z]*", vArgument):
            rOptions.append("-a")

    return rOptions


def check_conflict_command(pRepository, pAction, pArguments):
    """Refuse pendant un conflit ce qui ne sert pas à le résoudre."""

    vConflict = pRepository.conflict

    if not vConflict:
        return

    vOptions = set(split_options(pArguments)[0])
    vAllowed = (
        pAction in CONFLICT_COMMANDS
        or (
            pAction in ("merge", "rebase", "cherry-pick")
            and vOptions & {"--continue", "--skip", "--abort"}
        )
        or (pAction == "checkout" and vOptions & {"--ours", "--theirs"})
        or (pAction == "stash" and pArguments[:1] == ["list"])
    )

    if not vAllowed:
        raise ValueError(
            f"{OPERATION_LABELS[vConflict['operation']]} en cours : "
            f"{OPERATION_HINTS[vConflict['operation']]}"
        )


def run_command(pRepository, pCommand, pAllowSetup=False):
    """Exécute une commande sur le dépôt simulé ; retourne le message à afficher.

    pAllowSetup accepte les commandes de mise en place d'un niveau (@…). Lève
    ValueError, sans rien modifier, si la commande est invalide.
    """

    if len(pCommand) > MAX_COMMAND_LENGTH:
        raise ValueError("Commande trop longue")

    try:
        vWords = shlex.split(pCommand)

    except ValueError:
        raise ValueError("Guillemet non refermé") from None

    if not vWords:
        raise ValueError("Saisissez une commande")

    if pAllowSetup and vWords[0].startswith(SETUP_PREFIX):
        run_setup(pRepository, vWords)

        return ""

    vBefore = snapshot(pRepository)

    try:
        if vWords[0] == EDIT_COMMAND:
            expect_values(vWords[1:], 1, 1, f"{EDIT_COMMAND} <fichier>")
            return run_edit(pRepository, vWords[1])

        if vWords[0] != "git" or len(vWords) < 2:
            raise ValueError(
                "Les commandes commencent par git (par exemple git commit), "
                f"ou {EDIT_COMMAND} <fichier>"
            )

        vAction = COMMANDS.get(vWords[1])

        if vAction is None:
            raise ValueError(f"Commande non prise en charge : git {vWords[1]}")

        vArguments = vWords[2:]

        if vWords[1] == "commit":
            vArguments = read_commit_options(vArguments)

        check_conflict_command(pRepository, vWords[1], vArguments)
        rMessage = vAction(pRepository, vArguments)

    except ValueError:
        restore(pRepository, vBefore)
        raise

    return rMessage


def replay(pCommands):
    """Retourne le dépôt obtenu en rejouant des commandes depuis un dépôt neuf."""

    rRepository = Repository()

    for vCommand in pCommands:
        run_command(rRepository, vCommand, pAllowSetup=True)

    return rRepository
