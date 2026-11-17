part of '../revision_state.dart';

/// Simulation d'entretien et grille d'auto-évaluation : reçues du PC, saisies sur le
/// téléphone, puis renvoyées au PC à la synchronisation.
mixin InterviewSkills on LabsState {
  List<String> get interviewThemes => [
        for (final vTheme
            in (preferences[interviewPreference] as Map?)?['themes'] as List? ?? const [])
          vTheme as String,
      ];

  List<Map<String, dynamic>> get interviewQuestions => [
        for (final vItem
            in (preferences[interviewPreference] as Map?)?['questions'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  List<Map<String, dynamic>> get pendingInterview => [
        for (final vItem in preferences[pendingInterviewPreference] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  /// Grille d'auto-évaluation : compétence et niveau de 0 à 10.
  List<Map<String, dynamic>> get skillGrid => [
        for (final vItem in preferences[skillGridPreference] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  /// Garde une série de simulation, envoyée au PC à la synchronisation suivante.
  Future<void> recordInterviewSeries(String pTheme, List<Map<String, dynamic>> pResults) =>
      savePreference(pendingInterviewPreference, [
        ...pendingInterview,
        {'theme': pTheme, 'finished_at': DateTime.now().toIso8601String(), 'results': pResults},
      ]);

  /// Enregistre les niveaux saisis : affichés tout de suite, envoyés ensuite.
  Future<void> saveSkillLevels(Map<String, int> pLevels) async {
    preferences = {
      ...preferences,
      skillGridPreference: [
        for (final vEntry in pLevels.entries) {'skill': vEntry.key, 'level': vEntry.value},
      ],
      pendingSkillsPreference: pLevels,
    };
    await store.savePreferences(preferences);
    notifyListeners();
  }

  /// Échange simulation et auto-évaluation avec le PC ; un serveur plus ancien
  /// qui ne les connaît pas n'empêche pas le reste de la synchronisation.
  Future<void> exchangeInterviewAndSkills(ApiClient pClient) async {
    try {
      if (pendingInterview.isNotEmpty) {
        await pClient.uploadInterview(pendingInterview);
        await savePreference(pendingInterviewPreference, <Map<String, dynamic>>[]);
      }

      final vPendingSkills = preferences[pendingSkillsPreference] as Map?;

      if (vPendingSkills != null) {
        await pClient.uploadSkills(Map<String, int>.from(vPendingSkills));
        preferences = {...preferences}..remove(pendingSkillsPreference);
      }

      final vInterview = await pClient.downloadInterview();
      final vSkills = await pClient.downloadSkills();

      preferences = {
        ...preferences,
        interviewPreference: vInterview,
        skillGridPreference: vSkills['grid'] as List? ?? const [],
      };
      await store.savePreferences(preferences);
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('Simulation ou auto-évaluation non échangée : ${vException.message}', name: 'sync');
    } on FormatException catch (vException) {
      log('Réponse illisible pour la simulation : ${vException.message}', name: 'sync');
    }
  }
}
