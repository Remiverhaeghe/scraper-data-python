part of '../revision_state.dart';

/// Simulateur Git : niveaux, commandes jouées et meilleurs nombres de commandes.
mixin GitSimulation on LabsState {
  List<Map<String, dynamic>> get gitLevels => [
        for (final vItem in (labs['git'] as Map?)?['levels'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  int get gitXp => ((labs['git'] as Map?)?['xp'] as num? ?? 25).toInt();

  /// Meilleur nombre de commandes d'un niveau Git, sur le PC ou le téléphone, ou null.
  int? gitBest(String pLevelId) {
    final vCounts = [
      ((labs['git'] as Map?)?['best'] as Map?)?[pLevelId],
      (preferences[gitBestPreference] as Map?)?[pLevelId],
    ].whereType<num>().map((pCount) => pCount.toInt());

    final rBest = vCounts.isEmpty ? null : vCounts.reduce((pA, pB) => pA < pB ? pA : pB);

    return rBest;
  }

  /// Commandes déjà jouées dans un niveau Git, pour le reprendre là où on l'a laissé.
  List<String> gitHistory(String pLevelId) => List<String>.from(
      (preferences[gitHistoriesPreference] as Map?)?[pLevelId] as List? ?? const []);

  Future<void> saveGitHistory(String pLevelId, List<String> pHistory) => savePreference(
        gitHistoriesPreference,
        {
          ...Map<String, dynamic>.from(preferences[gitHistoriesPreference] as Map? ?? const {}),
          pLevelId: pHistory,
        },
      );

  /// Garde un niveau Git réussi ; les commandes partent au PC, qui les rejoue.
  Future<bool> recordGit(String pLevelId, List<String> pHistory) async {
    final vBest = gitBest(pLevelId);
    final rFirst = vBest == null;

    await queueLab(
      'git',
      {'level': pLevelId, 'history': pHistory},
      pChanges: {
        gitBestPreference: {
          ...Map<String, dynamic>.from(preferences[gitBestPreference] as Map? ?? const {}),
          pLevelId: vBest == null || pHistory.length < vBest ? pHistory.length : vBest,
        },
      },
    );

    return rFirst;
  }
}
