// Bac à sable Git, hors ligne : interprétation des commandes comme
// job/git_sandbox.py, mêmes messages, gardés identiques par les cas de
// tests/fixtures/shared_lab_cases.json.

import 'git_history.dart';
import 'git_remote.dart';
import 'git_repository.dart';
import 'git_worktree.dart';
import 'python_compat.dart';

const maxCommandLength = 120;
const maxHistory = 60;
const setupPrefix = '@';
const editCommand = 'modifier';
const conflictCommands = ['status', 'add', 'restore', 'diff', 'log', 'commit'];

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

/// Exécute une commande ; retourne le message, ou lève GitError sans rien modifier.
String runCommand(Repository pRepository, String pCommand, {bool pAllowSetup = false}) {
  if (pCommand.length > maxCommandLength) {
    throw GitError('Commande trop longue');
  }

  final List<String> vWords;

  try {
    vWords = splitCommand(pCommand);
  } on ShlexError {
    throw GitError('Guillemet non refermé');
  }

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
