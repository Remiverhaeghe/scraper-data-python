// Dépôt Git simulé, hors ligne : même modèle que job/git_repository.py
// (commits, branches, fichiers, index, remise, conflits, serveur origin) et
// outils partagés par les commandes : fusion à trois voies, conflits, noms
// et options.

const remoteName = 'origin';
const markers = 'marqueurs';

final branchPattern = RegExp(r"^[A-Za-z][A-Za-z0-9._/-]{0,29}$");
final commitPattern = RegExp(r"^C\d+'*$", caseSensitive: false);
final referencePattern = RegExp(r"^(?<base>[A-Za-z0-9._/'-]+?)(?<moves>(?:[\^~]\d*)*)$");
final movePattern = RegExp(r'([\^~])(\d*)');
final filePattern = RegExp(r'^[\p{L}\p{N}\p{M}_-][\p{L}\p{N}\p{M}_./-]{0,39}$', unicode: true);

const operationLabels = {
  'merge': 'Fusion',
  'rebase': 'Rebase',
  'cherry-pick': 'Cherry-pick',
  'stash': 'Application de la remise',
};
const operationHints = {
  'merge': 'git add puis git commit pour terminer, git merge --abort pour abandonner',
  'rebase': 'git add puis git rebase --continue, ou --skip, ou --abort',
  'cherry-pick': 'git add puis git cherry-pick --continue, ou --abort',
  'stash': 'git add pour marquer chaque fichier résolu',
};

