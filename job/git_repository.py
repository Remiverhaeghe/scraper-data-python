"""Bac à sable Git : dépôt simulé et outils communs aux commandes

L'historique (commits, branches et HEAD) et le contenu des fichiers sont
simulés : chaque version d'un fichier est une étiquette (« bleu »,
« bleu+modif »), ce qui suffit pour indexer, mettre de côté et fusionner à
trois voies, conflits compris. Aucun fichier n'est lu ni écrit. Le serveur
origin partage la même réserve de commits : ses branches sont dans remote, leur
copie locale (origin/main) dans tracking, et les commits poussés par l'équipe
restent inconnus du dépôt local jusqu'au prochain fetch.

Le module porte aussi ce que partagent les commandes : fusion à trois voies,
entrée et sortie d'un conflit, contrôle des noms et lecture des options.
"""

import copy
import re
from dataclasses import dataclass, field

BRANCH_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9._/-]{0,29}")
COMMIT_PATTERN = re.compile(r"C\d+'*", re.IGNORECASE)
REFERENCE_PATTERN = re.compile(r"(?P<base>[A-Za-z0-9._/'-]+?)(?P<moves>(?:[\^~]\d*)*)")
MOVE_PATTERN = re.compile(r"([\^~])(\d*)")
FILE_PATTERN = re.compile(r"[\w-][\w./-]{0,39}")

REMOTE_NAME = "origin"

# Contenu d'un fichier en conflit, tant que personne ne l'a corrigé
MARKERS = "marqueurs"

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


def snapshot(pRepository):
    """Retourne une copie de l'état du dépôt, pour annuler une commande en échec."""

    rState = copy.deepcopy(vars(pRepository))

    return rState


def restore(pRepository, pState):
    """Rétablit un état pris par snapshot."""

    vars(pRepository).update(copy.deepcopy(pState))
