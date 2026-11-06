part of '../revision_state.dart';

/// Contenu des simulations reçu du PC et parties en attente d'envoi.
mixin LabsState on ChangeNotifier {
  RevisionStore get store;

  Map<String, dynamic> get preferences;
  set preferences(Map<String, dynamic> pPreferences);

  Future<void> savePreference(String pKey, Object pValue);

  /// Contenu des simulations reçu du PC, par simulation.
  Map<String, dynamic> get labs =>
      Map<String, dynamic>.from(preferences[labsPreference] as Map? ?? const {});

  List<Map<String, dynamic>> get pendingLabs => [
        for (final vItem in preferences[pendingLabsPreference] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  /// Met une partie en attente d'envoi au PC, avec les préférences qu'elle modifie.
  Future<void> queueLab(
    String pLab,
    Map<String, dynamic> pFields, {
    Map<String, Object> pChanges = const {},
  }) async {
    preferences = {
      ...preferences,
      ...pChanges,
      pendingLabsPreference: [...pendingLabs, newLab(pLab, pFields)],
    };
    await store.savePreferences(preferences);
    notifyListeners();
  }

  /// Partie prête à envoyer : identifiant pour éviter les doublons, date de fin.
  Map<String, dynamic> newLab(String pLab, Map<String, dynamic> pFields) => {
        'id': const Uuid().v4(),
        'lab': pLab,
        ...pFields,
        'finished_at': DateTime.now().toIso8601String(),
      };

  /// Envoie les parties en attente et reçoit le contenu à jour des simulations ;
  /// un serveur plus ancien qui ne les connaît pas n'empêche pas le reste.
  Future<void> exchangeLabs(ApiClient pClient) async {
    try {
      if (pendingLabs.isNotEmpty) {
        await pClient.uploadLabs(pendingLabs);
        await savePreference(pendingLabsPreference, <Map<String, dynamic>>[]);
      }

      await savePreference(labsPreference, await pClient.downloadLabs());

      // Les séries envoyées sont comptées par le PC : sa progression fait foi
      preferences = {...preferences}..remove(puzzleProgressPreference);
      await store.savePreferences(preferences);
    } on ApiException catch (vException) {
      if (vException.unreachable) {
        rethrow;
      }

      log('Simulations non échangées : ${vException.message}', name: 'sync');
    } on FormatException catch (vException) {
      log('Réponse illisible pour les simulations : ${vException.message}', name: 'sync');
    }
  }
}
