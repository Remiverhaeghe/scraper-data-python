// Bac à sable Git, hors ligne : même dépôt simulé que job/git_sandbox.py (commits,
// branches, fichiers, index, remise, conflits, serveur origin), mêmes messages,
// gardés identiques par les cas de tests/fixtures/shared_lab_cases.json.

const maxCommandLength = 120;
const maxHistory = 60;
const remoteName = 'origin';
const setupPrefix = '@';
const editCommand = 'modifier';
const markers = 'marqueurs';

final branchPattern = RegExp(r"^[A-Za-z][A-Za-z0-9._/-]{0,29}$");
final commitPattern = RegExp(r"^C\d+'*$", caseSensitive: false);
final referencePattern = RegExp(r"^(?<base>[A-Za-z0-9._/'-]+?)(?<moves>(?:[\^~]\d*)*)$");
final movePattern = RegExp(r'([\^~])(\d*)');
final filePattern = RegExp(r'^[\p{L}\p{N}\p{M}_-][\p{L}\p{N}\p{M}_./-]{0,39}$', unicode: true);
final stashPattern = RegExp(r'^stash@\{(\d+)\}$');

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
const conflictCommands = ['status', 'add', 'restore', 'diff', 'log', 'commit'];

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

String runEdit(Repository pRepository, String pFile) {
  checkFileName(pFile);
  final vConflict = pRepository.conflict;

  if (vConflict != null && conflictFiles(pRepository).containsKey(pFile)) {
    final vSides = conflictFiles(pRepository)[pFile]!;

    pRepository.changes[pFile] = [vSides['ours'], vSides['theirs']]
        .where((pSide) => pSide != null && pSide.isNotEmpty)
        .join('+');

    return '$pFile corrigé à la main : les deux modifications sont gardées';
  }

  final vCurrent = pRepository.workingTree()[pFile];
  final vKnown = vCurrent != null && vCurrent.isNotEmpty;

  pRepository.changes[pFile] = vKnown ? '$vCurrent+modif' : 'nouveau';

  return '$pFile modifié${vKnown ? '' : ' (nouveau fichier)'}';
}

String runAdd(Repository pRepository, List<String> pArguments) {
  final (vOptions, vValues) = splitOptions(pArguments);
  final vAll = vValues.contains('.') || vOptions.contains('-A') || vOptions.contains('--all');

  if (!vAll) {
    expectValues(vValues, 1, 10, 'git add <fichier>… ou git add .');
  }

  final vFiles = vAll ? sortedOf(pRepository.changes.keys) : vValues;

  for (final vFile in vFiles) {
    if (!pRepository.changes.containsKey(vFile)) {
      throw GitError('Aucune modification de $vFile à indexer');
    }
  }

  final vConflict = pRepository.conflict;
  final vMarkers = <String>[];

  for (final vFile in vFiles) {
    pRepository.staged.add(vFile);

    if (vConflict != null && conflictFiles(pRepository).containsKey(vFile)) {
      conflictResolved(pRepository)[vFile] = pRepository.changes[vFile]!;
    }

    if (pRepository.changes[vFile] == markers) {
      vMarkers.add(vFile);
    }
  }

  var rMessage = vFiles.isNotEmpty ? 'Indexé : ${vFiles.join(', ')}' : 'Rien à indexer';

  if (vMarkers.isNotEmpty) {
    rMessage +=
        '. Attention : ${vMarkers.join(', ')} contient encore les marqueurs <<<<<<< ======= >>>>>>>';
  }

  if (vConflict != null &&
      vConflict['operation'] == 'stash' &&
      getUnresolved(pRepository).isEmpty) {
    final vTree = {...vConflict['tree'] as Map<String, String>, ...conflictResolved(pRepository)};

    pRepository.conflict = null;
    pRepository.changes.addAll(vTree);
    rMessage += '. Conflit résolu ; la remise reste dans la liste (git stash drop)';
  }

  return rMessage;
}

String runRestore(Repository pRepository, List<String> pArguments) {
  final (vOptions, vValues) = splitOptions(pArguments);

  expectValues(vValues, 1, 10, 'git restore [--staged] <fichier>…');

  for (final vFile in vValues) {
    if (!pRepository.changes.containsKey(vFile)) {
      throw GitError('Aucune modification de $vFile');
    }

    if (pRepository.conflict != null && conflictFiles(pRepository).containsKey(vFile)) {
      throw GitError('$vFile est en conflit : modifiez-le, ou git checkout --ours ou --theirs');
    }
  }

  for (final vFile in vValues) {
    pRepository.staged.remove(vFile);

    if (!vOptions.contains('--staged')) {
      pRepository.changes.remove(vFile);
    }
  }

  return (vOptions.contains('--staged') ? "Retiré de l'index : " : 'Modification annulée : ') +
      vValues.join(', ');
}

