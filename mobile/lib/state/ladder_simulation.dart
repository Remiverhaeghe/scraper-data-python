part of '../revision_state.dart';

/// Simulateur d'automate : niveaux, programmes en cours et niveaux réussis.
mixin LadderSimulation on LabsState {
  List<Map<String, dynamic>> get ladderLevels => [
        for (final vItem in (labs['ladder'] as Map?)?['levels'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  int get ladderXp => ((labs['ladder'] as Map?)?['xp'] as num? ?? 25).toInt();

  /// Niveaux d'automate réussis, sur le PC ou sur le téléphone.
  Set<String> get ladderPassed => {
        for (final vId in (labs['ladder'] as Map?)?['passed'] as List? ?? const []) vId as String,
        for (final vId in preferences[ladderPassedPreference] as List? ?? const []) vId as String,
      };

  /// Dernier programme écrit pour un niveau, ou son point de départ.
  String ladderProgram(Map<String, dynamic> pLevel) =>
      (preferences[ladderProgramsPreference] as Map?)?[pLevel['id']] as String? ??
      pLevel['starter'] as String;

  Future<void> saveLadderProgram(String pLevelId, String pProgram) => savePreference(
        ladderProgramsPreference,
        {
          ...Map<String, dynamic>.from(preferences[ladderProgramsPreference] as Map? ?? const {}),
          pLevelId: pProgram
        },
      );

  /// Garde un niveau réussi ; le programme part au PC, qui le revérifie.
  Future<bool> recordLadder(String pLevelId, String pProgram) async {
    final rFirst = !ladderPassed.contains(pLevelId);

    await queueLab(
      'ladder',
      {'level': pLevelId, 'program': pProgram},
      pChanges: {
        ladderPassedPreference: [...ladderPassed, if (rFirst) pLevelId]
      },
    );

    return rFirst;
  }
}
