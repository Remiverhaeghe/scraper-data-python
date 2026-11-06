part of '../revision_state.dart';

/// Simulateurs Maven et Docker : niveaux, parties en cours et niveaux réussis.
mixin DevopsSimulation on LabsState {
  Map<String, dynamic> get devopsContent =>
      Map<String, dynamic>.from(labs['devops'] as Map? ?? const {});

  List<Map<String, dynamic>> get devopsLevels => [
        for (final vItem in devopsContent['levels'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  int get devopsXp => (devopsContent['xp'] as num? ?? 20).toInt();

  /// Simulateurs Maven et Docker, avec le dépôt central et les images reçus du PC.
  DevopsLab get devopsLab => DevopsLab(
        Map<String, dynamic>.from(devopsContent['central'] as Map? ?? const {}),
        Map<String, dynamic>.from(devopsContent['registry'] as Map? ?? const {}),
      );

  /// Niveaux Maven et Docker réussis, sur le PC ou sur le téléphone.
  Set<String> get devopsPassed => {
        for (final vId in devopsContent['passed'] as List? ?? const []) vId as String,
        for (final vId in preferences[devopsPassedPreference] as List? ?? const []) vId as String,
      };

  /// Partie en cours d'un niveau : fichier, hôte Docker, console et étapes jouées.
  Map<String, dynamic>? devopsSession(String pLevelId) {
    final vSession = (preferences[devopsSessionsPreference] as Map?)?[pLevelId];

    return vSession == null ? null : jsonDecode(jsonEncode(vSession)) as Map<String, dynamic>;
  }

  Future<void> saveDevopsSession(String pLevelId, Map<String, dynamic>? pSession) {
    final vSessions =
        Map<String, dynamic>.from(preferences[devopsSessionsPreference] as Map? ?? const {});

    if (pSession == null) {
      vSessions.remove(pLevelId);
    } else {
      vSessions[pLevelId] = pSession;
    }

    return savePreference(devopsSessionsPreference, vSessions);
  }

  /// Garde un niveau Maven ou Docker réussi ; les étapes partent au PC, qui les rejoue.
  Future<bool> recordDevops(String pLevelId, List<Map<String, dynamic>> pSteps) async {
    final rFirst = !devopsPassed.contains(pLevelId);

    await queueLab(
      'devops',
      {'level': pLevelId, 'steps': pSteps},
      pChanges: {
        devopsPassedPreference: [...devopsPassed, if (rFirst) pLevelId]
      },
    );

    return rFirst;
  }
}