String runCommit(Repository pRepository, List<String> pArguments) {
  final (vOptions, _) = splitOptions(pArguments);
  final vConflict = pRepository.conflict;

  if (vConflict != null) {
    final vOperation = vConflict['operation'] as String;

    if (vOperation != 'merge') {
      throw GitError('${operationLabels[vOperation]} en cours : ${operationHints[vOperation]}');
    }

    final vMissing = getUnresolved(pRepository);

    if (vMissing.isNotEmpty) {
      throw GitError(
          'Impossible de valider : ${vMissing.join(', ')} encore en conflit (git add après correction)');
    }

    final vParents = List<String>.from(vConflict['parents'] as List);
    final vTree = closeConflict(pRepository);
    final vCommit = pRepository.addCommit(vParents, 'merge', '', vTree);

    pRepository.moveHead(vCommit);

    return 'Commit de fusion $vCommit créé'
        '${vTree.values.contains(markers) ? ' ; attention, un fichier contient encore les marqueurs de conflit' : ''}';
  }

  if (vOptions.contains('-a')) {
    pRepository.staged.addAll(pRepository.changes.keys);
  }

  if (pRepository.changes.isNotEmpty && pRepository.staged.isEmpty) {
    throw GitError("Aucune modification indexée : git add <fichier> d'abord, ou git commit -a");
  }

  final vHead = pRepository.headCommit();
  final vFiles = sortedOf(pRepository.staged);
  final vStaged = {for (final vFile in vFiles) vFile: pRepository.changes.remove(vFile)!};

  pRepository.staged = {};

  if (vOptions.contains('--amend')) {
    if (pRepository.commits[vHead]!.parents.isEmpty) {
      throw GitError('Le premier commit ne peut pas être modifié');
    }

    final vCommit = pRepository.addCommit(
      pRepository.commits[vHead]!.parents,
      'copy',
      vHead,
      {...pRepository.tree(vHead), ...vStaged},
    );

    pRepository.moveHead(vCommit);

    return 'Commit $vHead remplacé par $vCommit';
  }

  final vCommit =
      pRepository.addCommit([vHead], 'commit', '', {...pRepository.tree(vHead), ...vStaged});

  pRepository.moveHead(vCommit);

  return 'Commit $vCommit enregistré${vFiles.isNotEmpty ? ' (${vFiles.join(', ')})' : ''}';
}

String runBranch(Repository pRepository, List<String> pArguments) {
  final (vOptions, vValues) = splitOptions(pArguments);

  if (vOptions.isNotEmpty && ['-d', '-D', '--delete'].contains(vOptions.first)) {
    expectValues(vValues, 1, 1, 'git branch -d <nom>');
    checkBranchName(pRepository, vValues.first, true);

    if (!pRepository.detached && pRepository.head == vValues.first) {
      throw GitError("Impossible de supprimer ${vValues.first} : HEAD s'y trouve");
    }

    pRepository.branches.remove(vValues.first);

    return 'Branche ${vValues.first} supprimée';
  }

  if (vOptions.isNotEmpty && ['-f', '--force'].contains(vOptions.first)) {
    expectValues(vValues, 2, 2, 'git branch -f <nom> <réf>');
    checkBranchName(pRepository, vValues.first, true);

    if (!pRepository.detached && pRepository.head == vValues.first) {
      throw GitError("Impossible de forcer ${vValues.first} : HEAD s'y trouve (git reset)");
    }

    pRepository.branches[vValues.first] = pRepository.resolve(vValues[1]);

    return 'Branche ${vValues.first} déplacée sur ${pRepository.branches[vValues.first]}';
  }

  if (vOptions.isNotEmpty) {
    throw GitError('Option non prise en charge : ${vOptions.first}');
  }

  if (vValues.isEmpty) {
    return 'Branches : ${sortedOf(pRepository.branches.keys).join(', ')}';
  }

  expectValues(vValues, 1, 2, 'git branch <nom> [<réf>]');
  checkBranchName(pRepository, vValues.first, false);

  final vCommit = pRepository.resolve(vValues.length == 2 ? vValues[1] : 'HEAD');

  pRepository.branches[vValues.first] = vCommit;

  return 'Branche ${vValues.first} créée sur $vCommit';
}

String placeHead(Repository pRepository, String pReference, [bool pDetach = false]) {
  final vTarget = pRepository.resolve(pReference);

  checkOverwrite(pRepository, pRepository.tree(vTarget), const {}, 'le changement de branche');

  if (pRepository.branches.containsKey(pReference) && !pDetach) {
    pRepository
      ..head = pReference
      ..detached = false;

    return 'Sur la branche $pReference';
  }

  pRepository
    ..head = vTarget
    ..detached = true;

  return 'HEAD détaché sur ${pRepository.head}';
}

