"""Bac à sable Git : dépôt simulé et interprétation des commandes saisies

Seul l'historique est simulé (commits, branches et HEAD) : aucun fichier n'est
lu ni écrit, et aucune commande n'est transmise au système.
"""

import re
import shlex
from dataclasses import dataclass, field

MAX_COMMAND_LENGTH = 120
MAX_HISTORY = 60

BRANCH_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9._/-]{0,29}")
COMMIT_PATTERN = re.compile(r"C\d+'*", re.IGNORECASE)
REFERENCE_PATTERN = re.compile(r"(?P<base>[A-Za-z0-9._/'-]+?)(?P<moves>(?:[\^~]\d*)*)")
MOVE_PATTERN = re.compile(r"([\^~])(\d*)")

SUPPORTED_COMMANDS = (
    ("git commit [--amend]", "Enregistre un commit sur la position de HEAD"),
    ("git branch <nom> [<réf>]", "Crée une branche, sur HEAD par défaut"),
    ("git branch -f <nom> <réf>", "Déplace une branche existante"),
    ("git branch -d <nom>", "Supprime une branche"),
    ("git switch <branche>", "Se place sur une branche (-c pour la créer)"),
    ("git checkout <réf>", "Se place sur une branche ou un commit (-b pour créer)"),
    ("git merge <réf>", "Intègre une branche, en avance rapide si possible"),
    ("git rebase <réf>", "Rejoue les commits de la branche courante sur la référence"),
    ("git reset <réf>", "Ramène la branche courante sur un commit plus ancien"),
    ("git revert <réf>", "Ajoute un commit qui annule le commit désigné"),
    ("git cherry-pick <réf>…", "Recopie un ou plusieurs commits sur HEAD"),
    ("git status", "Indique la position de HEAD"),
)


@dataclass(frozen=True)
class Commit:
    """Commit simulé : ses parents, sa nature et le commit dont il est la copie."""

    parents: tuple
    kind: str = "commit"
    origin: str = ""


@dataclass
class Repository:
    """Dépôt simulé : commits dans l'ordre de création, branches et position de HEAD."""

    commits: dict = field(default_factory=lambda: {"C0": Commit(())})
    branches: dict = field(default_factory=lambda: {"main": "C0"})
    head: str = "main"
    detached: bool = False
    next_number: int = 1

    def head_commit(self):
        """Retourne le commit désigné par HEAD."""

        rCommit = self.head if self.detached else self.branches[self.head]

        return rCommit

    def ancestors(self, pCommit):
        """Retourne le commit et tous ceux dont il descend."""

        rAncestors = set()
        vPending = [pCommit]

        while vPending:
            vCommit = vPending.pop()

            if vCommit not in rAncestors:
                rAncestors.add(vCommit)
                vPending.extend(self.commits[vCommit].parents)

        return rAncestors

    def reachable(self):
        """Retourne les commits encore visibles depuis une branche ou HEAD."""

        rReachable = set()

        for vCommit in (*self.branches.values(), self.head_commit()):
            rReachable |= self.ancestors(vCommit)

        return rReachable

    def add_commit(self, pParents, pKind="commit", pOrigin=""):
        """Ajoute un commit ; une copie reprend l'identifiant de l'original, suivi de '."""

        if pKind == "copy":
            rCommit = pOrigin + "'"

            while rCommit in self.commits:
                rCommit += "'"
        else:
            rCommit = f"C{self.next_number}"
            self.next_number += 1

        self.commits[rCommit] = Commit(tuple(pParents), pKind, pOrigin)

        return rCommit

    def move_head(self, pCommit):
        """Avance la branche courante, ou HEAD lui-même s'il est détaché."""

        if self.detached:
            self.head = pCommit
        else:
            self.branches[self.head] = pCommit

    def root_origin(self, pCommit):
        """Retourne le commit d'origine d'une copie, en remontant les copies de copies."""

        rCommit = pCommit

        while self.commits[rCommit].kind == "copy":
            rCommit = self.commits[rCommit].origin

        return rCommit

    def resolve(self, pReference):
        """Retourne le commit désigné par une branche, un commit, HEAD, ^ ou ~."""

        vMatch = REFERENCE_PATTERN.fullmatch(pReference or "")

        if vMatch is None:
            raise ValueError(f"Référence invalide : {pReference}")

        vBase = vMatch["base"]

        if vBase.upper() == "HEAD":
            rCommit = self.head_commit()
        elif vBase in self.branches:
            rCommit = self.branches[vBase]
        elif vBase.upper() in self.commits:
            rCommit = vBase.upper()
        else:
            raise ValueError(f"Référence inconnue : {vBase}")

        for vSign, vNumber in MOVE_PATTERN.findall(vMatch["moves"]):
            vCount = int(vNumber) if vNumber else 1
            vParents = self.commits[rCommit].parents

            if vSign == "^":
                if vCount == 0:
                    continue

                if vCount > len(vParents):
                    raise ValueError(f"{pReference} : ce parent n'existe pas")

                rCommit = vParents[vCount - 1]
            else:
                for _ in range(vCount):
                    if not self.commits[rCommit].parents:
                        raise ValueError(
                            f"{pReference} : remonte avant le premier commit"
                        )

                    rCommit = self.commits[rCommit].parents[0]

        return rCommit


