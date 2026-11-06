part of '../revision_state.dart';

/// Schémas électriques : symboles, niveaux, brouillons et montages réussis.
mixin CircuitSimulation on LabsState {
  CircuitLibrary? _circuitLibrary;
  Object? _circuitSource;

  Map<String, dynamic> get circuitContent =>
      Map<String, dynamic>.from(labs['circuit'] as Map? ?? const {});

  /// Grille et symboles des schémas, refaits seulement quand le contenu reçu change.
  CircuitLibrary? get circuitLibrary {
    final vLibrary = circuitContent['library'];

    if (vLibrary == null) {
      return null;
    }

    if (!identical(vLibrary, _circuitSource)) {
      _circuitSource = vLibrary;
      _circuitLibrary = CircuitLibrary(Map<String, dynamic>.from(vLibrary as Map));
    }

    return _circuitLibrary;
  }

  List<Map<String, dynamic>> get circuitLevels => [
        for (final vItem in circuitContent['levels'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  int get circuitXp => (circuitContent['xp'] as num? ?? 20).toInt();

  /// Montages réussis, sur le PC ou sur le téléphone.
  Set<String> get circuitPassed => {
        for (final vId in circuitContent['passed'] as List? ?? const []) vId as String,
        for (final vId in preferences[circuitPassedPreference] as List? ?? const []) vId as String,
      };

  /// Schéma en cours d'un niveau, ou du mode libre (clé vide) : composants, fils, valeurs saisies.
  Map<String, dynamic>? circuitDraft(String pKey) {
    final vDraft = (preferences[circuitDraftsPreference] as Map?)?[pKey];

    return vDraft == null ? null : jsonDecode(jsonEncode(vDraft)) as Map<String, dynamic>;
  }

  Future<void> saveCircuitDraft(String pKey, Map<String, dynamic> pDraft) => savePreference(
        circuitDraftsPreference,
        {
          ...Map<String, dynamic>.from(preferences[circuitDraftsPreference] as Map? ?? const {}),
          pKey: pDraft
        },
      );

  /// Garde un montage réussi ; le schéma part au PC, qui le resimule.
  Future<bool> recordCircuit(
      String pLevelId, Map<String, dynamic> pSchema, Map<String, double> pValues) async {
    final rFirst = !circuitPassed.contains(pLevelId);

    await queueLab(
      'circuit',
      {'level': pLevelId, 'schema': jsonDecode(jsonEncode(pSchema)), 'values': pValues},
      pChanges: {
        circuitPassedPreference: [...circuitPassed, if (rFirst) pLevelId]
      },
    );

    return rFirst;
  }
}