String takeSide(Repository pRepository, String pOption, List<String> pFiles) {
  if (pRepository.conflict == null) {
    throw GitError('$pOption ne sert que pendant un conflit');
  }

  expectValues(pFiles, 1, 10, 'git checkout $pOption <fichier>');
  final vSide = pOption == '--ours' ? 'ours' : 'theirs';

  for (final vFile in pFiles) {
    if (!conflictFiles(pRepository).containsKey(vFile)) {
      throw GitError("$vFile n'est pas en conflit");
    }

    final vVersion = conflictFiles(pRepository)[vFile]![vSide];

    if (vVersion == null) {
      throw GitError('$vFile est supprimé de ce côté');
    }

    pRepository.changes[vFile] = vVersion;
  }

  return '${pFiles.join(', ')} : '
      '${vSide == 'ours' ? 'version de la branche courante gardée' : "version de l'autre côté gardée"}';
}

String runSwitch(Repository pRepository, List<String> pArguments, String pCreateOption) {
  var (vOptions, vValues) = splitOptions(pArguments);

  vOptions = [
    for (final vOption in vOptions)
      if (vOption != '--') vOption
  ];

  if (vOptions.isNotEmpty &&
      ['--ours', '--theirs'].contains(vOptions.first) &&
      pCreateOption == '-b') {
    return takeSide(pRepository, vOptions.first, vValues);
  }

  if (vOptions.isNotEmpty && [pCreateOption, '--create'].contains(vOptions.first)) {
    expectValues(vValues, 1, 2, 'git … $pCreateOption <nom> [<réf>]');
    runBranch(pRepository, vValues);

    return placeHead(pRepository, vValues.first);
  }

  if (vOptions.isNotEmpty && vOptions.first != '--detach') {
    throw GitError('Option non prise en charge : ${vOptions.first}');
  }

  expectValues(vValues, 1, 1, 'git switch <branche>');

  if (pCreateOption == '-c' &&
      vOptions.isEmpty &&
      !pRepository.branches.containsKey(vValues.first)) {
    throw GitError(
      "La branche ${vValues.first} n'existe pas : git switch -c pour la créer, "
      'ou --detach pour se placer sur un commit',
    );
  }

  return placeHead(pRepository, vValues.first, vOptions.isNotEmpty);
}

String runMerge(Repository pRepository, List<String> pArguments) {
  final (vOptions, vValues) = splitOptions(pArguments);

  if (vOptions.contains('--abort')) {
    return abortOperation(pRepository, 'merge');
  }

  expectValues(vValues, 1, 1, 'git merge <réf>');

  final vTarget = pRepository.resolve(vValues.first);
  final vHead = pRepository.headCommit();

  if (pRepository.ancestors(vHead).contains(vTarget)) {
    return 'Déjà à jour';
  }

  if (pRepository.ancestors(vTarget).contains(vHead)) {
    checkOverwrite(pRepository, pRepository.tree(vTarget), const {}, 'la fusion');
    pRepository.moveHead(vTarget);

    return "Avance rapide jusqu'à $vTarget";
  }

  final (vTree, vConflicts) = threeWay(
    pRepository.tree(pRepository.mergeBase(vHead, vTarget)),
    pRepository.tree(vHead),
    pRepository.tree(vTarget),
  );

  checkOverwrite(pRepository, vTree, vConflicts, 'la fusion');

  if (vConflicts.isNotEmpty) {
    return 'Fusion automatique impossible. '
        '${enterConflict(pRepository, 'merge', vConflicts, vTree, pRepository.copy(), {
          'parents': [vHead, vTarget],
        })}';
  }

  final vCommit = pRepository.addCommit([vHead, vTarget], 'merge', '', vTree);

  pRepository.moveHead(vCommit);

  return 'Commit de fusion $vCommit créé';
}

/// Recopie des commits un à un ; (copies faites, message de conflit ou vide).
(List<String>, String) playSequence(
  Repository pRepository,
  String pOperation,
  List<String> pTodo,
  String pTip,
  Repository pSaved,
  String? pBranch,
) {
  final vTodo = List.of(pTodo);
  var vTip = pTip;
  final vCopies = <String>[];

  while (vTodo.isNotEmpty) {
    final vCommit = vTodo.removeAt(0);
    final vParents = pRepository.commits[vCommit]!.parents;
    final (vTree, vConflicts) = threeWay(
      vParents.isEmpty ? {} : pRepository.tree(vParents.first),
      pRepository.tree(vTip),
      pRepository.tree(vCommit),
    );

    if (vConflicts.isNotEmpty) {
      if (pOperation == 'rebase') {
        pRepository
          ..head = vTip
          ..detached = true;
      } else {
        pRepository.moveHead(vTip);
      }

      return (
        vCopies,
        'Arrêt sur $vCommit. ${enterConflict(pRepository, pOperation, vConflicts, vTree, pSaved, {
              'current': vCommit,
              'todo': vTodo,
              'tip': vTip,
              'branch': pBranch,
            })}',
      );
    }

    vTip = pRepository.addCommit([vTip], 'copy', vCommit, vTree);
    vCopies.add(vTip);
  }

  if (pOperation == 'rebase' && pBranch != null) {
    pRepository.branches[pBranch] = vTip;
    pRepository
      ..head = pBranch
      ..detached = false;
  } else if (pOperation == 'rebase') {
    pRepository
      ..head = vTip
      ..detached = true;
  } else {
    pRepository.moveHead(vTip);
  }

  return (vCopies, '');
}