def check_branch_name(pRepository, pName, pMustExist):
    """Vérifie un nom de branche, existante ou à créer."""

    if pMustExist:
        if pName not in pRepository.branches:
            raise ValueError(f"La branche {pName} n'existe pas")

        return

    if (
        not BRANCH_PATTERN.fullmatch(pName)
        or pName.upper() == "HEAD"
        or COMMIT_PATTERN.fullmatch(pName)
    ):
        raise ValueError(
            f"Nom de branche invalide : {pName} (lettres, chiffres, . _ / -, "
            "30 caractères au plus, différent d'un identifiant de commit)"
        )

    if pName in pRepository.branches:
        raise ValueError(f"La branche {pName} existe déjà")


def split_options(pArguments):
    """Sépare les options (commençant par -) des autres arguments."""

    vOptions = [vArgument for vArgument in pArguments if vArgument.startswith("-")]
    vValues = [vArgument for vArgument in pArguments if not vArgument.startswith("-")]

    rParts = (vOptions, vValues)

    return rParts


def expect_values(pValues, pMinimum, pMaximum, pUsage):
    """Vérifie le nombre d'arguments d'une commande."""

    if not pMinimum <= len(pValues) <= pMaximum:
        raise ValueError(f"Usage : {pUsage}")


def run_commit(pRepository, pArguments):
    """Ajoute un commit sur HEAD, ou remplace le dernier avec --amend."""

    vOptions, _ = split_options(pArguments)
    vHead = pRepository.head_commit()

    if "--amend" in vOptions:
        if not pRepository.commits[vHead].parents:
            raise ValueError("Le premier commit ne peut pas être modifié")

        vCommit = pRepository.add_commit(
            pRepository.commits[vHead].parents, "copy", vHead
        )
        pRepository.move_head(vCommit)

        return f"Commit {vHead} remplacé par {vCommit}"

    vCommit = pRepository.add_commit((vHead,))
    pRepository.move_head(vCommit)

    rMessage = f"Commit {vCommit} enregistré"

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


def place_head(pRepository, pReference):
    """Place HEAD sur une branche, ou le détache sur un commit."""

    if pReference in pRepository.branches:
        pRepository.head, pRepository.detached = pReference, False

        return f"Sur la branche {pReference}"

    pRepository.head = pRepository.resolve(pReference)
    pRepository.detached = True

    rMessage = f"HEAD détaché sur {pRepository.head}"

    return rMessage


def run_switch(pRepository, pArguments, pCreateOption):
    """Change de branche, en la créant avec -c ou -b."""

    vOptions, vValues = split_options(pArguments)

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

    if vOptions:
        pRepository.head = pRepository.resolve(vValues[0])
        pRepository.detached = True

        return f"HEAD détaché sur {pRepository.head}"

    rMessage = place_head(pRepository, vValues[0])

    return rMessage


def run_merge(pRepository, pArguments):
    """Fusionne une référence dans HEAD, par avance rapide quand c'est possible."""

    _, vValues = split_options(pArguments)
    expect_values(vValues, 1, 1, "git merge <réf>")

    vTarget = pRepository.resolve(vValues[0])
    vHead = pRepository.head_commit()

    if vTarget in pRepository.ancestors(vHead):
        return "Déjà à jour"

    if vHead in pRepository.ancestors(vTarget):
        pRepository.move_head(vTarget)

        return f"Avance rapide jusqu'à {vTarget}"

    vCommit = pRepository.add_commit((vHead, vTarget), "merge")
    pRepository.move_head(vCommit)

    rMessage = f"Commit de fusion {vCommit} créé"

    return rMessage


def run_rebase(pRepository, pArguments):
    """Rejoue sur une référence les commits propres à la branche courante."""

    _, vValues = split_options(pArguments)
    expect_values(vValues, 1, 1, "git rebase <réf>")

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

    vTip = vBase

    for vCommit in vToCopy:
        vTip = pRepository.add_commit((vTip,), "copy", vCommit)

    pRepository.move_head(vTip)

    rMessage = f"{len(vToCopy)} commit(s) rejoué(s) sur {vBase}"

    return rMessage


