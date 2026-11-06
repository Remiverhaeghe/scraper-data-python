part of '../revision_state.dart';

/// Entretien oral : règles de notation et notes des dernières séances.
mixin OralSimulation on LabsState {
  Map<String, dynamic> get oralContent =>
      Map<String, dynamic>.from(labs['oral'] as Map? ?? const {});

  Map<String, dynamic> get oralRules =>
      Map<String, dynamic>.from(oralContent['rules'] as Map? ?? const {});

  int get oralXp => (oralContent['xp'] as num? ?? 25).toInt();

  /// Notes des dernières séances : celles du PC, puis celles pas encore envoyées.
  List<int> get oralRecent => [
        for (final vScore in oralContent['recent'] as List? ?? const []) (vScore as num).toInt(),
        for (final vLab in pendingLabs)
          if (vLab['lab'] == 'oral') (vLab['score'] as num).toInt(),
      ];

  /// Garde une séance d'entretien oral ; ses notes partent au PC, qui les renote.
  Future<void> recordOral(Map<String, dynamic> pSession, int pScore) =>
      queueLab('oral', {'session': pSession, 'score': pScore});
}
