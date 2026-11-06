part of '../revision_state.dart';

/// Pannes à résoudre : scénarios, règles de notation et meilleurs scores.
mixin TroubleshootingSimulation on LabsState {
  List<Map<String, dynamic>> get troubleshootingScenarios => [
        for (final vItem in (labs['troubleshooting'] as Map?)?['scenarios'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  TroubleshootingRules get troubleshootingRules => TroubleshootingRules.fromJson(
        Map<String, dynamic>.from((labs['troubleshooting'] as Map?)?['rules'] as Map? ?? const {}),
      );

  /// Meilleur score d'un scénario, sur le téléphone ou sur le PC, ou null.
  int? bestLabScore(String pScenarioId) {
    final vScores = [
      (preferences[labScoresPreference] as Map?)?[pScenarioId],
      ((labs['troubleshooting'] as Map?)?['best'] as Map?)?[pScenarioId],
    ].whereType<num>().map((pScore) => pScore.toInt());

    final rBest = vScores.isEmpty ? null : vScores.reduce((pA, pB) => pA > pB ? pA : pB);

    return rBest;
  }

  /// Garde une panne résolue : meilleur score affiché, partie envoyée au PC ensuite.
  Future<void> recordTroubleshooting(String pScenarioId, List<String> pActions, int pScore) {
    final vScores = Map<String, dynamic>.from(preferences[labScoresPreference] as Map? ?? const {});
    final vBest = bestLabScore(pScenarioId);

    if (vBest == null || pScore > vBest) {
      vScores[pScenarioId] = pScore;
    }

    return queueLab(
      'troubleshooting',
      {'scenario': pScenarioId, 'actions': pActions},
      pChanges: {labScoresPreference: vScores},
    );
  }
}