String describeSequence(String pOperation, List<String> pCopies, String pMessage,
    [String pBase = '']) {
  if (pMessage.isNotEmpty) {
    return '${pCopies.isNotEmpty ? '${pCopies.length} commit(s) recopié(s). ' : ''}$pMessage';
  }

  if (pOperation == 'rebase') {
    return '${pCopies.length} commit(s) rejoué(s)${pBase.isNotEmpty ? ' sur $pBase' : ''}';
  }

  return 'Commit(s) recopié(s) : ${pCopies.join(', ')}';
}

String continueOperation(Repository pRepository, String pOperation, [bool pSkip = false]) {
  final vConflict = pRepository.conflict;

  if (vConflict == null || vConflict['operation'] != pOperation) {
    throw GitError('Aucun $pOperation en cours');
  }

  if (!pSkip && getUnresolved(pRepository).isNotEmpty) {
    throw GitError(
        '${getUnresolved(pRepository).join(', ')} encore en conflit (git add après correction)');
  }

  var vTip = vConflict['tip'] as String;
  final vCurrent = vConflict['current'] as String;
  final vTodo = List<String>.from(vConflict['todo'] as List);
  final vSaved = vConflict['saved'] as Repository;
  final vBranch = vConflict['branch'] as String?;
  final vTree = closeConflict(pRepository);
  final vCopies = <String>[];

  if (!pSkip) {
    vTip = pRepository.addCommit([vTip], 'copy', vCurrent, vTree);
    vCopies.add(vTip);
  }

  final (vMore, vMessage) = playSequence(pRepository, pOperation, vTodo, vTip, vSaved, vBranch);

  return describeSequence(pOperation, [...vCopies, ...vMore], vMessage);
}

String abortOperation(Repository pRepository, String pOperation) {
  final vConflict = pRepository.conflict;

  if (vConflict == null || vConflict['operation'] != pOperation) {
    throw GitError('Aucun $pOperation en cours à abandonner');
  }

  pRepository.restoreFrom(vConflict['saved'] as Repository);

  return "${operationLabels[pOperation]} abandonné(e) : retour à l'état d'avant";
}

String runRebase(Repository pRepository, List<String> pArguments) {
  final (vOptions, vValues) = splitOptions(pArguments);

  if (vOptions.contains('--continue') || vOptions.contains('--skip')) {
    return continueOperation(pRepository, 'rebase', vOptions.contains('--skip'));
  }

  if (vOptions.contains('--abort')) {
    return abortOperation(pRepository, 'rebase');
  }

  expectValues(vValues, 1, 1, 'git rebase <réf>');
  requireClean(pRepository, 'un rebase');

  final vBase = pRepository.resolve(vValues.first);
  final vHead = pRepository.headCommit();
  final vBaseAncestors = pRepository.ancestors(vBase);

  if (vBaseAncestors.contains(vHead)) {
    pRepository.moveHead(vBase);

    return "Avance rapide jusqu'à $vBase";
  }

  if (pRepository.ancestors(vHead).contains(vBase)) {
    return 'Déjà à jour';
  }

  // Comme git : les fusions ne sont pas rejouées, ni un commit déjà recopié sur la base.
  final vUpstreamOrigins = {for (final vCommit in vBaseAncestors) pRepository.rootOrigin(vCommit)};
  final vOwnCommits = pRepository.ancestors(vHead).difference(vBaseAncestors);
  final vToCopy = [
    for (final vEntry in pRepository.commits.entries)
      if (vOwnCommits.contains(vEntry.key) &&
          vEntry.value.kind != 'merge' &&
          !vUpstreamOrigins.contains(pRepository.rootOrigin(vEntry.key)))
        vEntry.key,
  ];

  final (vCopies, vMessage) = playSequence(
    pRepository,
    'rebase',
    vToCopy,
    vBase,
    pRepository.copy(),
    pRepository.detached ? null : pRepository.head,
  );

  return describeSequence('rebase', vCopies, vMessage, vBase);
}

String runReset(Repository pRepository, List<String> pArguments) {
  final (vOptions, vValues) = splitOptions(pArguments);

  for (final vOption in vOptions) {
    if (!['--hard', '--soft', '--mixed'].contains(vOption)) {
      throw GitError('Option non prise en charge : $vOption');
    }
  }

  expectValues(vValues, 1, 1, 'git reset <réf>');

  final vCommit = pRepository.resolve(vValues.first);
  final vWorking = pRepository.workingTree();

  pRepository.moveHead(vCommit);

  if (vOptions.contains('--hard')) {
    pRepository
      ..changes = {}
      ..staged = {};
  } else {
    final vTree = pRepository.tree(vCommit);

    pRepository.changes = {
      for (final vEntry in vWorking.entries)
        if (vTree[vEntry.key] != vEntry.value) vEntry.key: vEntry.value,
    };
    pRepository.staged = vOptions.contains('--soft') ? {...pRepository.changes.keys} : {};
  }

  return 'HEAD ramené sur $vCommit';
}

