// Commandes qui écrivent ou déplacent l'historique : réécriture de
// job/git_history.py.

import 'git_repository.dart';

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
