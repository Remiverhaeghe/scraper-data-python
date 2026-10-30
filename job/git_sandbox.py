"""Bac à sable Git : dépôt simulé et interprétation des commandes saisies

L'historique (commits, branches et HEAD) et le contenu des fichiers sont
simulés : chaque version d'un fichier est une étiquette (« bleu »,
« bleu+modif »), ce qui suffit pour indexer, mettre de côté et fusionner à
trois voies, conflits compris. Aucun fichier n'est lu ni écrit, et aucune
commande n'est transmise au système. Le serveur origin partage la même réserve
de commits : ses branches sont dans remote, leur copie locale (origin/main)
dans tracking, et les commits poussés par l'équipe restent inconnus du dépôt
local jusqu'au prochain fetch.
"""

import copy
import re
import shlex
from dataclasses import dataclass, field

MAX_COMMAND_LENGTH = 120
MAX_HISTORY = 60

BRANCH_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9._/-]{0,29}")
COMMIT_PATTERN = re.compile(r"C\d+'*", re.IGNORECASE)
REFERENCE_PATTERN = re.compile(r"(?P<base>[A-Za-z0-9._/'-]+?)(?P<moves>(?:[\^~]\d*)*)")
MOVE_PATTERN = re.compile(r"([\^~])(\d*)")
FILE_PATTERN = re.compile(r"[\w-][\w./-]{0,39}")
STASH_PATTERN = re.compile(r"stash@\{(\d+)\}")

REMOTE_NAME = "origin"
# Commandes de mise en place des niveaux, refusées à la saisie
SETUP_PREFIX = "@"
# Commande qui simule la modification d'un fichier dans l'éditeur
EDIT_COMMAND = "modifier"
# Contenu d'un fichier en conflit, tant que personne ne l'a corrigé
MARKERS = "marqueurs"

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

OPERATION_LABELS = {
    "merge": "Fusion",
    "rebase": "Rebase",
    "cherry-pick": "Cherry-pick",
    "stash": "Application de la remise",
}
OPERATION_HINTS = {
    "merge": "git add puis git commit pour terminer, git merge --abort pour abandonner",
    "rebase": "git add puis git rebase --continue, ou --skip, ou --abort",
    "cherry-pick": "git add puis git cherry-pick --continue, ou --abort",
    "stash": "git add pour marquer chaque fichier résolu",
}
# Commandes permises pendant un conflit, en plus des options --continue et --abort
CONFLICT_COMMANDS = ("status", "add", "restore", "diff", "log", "commit")


@dataclass(frozen=True)
class Commit:
    """Commit simulé : parents, nature, commit copié et contenu des fichiers."""

    parents: tuple
    kind: str = "commit"
    origin: str = ""
    tree: tuple = ()


@dataclass
class Repository:
    """Dépôt simulé : commits, branches, HEAD, répertoire de travail et remise."""

    commits: dict = field(default_factory=lambda: {"C0": Commit(())})
    branches: dict = field(default_factory=lambda: {"main": "C0"})
    head: str = "main"
    detached: bool = False
    next_number: int = 1
    remote: dict = field(default_factory=dict)
    tracking: dict = field(default_factory=dict)
    unknown: set = field(default_factory=set)
    # Fichiers modifiés depuis HEAD et leur version, ceux qui sont indexés
    changes: dict = field(default_factory=dict)
    staged: set = field(default_factory=set)
    stash: list = field(default_factory=list)
    # Fusion, rebase, cherry-pick ou remise arrêtés sur un conflit
    conflict: dict = None

    def head_commit(self):
        """Retourne le commit désigné par HEAD."""

        rCommit = self.head if self.detached else self.branches[self.head]

        return rCommit

    def tree(self, pCommit):
        """Retourne le contenu d'un commit : version de chaque fichier."""

        rTree = dict(self.commits[pCommit].tree)

        return rTree

    def head_tree(self):
        """Retourne le contenu du commit de HEAD."""

        rTree = self.tree(self.head_commit())

        return rTree

    def working_tree(self):
        """Retourne le contenu du répertoire de travail : HEAD et modifications."""

        rTree = {**self.head_tree(), **self.changes}

        return rTree

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

    def merge_base(self, pFirst, pSecond):
        """Retourne l'ancêtre commun le plus récent de deux commits."""

        vCommon = self.ancestors(pFirst) & self.ancestors(pSecond)
        vOrder = list(self.commits)

        rBase = max(vCommon, key=vOrder.index)

        return rBase

    def reachable(self):
        """Retourne les commits encore visibles depuis une branche ou HEAD."""

        rReachable = set()

        for vCommit in (
            *self.branches.values(),
            *self.tracking.values(),
            self.head_commit(),
        ):
            rReachable |= self.ancestors(vCommit)

        return rReachable

    def local_view(self):
        """Retourne le dépôt tel que vu localement : origin/… parmi les étiquettes."""

        rView = Repository(
            {
                vCommit: vData
                for vCommit, vData in self.commits.items()
                if vCommit not in self.unknown
            },
            {**self.branches, **self.tracking},
            self.head,
            self.detached,
        )

        return rView

    def server_view(self):
        """Retourne le dépôt du serveur : ses commits et ses branches, sans HEAD."""

        vCommits = set()

        for vCommit in self.remote.values():
            vCommits |= self.ancestors(vCommit)

        rView = Repository(
            {
                vCommit: vData
                for vCommit, vData in self.commits.items()
                if vCommit in vCommits
            },
            dict(self.remote),
            next(iter(self.remote)),
        )

        return rView

    def add_commit(self, pParents, pKind="commit", pOrigin="", pTree=None):
        """Ajoute un commit ; une copie reprend l'identifiant de l'original, suivi de '.

        Sans contenu donné, le commit reprend celui de son premier parent.
        """

        if pKind == "copy":
            rCommit = pOrigin + "'"

            while rCommit in self.commits:
                rCommit += "'"
        else:
            rCommit = f"C{self.next_number}"
            self.next_number += 1

        if pTree is None:
            pTree = self.tree(pParents[0]) if pParents else {}

        self.commits[rCommit] = Commit(
            tuple(pParents), pKind, pOrigin, tuple(sorted(pTree.items()))
        )

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
        elif vBase in self.tracking:
            rCommit = self.tracking[vBase]
        elif vBase.upper() in self.commits and vBase.upper() not in self.unknown:
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