/// Commande refusée, avec le message à afficher ; le dépôt n'a pas changé.
class GitError implements Exception {
  GitError(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Commit simulé : parents, nature, commit copié et contenu des fichiers.
class Commit {
  const Commit(this.parents, [this.kind = 'commit', this.origin = '', this.tree = const {}]);

  final List<String> parents;
  final String kind;
  final String origin;

  /// Version de chaque fichier, triée par nom.
  final Map<String, String> tree;
}

/// Contenu trié par nom de fichier, comme le tuple trié de Python.
Map<String, String> sortedTree(Map<String, String> pTree) =>
    {for (final vFile in pTree.keys.toList()..sort()) vFile: pTree[vFile]!};

List<String> sortedOf(Iterable<String> pValues) => pValues.toList()..sort();

class Repository {
  Repository({
    Map<String, Commit>? commits,
    Map<String, String>? branches,
    this.head = 'main',
    this.detached = false,
  })  : commits = commits ?? {'C0': const Commit([])},
        branches = branches ?? {'main': 'C0'};

  Map<String, Commit> commits;
  Map<String, String> branches;
  String head;
  bool detached;
  int nextNumber = 1;
  Map<String, String> remote = {};
  Map<String, String> tracking = {};
  Set<String> unknown = {};
  Map<String, String> changes = {};
  Set<String> staged = {};
  List<Map<String, dynamic>> stash = [];
  Map<String, dynamic>? conflict;

  /// Copie complète, pour annuler une commande ou abandonner une opération.
  Repository copy() {
    final rCopy =
        Repository(commits: {...commits}, branches: {...branches}, head: head, detached: detached)
          ..nextNumber = nextNumber
          ..remote = {...remote}
          ..tracking = {...tracking}
          ..unknown = {...unknown}
          ..changes = {...changes}
          ..staged = {...staged}
          ..stash = [
            for (final vEntry in stash)
              {
                'changes': {...vEntry['changes'] as Map<String, String>},
                'base': {...vEntry['base'] as Map<String, String?>},
                'where': vEntry['where'],
              },
          ];

    if (conflict != null) {
      final vConflict = conflict!;

      rCopy.conflict = {
        ...vConflict,
        'files': {
          for (final vEntry in (vConflict['files'] as Map<String, Map<String, String?>>).entries)
            vEntry.key: {...vEntry.value},
        },
        'resolved': {...vConflict['resolved'] as Map<String, String>},
        'tree': {...vConflict['tree'] as Map<String, String>},
        'saved': (vConflict['saved'] as Repository).copy(),
        if (vConflict.containsKey('todo')) 'todo': [...vConflict['todo'] as List<String>],
        if (vConflict.containsKey('parents')) 'parents': [...vConflict['parents'] as List<String>],
      };
    }

    return rCopy;
  }

  void restoreFrom(Repository pState) {
    final vCopy = pState.copy();

    commits = vCopy.commits;
    branches = vCopy.branches;
    head = vCopy.head;
    detached = vCopy.detached;
    nextNumber = vCopy.nextNumber;
    remote = vCopy.remote;
    tracking = vCopy.tracking;
    unknown = vCopy.unknown;
    changes = vCopy.changes;
    staged = vCopy.staged;
    stash = vCopy.stash;
    conflict = vCopy.conflict;
  }

  String headCommit() => detached ? head : branches[head]!;

  Map<String, String> tree(String pCommit) => {...commits[pCommit]!.tree};

  Map<String, String> headTree() => tree(headCommit());

  Map<String, String> workingTree() => {...headTree(), ...changes};

  Set<String> ancestors(String pCommit) {
    final rAncestors = <String>{};
    final vPending = [pCommit];

    while (vPending.isNotEmpty) {
      final vCommit = vPending.removeLast();

      if (rAncestors.add(vCommit)) {
        vPending.addAll(commits[vCommit]!.parents);
      }
    }

    return rAncestors;
  }

  String mergeBase(String pFirst, String pSecond) {
    final vCommon = ancestors(pFirst).intersection(ancestors(pSecond));
    final vOrder = commits.keys.toList();

    return vCommon.reduce((pA, pB) => vOrder.indexOf(pA) >= vOrder.indexOf(pB) ? pA : pB);
  }

  Set<String> reachable() => {
        for (final vCommit in [...branches.values, ...tracking.values, headCommit()])
          ...ancestors(vCommit),
      };

  Repository localView() => Repository(
        commits: {
          for (final vEntry in commits.entries)
            if (!unknown.contains(vEntry.key)) vEntry.key: vEntry.value,
        },
        branches: {...branches, ...tracking},
        head: head,
        detached: detached,
      );

  Repository serverView() {
    final vCommits = {for (final vCommit in remote.values) ...ancestors(vCommit)};

    return Repository(
      commits: {
        for (final vEntry in commits.entries)
          if (vCommits.contains(vEntry.key)) vEntry.key: vEntry.value,
      },
      branches: {...remote},
      head: remote.keys.first,
    );
  }

  String addCommit(List<String> pParents,
      [String pKind = 'commit', String pOrigin = '', Map<String, String>? pTree]) {
    var rCommit = '';

    if (pKind == 'copy') {
      rCommit = "$pOrigin'";

      while (commits.containsKey(rCommit)) {
        rCommit += "'";
      }
    } else {
      rCommit = 'C$nextNumber';
      nextNumber++;
    }

    final vTree = pTree ?? (pParents.isEmpty ? <String, String>{} : tree(pParents.first));

    commits[rCommit] = Commit(List.of(pParents), pKind, pOrigin, sortedTree(vTree));

    return rCommit;
  }

  void moveHead(String pCommit) {
    if (detached) {
      head = pCommit;
    } else {
      branches[head] = pCommit;
    }
  }

  String rootOrigin(String pCommit) {
    var rCommit = pCommit;

    while (commits[rCommit]!.kind == 'copy') {
      rCommit = commits[rCommit]!.origin;
    }

    return rCommit;
  }

  String resolve(String? pReference) {
    final vMatch = referencePattern.firstMatch(pReference ?? '');

    if (vMatch == null) {
      throw GitError('Référence invalide : $pReference');
    }

    final vBase = vMatch.namedGroup('base')!;
    String rCommit;

    if (vBase.toUpperCase() == 'HEAD') {
      rCommit = headCommit();
    } else if (branches.containsKey(vBase)) {
      rCommit = branches[vBase]!;
    } else if (tracking.containsKey(vBase)) {
      rCommit = tracking[vBase]!;
    } else if (commits.containsKey(vBase.toUpperCase()) && !unknown.contains(vBase.toUpperCase())) {
      rCommit = vBase.toUpperCase();
    } else {
      throw GitError('Référence inconnue : $vBase');
    }

    for (final vMove in movePattern.allMatches(vMatch.namedGroup('moves')!)) {
      final vCount = vMove.group(2)!.isEmpty ? 1 : int.parse(vMove.group(2)!);
      final vParents = commits[rCommit]!.parents;

      if (vMove.group(1) == '^') {
        if (vCount == 0) {
          continue;
        }

        if (vCount > vParents.length) {
          throw GitError('$pReference : ce parent n\'existe pas');
        }

        rCommit = vParents[vCount - 1];
      } else {
        for (var vIndex = 0; vIndex < vCount; vIndex++) {
          if (commits[rCommit]!.parents.isEmpty) {
            throw GitError('$pReference : remonte avant le premier commit');
          }

          rCommit = commits[rCommit]!.parents.first;
        }
      }
    }

    return rCommit;
  }
}

/// Fusion à trois voies : (contenu, conflits {fichier : {ours, theirs}}).
(Map<String, String>, Map<String, Map<String, String?>>) threeWay(
  Map<String, String> pBase,
  Map<String, String> pOurs,
  Map<String, String> pTheirs,
) {
  final rTree = <String, String>{};
  final rConflicts = <String, Map<String, String?>>{};

  for (final vFile in sortedOf({...pBase.keys, ...pOurs.keys, ...pTheirs.keys})) {
    final vBase = pBase[vFile];
    final vOurs = pOurs[vFile];
    final vTheirs = pTheirs[vFile];
    String? vValue;

    if (vTheirs == vOurs || vTheirs == vBase) {
      vValue = vOurs;
    } else if (vOurs == vBase) {
      vValue = vTheirs;
    } else {
      rConflicts[vFile] = {'ours': vOurs, 'theirs': vTheirs};
      vValue = vOurs;
    }

    if (vValue != null) {
      rTree[vFile] = vValue;
    }
  }

  return (rTree, rConflicts);
}

void checkOverwrite(Repository pRepository, Map<String, String> pTree,
    Map<String, Object?> pConflicts, String pAction) {
  final vHead = pRepository.headTree();
  final vTouched = sortedOf(
    pRepository.changes.keys
        .where((pFile) => pTree[pFile] != vHead[pFile] || pConflicts.containsKey(pFile)),
  );

  if (vTouched.isNotEmpty) {
    throw GitError(
      'Vos modifications locales de ${vTouched.join(', ')} seraient écrasées par $pAction. '
      'Validez-les (git commit) ou mettez-les de côté (git stash)',
    );
  }
}

void requireClean(Repository pRepository, String pAction) {
  if (pRepository.changes.isNotEmpty) {
    throw GitError(
      'Impossible de lancer $pAction : modifications non validées '
      '(${sortedOf(pRepository.changes.keys).join(', ')}). Validez-les ou mettez-les de côté (git stash)',
    );
  }
}

String enterConflict(
  Repository pRepository,
  String pOperation,
  Map<String, Map<String, String?>> pConflicts,
  Map<String, String> pTree,
  Repository pSaved, [
  Map<String, dynamic> pExtra = const {},
]) {
  pRepository.conflict = {
    'operation': pOperation,
    'files': pConflicts,
    'resolved': <String, String>{},
    'tree': pTree,
    'saved': pSaved,
    ...pExtra,
  };

  for (final vFile in pConflicts.keys) {
    pRepository.changes[vFile] = markers;
    pRepository.staged.remove(vFile);
  }

  return 'CONFLIT dans ${sortedOf(pConflicts.keys).join(', ')} : corrigez (modifier, '
      'git checkout --ours ou --theirs), puis ${operationHints[pOperation]}';
}

Map<String, Map<String, String?>> conflictFiles(Repository pRepository) =>
    pRepository.conflict!['files'] as Map<String, Map<String, String?>>;

Map<String, String> conflictResolved(Repository pRepository) =>
    pRepository.conflict!['resolved'] as Map<String, String>;

List<String> getUnresolved(Repository pRepository) => sortedOf(conflictFiles(pRepository)
    .keys
    .where((pFile) => !conflictResolved(pRepository).containsKey(pFile)));

Map<String, String> closeConflict(Repository pRepository) {
  final vConflict = pRepository.conflict!;
  final rTree = {...vConflict['tree'] as Map<String, String>, ...conflictResolved(pRepository)};

  for (final vFile in conflictFiles(pRepository).keys) {
    pRepository.changes.remove(vFile);
    pRepository.staged.remove(vFile);
  }

  pRepository.conflict = null;

  return rTree;
}

void checkBranchName(Repository pRepository, String pName, bool pMustExist) {
  if (pMustExist) {
    if (!pRepository.branches.containsKey(pName)) {
      throw GitError("La branche $pName n'existe pas");
    }

    return;
  }

  if (!branchPattern.hasMatch(pName) ||
      pName.toUpperCase() == 'HEAD' ||
      commitPattern.hasMatch(pName) ||
      pName.startsWith('$remoteName/')) {
    throw GitError(
      'Nom de branche invalide : $pName (lettres, chiffres, . _ / -, 30 caractères au plus, '
      "différent d'un identifiant de commit et sans $remoteName/ au début)",
    );
  }

  if (pRepository.branches.containsKey(pName)) {
    throw GitError('La branche $pName existe déjà');
  }
}

void checkFileName(String pName) {
  if (!filePattern.hasMatch(pName) || pName.contains('..')) {
    throw GitError('Nom de fichier invalide : $pName');
  }
}

(List<String>, List<String>) splitOptions(List<String> pArguments) => (
      [
        for (final vArgument in pArguments)
          if (vArgument.startsWith('-')) vArgument
      ],
      [
        for (final vArgument in pArguments)
          if (!vArgument.startsWith('-')) vArgument
      ],
    );

void expectValues(List<String> pValues, int pMinimum, int pMaximum, String pUsage) {
  if (pValues.length < pMinimum || pValues.length > pMaximum) {
    throw GitError('Usage : $pUsage');
  }
}
