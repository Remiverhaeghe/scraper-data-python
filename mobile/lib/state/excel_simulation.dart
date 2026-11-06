part of '../revision_state.dart';

/// Atelier Excel : niveaux, règles, formules en cours et niveaux réussis.
mixin ExcelSimulation on LabsState {
  ExcelLevels? _excelLevels;
  Object? _excelSource;

  Map<String, dynamic> get excelPackage =>
      Map<String, dynamic>.from(labs['excel'] as Map? ?? const {});

  /// Niveaux Excel et leurs règles, refaits seulement quand le contenu reçu change.
  ExcelLevels? get excelLevels {
    final vPackage = labs['excel'];

    if (vPackage == null) {
      return null;
    }

    if (!identical(vPackage, _excelSource)) {
      _excelSource = vPackage;
      _excelLevels = ExcelLevels(Map<String, dynamic>.from(vPackage as Map));
    }

    return _excelLevels;
  }

  List<Map<String, dynamic>> get excelLevelList => [
        for (final vItem in excelPackage['levels'] as List? ?? const [])
          Map<String, dynamic>.from(vItem as Map),
      ];

  int get excelXp => (excelPackage['xp'] as num? ?? 15).toInt();

  /// Niveaux Excel réussis, sur le PC ou sur le téléphone.
  Set<String> get excelPassed => {
        for (final vId in excelPackage['passed'] as List? ?? const []) vId as String,
        for (final vId in preferences[excelPassedPreference] as List? ?? const []) vId as String,
      };

  /// Dernière formule écrite pour un niveau, ou « = » pour commencer.
  String excelFormula(Map<String, dynamic> pLevel) =>
      (preferences[excelFormulasPreference] as Map?)?[pLevel['id']] as String? ?? '=';

  Future<void> saveExcelFormula(String pLevelId, String pFormula) => savePreference(
        excelFormulasPreference,
        {
          ...Map<String, dynamic>.from(preferences[excelFormulasPreference] as Map? ?? const {}),
          pLevelId: pFormula
        },
      );

  /// Garde un niveau Excel réussi ; la formule part au PC, qui la recalcule.
  Future<bool> recordExcel(String pLevelId, String pFormula) async {
    final rFirst = !excelPassed.contains(pLevelId);

    await queueLab(
      'excel',
      {'level': pLevelId, 'formula': pFormula},
      pChanges: {
        excelPassedPreference: [...excelPassed, if (rFirst) pLevelId]
      },
    );

    return rFirst;
  }
}