String runRevert(Repository pRepository, List<String> pArguments) {
  final (_, vValues) = splitOptions(pArguments);

  expectValues(vValues, 1, 1, 'git revert <réf>');

  final vTarget = pRepository.resolve(vValues.first);
  final vParents = pRepository.commits[vTarget]!.parents;

  if (vParents.isEmpty) {
    throw GitError('Le premier commit ne peut pas être annulé');
  }

  final (vTree, vConflicts) = threeWay(
    pRepository.tree(vTarget),
    pRepository.headTree(),
    pRepository.tree(vParents.first),
  );

  if (vConflicts.isNotEmpty) {
    throw GitError(
      "L'annulation de $vTarget entre en conflit avec des modifications plus récentes : non simulé ici",
    );
  }

  checkOverwrite(pRepository, vTree, const {}, "l'annulation");

  final vCommit = pRepository.addCommit([pRepository.headCommit()], 'revert', vTarget, vTree);

  pRepository.moveHead(vCommit);

  return 'Commit $vCommit : annulation de $vTarget';
}

String runCherryPick(Repository pRepository, List<String> pArguments) {
  final (vOptions, vValues) = splitOptions(pArguments);

  if (vOptions.contains('--continue')) {
    return continueOperation(pRepository, 'cherry-pick');
  }

  if (vOptions.contains('--abort')) {
    return abortOperation(pRepository, 'cherry-pick');
  }

  expectValues(vValues, 1, 10, 'git cherry-pick <réf>…');
  requireClean(pRepository, 'un cherry-pick');

  final vTargets = [for (final vValue in vValues) pRepository.resolve(vValue)];
  final vHeadAncestors = pRepository.ancestors(pRepository.headCommit());

  for (final vTarget in vTargets) {
    if (vHeadAncestors.contains(vTarget)) {
      throw GitError('$vTarget est déjà présent sous HEAD');
    }

    if (pRepository.commits[vTarget]!.kind == 'merge') {
      throw GitError('$vTarget est une fusion : non pris en charge');
    }
  }

  final (vCopies, vMessage) = playSequence(
    pRepository,
    'cherry-pick',
    vTargets,
    pRepository.headCommit(),
    pRepository.copy(),
    null,
  );

  return describeSequence('cherry-pick', vCopies, vMessage);
}

String runStash(Repository pRepository, List<String> pArguments) {
  final (_, vValues) = splitOptions(pArguments);
  final vAction = vValues.isEmpty ? 'push' : vValues.first;
  final vStash = pRepository.stash;

  if (vAction == 'push' || vAction == 'save') {
    if (pRepository.changes.isEmpty) {
      return 'Aucune modification à mettre de côté';
    }

    final vHead = pRepository.headTree();

    vStash.insert(0, {
      'changes': {...pRepository.changes},
      'base': <String, String?>{for (final vFile in pRepository.changes.keys) vFile: vHead[vFile]},
      'where': pRepository.head,
    });

    final vFiles = sortedOf(pRepository.changes.keys).join(', ');

    pRepository
      ..changes = {}
      ..staged = {};

    return 'Modifications mises de côté dans stash@{0} : $vFiles';
  }

  if (vAction == 'list') {
    final vText = [
      for (final (vIndex, vEntry) in vStash.indexed)
        'stash@{$vIndex} : sur ${vEntry['where']}, '
            '${sortedOf((vEntry['changes'] as Map<String, String>).keys).join(', ')}',
    ].join(' · ');

    return vText.isEmpty ? 'Remise vide' : vText;
  }

  var vIndex = 0;

  if (vValues.length == 2) {
    final vMatch = stashPattern.firstMatch(vValues[1]);

    if (vMatch == null) {
      throw GitError('Désignez une entrée comme stash@{0}');
    }

    vIndex = int.parse(vMatch.group(1)!);
  }

  if (vIndex >= vStash.length) {
    throw GitError(vStash.isNotEmpty ? "Cette entrée de la remise n'existe pas" : 'Remise vide');
  }

  if (vAction == 'drop') {
    vStash.removeAt(vIndex);

    return 'stash@{$vIndex} supprimée';
  }

  if (vAction != 'pop' && vAction != 'apply') {
    throw GitError('Usage : git stash [push | pop | apply | list | drop]');
  }

  final vEntry = vStash[vIndex];
  final vChanges = vEntry['changes'] as Map<String, String>;
  final vOverlap = sortedOf(vChanges.keys.where(pRepository.changes.containsKey));

  if (vOverlap.isNotEmpty) {
    throw GitError(
      'Vos modifications locales de ${vOverlap.join(', ')} seraient écrasées : '
      'validez-les ou mettez-les aussi de côté',
    );
  }

  final vSaved = pRepository.copy();
  final vHead = pRepository.headTree();
  final vConflicts = <String, Map<String, String?>>{};

  for (final vChange in vChanges.entries) {
    final vCurrent = vHead[vChange.key];

    if (vCurrent == (vEntry['base'] as Map<String, String?>)[vChange.key]) {
      pRepository.changes[vChange.key] = vChange.value;
    } else if (vCurrent != vChange.value) {
      vConflicts[vChange.key] = {'ours': vCurrent, 'theirs': vChange.value};
    }
  }

  if (vConflicts.isNotEmpty) {
    return '${enterConflict(pRepository, 'stash', vConflicts, {}, vSaved)}. La remise est conservée';
  }

  if (vAction == 'pop') {
    vStash.removeAt(vIndex);
  }

  return 'Modifications réappliquées : ${sortedOf(vChanges.keys).join(', ')}';
}