def three_way(pBase, pOurs, pTheirs):
    """Fusionne deux contenus depuis leur base commune ; retourne (contenu, conflits).

    Un fichier modifié d'un seul côté prend cette version ; modifié des deux
    côtés différemment, il est en conflit et garde provisoirement notre version.
    """

    rTree = {}
    rConflicts = {}

    for vFile in sorted(set(pBase) | set(pOurs) | set(pTheirs)):
        vBase, vOurs, vTheirs = (
            pBase.get(vFile),
            pOurs.get(vFile),
            pTheirs.get(vFile),
        )

        if vTheirs in (vOurs, vBase):
            vValue = vOurs
        elif vOurs == vBase:
            vValue = vTheirs
        else:
            rConflicts[vFile] = {"ours": vOurs, "theirs": vTheirs}
            vValue = vOurs

        if vValue is not None:
            rTree[vFile] = vValue

    return (rTree, rConflicts)


def check_overwrite(pRepository, pTree, pConflicts, pAction):
    """Refuse une opération qui écraserait des modifications non validées."""

    vHead = pRepository.head_tree()
    vTouched = sorted(
        vFile
        for vFile in pRepository.changes
        if pTree.get(vFile) != vHead.get(vFile) or vFile in pConflicts
    )

    if vTouched:
        raise ValueError(
            f"Vos modifications locales de {', '.join(vTouched)} seraient écrasées "
            f"par {pAction}. Validez-les (git commit) ou mettez-les de côté "
            "(git stash)"
        )


def require_clean(pRepository, pAction):
    """Refuse une opération qui demande un répertoire de travail propre."""

    if pRepository.changes:
        raise ValueError(
            f"Impossible de lancer {pAction} : modifications non validées "
            f"({', '.join(sorted(pRepository.changes))}). Validez-les ou "
            "mettez-les de côté (git stash)"
        )


def enter_conflict(pRepository, pOperation, pConflicts, pTree, pSaved, **pExtra):
    """Arrête une opération sur un conflit ; retourne le message de git."""

    pRepository.conflict = {
        "operation": pOperation,
        "files": pConflicts,
        "resolved": {},
        "tree": pTree,
        "saved": pSaved,
        **pExtra,
    }

    for vFile in pConflicts:
        pRepository.changes[vFile] = MARKERS
        pRepository.staged.discard(vFile)

    rMessage = (
        f"CONFLIT dans {', '.join(sorted(pConflicts))} : corrigez (modifier, "
        f"git checkout --ours ou --theirs), puis {OPERATION_HINTS[pOperation]}"
    )

    return rMessage


def get_unresolved(pRepository):
    """Retourne les fichiers en conflit pas encore marqués résolus par git add."""

    rFiles = sorted(
        vFile
        for vFile in pRepository.conflict["files"]
        if vFile not in pRepository.conflict["resolved"]
    )

    return rFiles


def close_conflict(pRepository):
    """Termine un conflit résolu ; retourne le contenu obtenu."""

    vConflict = pRepository.conflict
    rTree = {**vConflict["tree"], **vConflict["resolved"]}

    for vFile in vConflict["files"]:
        pRepository.changes.pop(vFile, None)
        pRepository.staged.discard(vFile)

    pRepository.conflict = None

    return rTree


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
        or pName.startswith(f"{REMOTE_NAME}/")
    ):
        raise ValueError(
            f"Nom de branche invalide : {pName} (lettres, chiffres, . _ / -, "
            "30 caractères au plus, différent d'un identifiant de commit et "
            f"sans {REMOTE_NAME}/ au début)"
        )

    if pName in pRepository.branches:
        raise ValueError(f"La branche {pName} existe déjà")


def check_file_name(pName):
    """Vérifie un nom de fichier saisi."""

    if not FILE_PATTERN.fullmatch(pName or "") or ".." in pName:
        raise ValueError(f"Nom de fichier invalide : {pName}")


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


def snapshot(pRepository):
    """Retourne une copie de l'état du dépôt, pour annuler une commande en échec."""

    rState = copy.deepcopy(vars(pRepository))

    return rState


def restore(pRepository, pState):
    """Rétablit un état pris par snapshot."""

    vars(pRepository).update(copy.deepcopy(pState))


def replay(pCommands):
    """Retourne le dépôt obtenu en rejouant des commandes depuis un dépôt neuf."""

    rRepository = Repository()

    for vCommand in pCommands:
        run_command(rRepository, vCommand, pAllowSetup=True)

    return rRepository
