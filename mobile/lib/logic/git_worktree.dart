// Commandes sur les fichiers, l'index et la remise : réécriture de
// job/git_worktree.py.

import 'git_repository.dart';

final stashPattern = RegExp(r'^stash@\{(\d+)\}$');

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