def run_reset(pRepository, pArguments):
    """Déplace la branche courante (ou HEAD détaché) sur une référence."""

    vOptions, vValues = split_options(pArguments)

    for vOption in vOptions:
        if vOption not in ("--hard", "--soft", "--mixed"):
            raise ValueError(f"Option non prise en charge : {vOption}")

    expect_values(vValues, 1, 1, "git reset <réf>")

    vCommit = pRepository.resolve(vValues[0])
    pRepository.move_head(vCommit)

    rMessage = f"HEAD ramené sur {vCommit}"

    return rMessage


def run_revert(pRepository, pArguments):
    """Ajoute un commit qui annule le commit désigné."""

    _, vValues = split_options(pArguments)
    expect_values(vValues, 1, 1, "git revert <réf>")

    vTarget = pRepository.resolve(vValues[0])

    if not pRepository.commits[vTarget].parents:
        raise ValueError("Le premier commit ne peut pas être annulé")

    vCommit = pRepository.add_commit((pRepository.head_commit(),), "revert", vTarget)
    pRepository.move_head(vCommit)

    rMessage = f"Commit {vCommit} : annulation de {vTarget}"

    return rMessage


def run_cherry_pick(pRepository, pArguments):
    """Recopie un ou plusieurs commits, dans l'ordre donné, sur HEAD."""

    _, vValues = split_options(pArguments)
    expect_values(vValues, 1, 10, "git cherry-pick <réf>…")

    vTargets = [pRepository.resolve(vValue) for vValue in vValues]
    vCopies = []

    for vTarget in vTargets:
        if vTarget in pRepository.ancestors(pRepository.head_commit()):
            raise ValueError(f"{vTarget} est déjà présent sous HEAD")

        if pRepository.commits[vTarget].kind == "merge":
            raise ValueError(f"{vTarget} est une fusion : non pris en charge")

        vCopy = pRepository.add_commit((pRepository.head_commit(),), "copy", vTarget)
        pRepository.move_head(vCopy)
        vCopies.append(vCopy)

    rMessage = "Commit(s) recopié(s) : " + ", ".join(vCopies)

    return rMessage


def run_status(pRepository, pArguments):
    """Indique la position de HEAD."""

    expect_values(pArguments, 0, 0, "git status")

    if pRepository.detached:
        return f"HEAD détaché sur {pRepository.head}"

    rMessage = (
        f"Sur la branche {pRepository.head}, "
        f"commit {pRepository.branches[pRepository.head]}"
    )

    return rMessage


COMMANDS = {
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
    "status": run_status,
}


def run_command(pRepository, pCommand):
    """Exécute une commande sur le dépôt simulé ; retourne le message à afficher.

    Lève ValueError, sans rien modifier, si la commande est invalide.
    """

    if len(pCommand) > MAX_COMMAND_LENGTH:
        raise ValueError("Commande trop longue")

    try:
        vWords = shlex.split(pCommand)

    except ValueError:
        raise ValueError("Guillemet non refermé") from None

    if not vWords:
        raise ValueError("Saisissez une commande")

    if vWords[0] != "git" or len(vWords) < 2:
        raise ValueError("Les commandes commencent par git, par exemple git commit")

    vAction = COMMANDS.get(vWords[1])

    if vAction is None:
        raise ValueError(f"Commande non prise en charge : git {vWords[1]}")

    # Le message de commit n'a pas d'effet sur le graphe.
    vArguments = vWords[2:]

    if vWords[1] == "commit":
        vArguments = [vArgument for vArgument in vArguments if vArgument == "--amend"]

    vBefore = snapshot(pRepository)

    try:
        rMessage = vAction(pRepository, vArguments)

    except ValueError:
        restore(pRepository, vBefore)
        raise

    return rMessage


def snapshot(pRepository):
    """Retourne une copie de l'état du dépôt, pour annuler une commande en échec."""

    rState = (
        dict(pRepository.commits),
        dict(pRepository.branches),
        pRepository.head,
        pRepository.detached,
        pRepository.next_number,
    )

    return rState


def restore(pRepository, pState):
    """Rétablit un état pris par snapshot."""

    (
        pRepository.commits,
        pRepository.branches,
        pRepository.head,
        pRepository.detached,
        pRepository.next_number,
    ) = (dict(pState[0]), dict(pState[1]), *pState[2:])


def replay(pCommands):
    """Retourne le dépôt obtenu en rejouant des commandes depuis un dépôt neuf."""

    rRepository = Repository()

    for vCommand in pCommands:
        run_command(rRepository, vCommand)

    return rRepository
