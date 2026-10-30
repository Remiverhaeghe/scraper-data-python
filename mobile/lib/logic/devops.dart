// Niveaux Maven et Docker, hors ligne : objectif et étape de jeu identiques à
// job/devops_levels.py, pour les deux simulateurs.

import 'docker_sim.dart';
import 'maven_sim.dart';
import 'python_compat.dart';

const maxDevopsCommandLength = 300;
const maxDevopsFileLength = 8000;
const maxDevopsSteps = 100;
const fileNames = {'maven': 'pom.xml', 'docker': 'Dockerfile'};

/// (atteint, explication) de l'objectif d'un niveau Maven.
(bool, String) checkMavenGoal(Map pTarget, Map<String, dynamic> pReport) {
  if (pReport['success'] != true || pReport['phase'] == null) {
    return (false, '');
  }

  if (phases.indexOf(pReport['phase'] as String) < phases.indexOf(pTarget['phase'] as String)) {
    return (false, "Construction réussie, mais l'objectif demande mvn ${pTarget['phase']}.");
  }

  if (pReport['skipped_tests'] == true) {
    return (false, "Les tests ont été sautés : l'objectif demande qu'ils passent.");
  }

  if ((pReport['tests_run'] as int) < ((pTarget['tests_min'] as int?) ?? 0)) {
    return (
      false,
      '${pReport['tests_run']} test exécuté sur ${pTarget['tests_min']} : '
          'des tests existent mais ne sont pas lancés.',
    );
  }

  if (pTarget['jar'] != null &&
      (pTarget['jar'] as String).isNotEmpty &&
      pReport['jar'] != pTarget['jar']) {
    return (false, 'Le jar produit est ${pReport['jar']}, il faut ${pTarget['jar']}.');
  }

  final vScopes = pReport['scopes'] as Map;

  for (final vEntry in (pTarget['scopes'] as Map? ?? const {}).entries) {
    if (vScopes[vEntry.key] != vEntry.value) {
      return (
        false,
        'Construction réussie, mais ${(vEntry.key as String).split(':')[1]} est en scope '
            '${vScopes[vEntry.key] ?? 'absent'} : il faut ${vEntry.value}.',
      );
    }
  }

  return (true, '');
}

/// Simulateurs Maven et Docker, avec le contenu reçu du PC.
class DevopsLab {
  DevopsLab(Map<String, dynamic> pCentral, Map<String, dynamic> pRegistry)
      : maven = MavenSimulator(pCentral),
        docker = DockerSimulator(pRegistry);

  final MavenSimulator maven;
  final DockerSimulator docker;

  Map<String, dynamic> newHost(Map<String, dynamic> pLevel) =>
      docker.newHost(pLevel['setup'] as List? ?? const []);

  /// Joue une commande ; (lignes, objectif atteint, message). L'hôte Docker est modifié sur place.
  (List<String>, bool, String) playStep(
    Map<String, dynamic> pLevel,
    String pFile,
    String pCommand,
    Map<String, dynamic> pHost,
  ) {
    if (pLevel['tool'] == 'maven') {
      final (vLines, vReport) =
          maven.run(pLevel['project'] as Map<String, dynamic>, pFile, pCommand);
      final (vReached, vMessage) = checkMavenGoal(pLevel['target'] as Map, vReport);

      return (vLines, vReached, vMessage);
    }

    List<String> vLines;

    try {
      vLines = docker.run(pHost, pLevel, pFile, pCommand);
    } on DockerError catch (vError) {
      vLines = ['Error: ${vError.message}'];
    }

    return (vLines, isDockerGoalReached(pHost, pLevel['target'] as Map), '');
  }
}

/// Commande nettoyée comme sur le PC : blancs réduits, longueur bornée.
String cleanCommand(String pCommand) {
  final vCommand = pySplit(pCommand).join(' ');

  return vCommand.length > maxDevopsCommandLength
      ? vCommand.substring(0, maxDevopsCommandLength)
      : vCommand;
}