/// État du répertoire de travail, ligne par ligne, pour l'affichage.
List<String> describeWorktree(Repository pRepository) {
  final rLines = <String>[];
  final vConflict = pRepository.conflict;

  if (vConflict != null) {
    rLines.add(
      '${operationLabels[vConflict['operation']]} en cours, conflit dans '
      '${sortedOf(conflictFiles(pRepository).keys).map((pFile) => '$pFile (${conflictResolved(pRepository).containsKey(pFile) ? 'résolu' : 'à résoudre'})').join(', ')}',
    );
  }

  final vStaged = sortedOf(pRepository.staged);
  final vModified =
      sortedOf(pRepository.changes.keys.where((pFile) => !pRepository.staged.contains(pFile)));

  if (vStaged.isNotEmpty) {
    rLines.add('Indexé : ${vStaged.join(', ')}');
  }

  if (vModified.isNotEmpty) {
    rLines.add('Modifié, non indexé : ${vModified.join(', ')}');
  }

  if (pRepository.stash.isNotEmpty) {
    rLines.add('Remise : ${pRepository.stash.length} entrée(s)');
  }

  return rLines;
}

String runStatus(Repository pRepository, List<String> pArguments) {
  expectValues(pArguments, 0, 0, 'git status');

  final vPosition = pRepository.detached
      ? 'HEAD détaché sur ${pRepository.head}'
      : 'Sur la branche ${pRepository.head}, commit ${pRepository.branches[pRepository.head]}';
  var rMessage = [vPosition, ...describeWorktree(pRepository)].join(' · ');

  if (pRepository.conflict != null) {
    rMessage += ' · Pour finir : ${operationHints[pRepository.conflict!['operation']]}';
  }

  return rMessage;
}

String runDiff(Repository pRepository, List<String> pArguments) {
  expectValues(splitOptions(pArguments).$2, 0, 1, 'git diff [--staged]');

  final vLines = describeWorktree(pRepository);
  final vText = vLines.sublist(vLines.length > 3 ? vLines.length - 3 : 0).join(' · ');

  return vText.isEmpty ? 'Aucune modification' : vText;
}

String runLog(Repository pRepository, List<String> pArguments) {
  expectValues(splitOptions(pArguments).$2, 0, 1, 'git log [--oneline]');

  final vAncestors = pRepository.ancestors(pRepository.headCommit());
  final vLines = <String>[];

  for (final vCommit in pRepository.commits.keys.toList().reversed) {
    if (!vAncestors.contains(vCommit)) {
      continue;
    }

    final vData = pRepository.commits[vCommit]!;
    final vBefore =
        vData.parents.isEmpty ? <String, String>{} : pRepository.tree(vData.parents.first);
    final vChanged = [
      for (final vEntry in vData.tree.entries)
        if (vBefore[vEntry.key] != vEntry.value) '${vEntry.key}=${vEntry.value}',
    ];

    vLines.add(vCommit + (vChanged.isEmpty ? '' : ' (${vChanged.join(', ')})'));
  }

  return vLines.take(12).join(' · ');
}

void requireRemote(Repository pRepository) {
  if (pRepository.remote.isEmpty) {
    throw GitError('Aucun dépôt distant $remoteName dans ce niveau');
  }
}

String runFetch(Repository pRepository, List<String> pArguments) {
  requireRemote(pRepository);
  expectValues(splitOptions(pArguments).$2, 0, 1, 'git fetch [origin]');

  final vBefore = {...pRepository.tracking};
  final vCount = pRepository.unknown.length;

  pRepository.tracking = {
    for (final vEntry in pRepository.remote.entries) '$remoteName/${vEntry.key}': vEntry.value,
  };
  pRepository.unknown = {};

  final vSame = vBefore.length == pRepository.tracking.length &&
      vBefore.entries.every((pEntry) => pRepository.tracking[pEntry.key] == pEntry.value);

  return vSame ? 'Déjà à jour' : '$vCount commit(s) récupéré(s) du serveur';
}

