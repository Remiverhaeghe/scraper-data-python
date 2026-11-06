// Échanges avec le serveur origin : réécriture de job/git_remote.py.

import 'git_history.dart';
import 'git_repository.dart';

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