String runPull(Repository pRepository, List<String> pArguments) {
  final (vOptions, _) = splitOptions(pArguments);

  if (pRepository.detached) {
    throw GitError("HEAD détaché : placez-vous d'abord sur une branche");
  }

  final vFetch = runFetch(pRepository, []);
  final vTracked = '$remoteName/${pRepository.head}';

  if (!pRepository.tracking.containsKey(vTracked)) {
    throw GitError("$vTracked n'existe pas sur le serveur");
  }

  final vIntegrate = vOptions.contains('--rebase') ? runRebase : runMerge;

  return '$vFetch. ${vIntegrate(pRepository, [vTracked])}';
}

String runPush(Repository pRepository, List<String> pArguments) {
  requireRemote(pRepository);
  final (_, vValues) = splitOptions(pArguments);

  expectValues(vValues, 0, 2, 'git push [origin [<branche>]]');

  if (vValues.isNotEmpty && vValues.first != remoteName) {
    throw GitError('Dépôt distant inconnu : ${vValues.first}');
  }

  final String vBranch;

  if (vValues.length == 2) {
    vBranch = vValues[1];
  } else if (pRepository.detached) {
    throw GitError('HEAD détaché : précisez la branche à envoyer');
  } else {
    vBranch = pRepository.head;
  }

  checkBranchName(pRepository, vBranch, true);

  final vCommit = pRepository.branches[vBranch]!;
  final vServer = pRepository.remote[vBranch];

  if (vServer == vCommit) {
    return 'Déjà à jour';
  }

  if (vServer != null && !pRepository.ancestors(vCommit).contains(vServer)) {
    throw GitError(
      "Envoi refusé : le serveur contient des commits que vous n'avez pas. Récupérez-les d'abord (git pull)",
    );
  }

  pRepository.remote[vBranch] = vCommit;
  pRepository.tracking['$remoteName/$vBranch'] = vCommit;

  return '$vBranch envoyée : $remoteName/$vBranch sur $vCommit';
}

Map<String, String> readFiles(List<String> pWords) {
  final rFiles = <String, String>{};

  for (final vWord in pWords) {
    final vSeparator = vWord.indexOf('=');

    if (vSeparator < 0 || vSeparator == vWord.length - 1) {
      throw GitError('Mise en place : fichier=étiquette attendu, pas $vWord');
    }

    final vFile = vWord.substring(0, vSeparator);

    checkFileName(vFile);
    rFiles[vFile] = vWord.substring(vSeparator + 1);
  }

  return rFiles;
}

bool isDigits(String pText) => RegExp(r'^\d+$').hasMatch(pText);

void runSetup(Repository pRepository, List<String> pWords) {
  if (pWords.length == 1 && pWords.first == '@clone') {
    pRepository.remote = {...pRepository.branches};
    pRepository.tracking = {
      for (final vEntry in pRepository.branches.entries) '$remoteName/${vEntry.key}': vEntry.value,
    };
  } else if (pWords.first == '@equipe' && pWords.length >= 2) {
    final vBranch = pWords[1];
    final vCount = pWords.length > 2 && isDigits(pWords[2]) ? int.parse(pWords[2]) : 1;
    final vFiles = readFiles([
      for (final vWord in pWords.skip(2))
        if (!isDigits(vWord)) vWord
    ]);
    var vParent = pRepository.remote[vBranch] ?? pRepository.remote['main']!;

    for (var vIndex = 0; vIndex < vCount; vIndex++) {
      vParent =
          pRepository.addCommit([vParent], 'commit', '', {...pRepository.tree(vParent), ...vFiles});
      pRepository.unknown.add(vParent);
    }

    pRepository.remote[vBranch] = vParent;
  } else if (pWords.first == '@commit' && pWords.length >= 2) {
    final vHead = pRepository.headCommit();
    final vCommit = pRepository.addCommit(
      [vHead],
      'commit',
      '',
      {...pRepository.tree(vHead), ...readFiles(pWords.sublist(1))},
    );

    pRepository.moveHead(vCommit);
  } else if (pWords.first == '@modifie' && pWords.length >= 2) {
    pRepository.changes.addAll(readFiles(pWords.sublist(1)));
  } else {
    throw GitError('Mise en place inconnue : ${pWords.join(' ')}');
  }
}

final commands = <String, String Function(Repository, List<String>)>{
  'add': runAdd,
  'restore': runRestore,
  'commit': runCommit,
  'branch': runBranch,
  'switch': (pRepository, pArguments) => runSwitch(pRepository, pArguments, '-c'),
  'checkout': (pRepository, pArguments) => runSwitch(pRepository, pArguments, '-b'),
  'merge': runMerge,
  'rebase': runRebase,
  'reset': runReset,
  'revert': runRevert,
  'cherry-pick': runCherryPick,
  'stash': runStash,
  'status': runStatus,
  'diff': runDiff,
  'log': runLog,
  'fetch': runFetch,
  'pull': runPull,
  'push': runPush,
};

/// Options utiles de git commit : le message n'a pas d'effet ici.
List<String> readCommitOptions(List<String> pArguments) => [
      for (final vArgument in pArguments)
        if (vArgument == '--amend' || vArgument == '-a')
          vArgument
        else if (vArgument == '--all' || RegExp(r'^-[a-z]*a[a-z]*$').hasMatch(vArgument))
          '-a',
    ];

void checkConflictCommand(Repository pRepository, String pAction, List<String> pArguments) {
  final vConflict = pRepository.conflict;

  if (vConflict == null) {
    return;
  }

  final vOptions = splitOptions(pArguments).$1.toSet();
  final vAllowed = conflictCommands.contains(pAction) ||
      (['merge', 'rebase', 'cherry-pick'].contains(pAction) &&
          vOptions.intersection({'--continue', '--skip', '--abort'}).isNotEmpty) ||
      (pAction == 'checkout' && vOptions.intersection({'--ours', '--theirs'}).isNotEmpty) ||
      (pAction == 'stash' && pArguments.isNotEmpty && pArguments.first == 'list');

  if (!vAllowed) {
    throw GitError(
        '${operationLabels[vConflict['operation']]} en cours : ${operationHints[vConflict['operation']]}');
  }
}

/// Découpe une commande comme shlex.split : guillemets simples et doubles, \ d'échappement.
List<String> splitCommand(String pCommand) {
  final rWords = <String>[];
  final vWord = StringBuffer();
  var vInWord = false;
  var vIndex = 0;

  while (vIndex < pCommand.length) {
    final vChar = pCommand[vIndex];

    if (vChar == "'" || vChar == '"') {
      final vEnd = vChar == "'" ? pCommand.indexOf("'", vIndex + 1) : -1;

      vInWord = true;

      if (vChar == "'") {
        if (vEnd < 0) {
          throw GitError('Guillemet non refermé');
        }

        vWord.write(pCommand.substring(vIndex + 1, vEnd));
        vIndex = vEnd + 1;
        continue;
      }

      vIndex++;

      while (true) {
        if (vIndex >= pCommand.length) {
          throw GitError('Guillemet non refermé');
        }

        final vInner = pCommand[vIndex];

        if (vInner == '"') {
          vIndex++;
          break;
        }

        if (vInner == '\\' &&
            vIndex + 1 < pCommand.length &&
            '"\\'.contains(pCommand[vIndex + 1])) {
          vWord.write(pCommand[vIndex + 1]);
          vIndex += 2;
          continue;
        }

        vWord.write(vInner);
        vIndex++;
      }

      continue;
    }

    if (vChar == '\\') {
      if (vIndex + 1 >= pCommand.length) {
        throw GitError('Guillemet non refermé');
      }

      vWord.write(pCommand[vIndex + 1]);
      vInWord = true;
      vIndex += 2;
      continue;
    }

    if (' \t\r\n'.contains(vChar)) {
      if (vInWord) {
        rWords.add(vWord.toString());
        vWord.clear();
        vInWord = false;
      }

      vIndex++;
      continue;
    }

    vWord.write(vChar);
    vInWord = true;
    vIndex++;
  }

  if (vInWord) {
    rWords.add(vWord.toString());
  }

  return rWords;
}

/// Exécute une commande ; retourne le message, ou lève GitError sans rien modifier.
String runCommand(Repository pRepository, String pCommand, {bool pAllowSetup = false}) {
  if (pCommand.length > maxCommandLength) {
    throw GitError('Commande trop longue');
  }

  final vWords = splitCommand(pCommand);

  if (vWords.isEmpty) {
    throw GitError('Saisissez une commande');
  }

  if (pAllowSetup && vWords.first.startsWith(setupPrefix)) {
    runSetup(pRepository, vWords);

    return '';
  }

  final vBefore = pRepository.copy();

  try {
    if (vWords.first == editCommand) {
      expectValues(vWords.sublist(1), 1, 1, '$editCommand <fichier>');

      return runEdit(pRepository, vWords[1]);
    }

    if (vWords.first != 'git' || vWords.length < 2) {
      throw GitError(
          'Les commandes commencent par git (par exemple git commit), ou $editCommand <fichier>');
    }

    final vAction = commands[vWords[1]];

    if (vAction == null) {
      throw GitError('Commande non prise en charge : git ${vWords[1]}');
    }

    var vArguments = vWords.sublist(2);

    if (vWords[1] == 'commit') {
      vArguments = readCommitOptions(vArguments);
    }

    checkConflictCommand(pRepository, vWords[1], vArguments);

    return vAction(pRepository, vArguments);
  } on GitError {
    pRepository.restoreFrom(vBefore);
    rethrow;
  }
}

/// Dépôt obtenu en rejouant des commandes depuis un dépôt neuf.
Repository replay(List<String> pCommands) {
  final rRepository = Repository();

  for (final vCommand in pCommands) {
    runCommand(rRepository, vCommand, pAllowSetup: true);
  }

  return rRepository;
}
